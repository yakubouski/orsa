from logging import Logger
import asyncio, threading, sys
from ._context import Context
from ._logger import getLogger
import concurrent.futures

_logger = getLogger("orsa", True)

async def _call_helper(func,*args, **kwargs):
    if func:
        return await func(*args,**kwargs) if asyncio.iscoroutinefunction(func) else func(*args,**kwargs)

class _OnSaga():
    def __init__(self):
        ...
    def commit():
        ...

    def complete():
        ...

    def abort():
        ...

class _OnManager():
    def __init__(self):
        self._on_monitor = (None, 10.0)
        self._on_startup = None
        self._on_shutdown = None
        self._on_saga = _OnSaga()

    @property
    def saga(self) -> _OnSaga:
        return self._on_saga

    def monitor(self, func = None, timeout: float = 10.0):
        """
        Decorator to add manager monitoring callback
        """
        if func is not None:
            self._on_monitor = (func, timeout)
        else:
            def wrapper(func):
                self._on_monitor = (func, timeout)
            return wrapper

    def startup(self, func):
        """
        Decorator called after manager is success init and used to restore Saga execution states
        """
        self._on_startup = func

    def shutdown(self, func):
        """
        Decorator called before manager is shutdown
        """
        self._on_shutdown = func

class Manager():
    """Saga orchestrator manager base class"""
    def __init__(self, threads: int = 1):
        self._event_loop = None
        self._event_thread = None
        self.__monitoring_fn = None
        self.__on_e =_OnManager()

    async def __monitor(self):
        while not self.__monitoring_fn.cancelled():
            await _call_helper(self.__on_e._on_monitor[0],self)
            await asyncio.sleep(self.__on_e._on_monitor[1])

    def schedule(self, saga: Context):
        """
        Schedule or reschedule Saga
        """
        task = asyncio.run_coroutine_threadsafe(saga(), loop=self._event_loop)
        def __complete_task(future):
            print(f"!!! SAGA {saga._name} is done")
        task.add_done_callback(__complete_task)
        return task

    @property
    def logger(self) -> Logger:
        return _logger

    def start(self):
        """
        Create new event loop in separate thread and run manager
        """
        def async_loop_thread(loop: asyncio.AbstractEventLoop):
            asyncio.set_event_loop(loop)
            if sys.platform == "win32":
                try:
                    current_policy = asyncio.get_event_loop_policy()
                    if not isinstance(current_policy, asyncio.WindowsSelectorEventLoopPolicy):
                        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
                except Exception:
                    pass
            try:
                loop.run_until_complete(_call_helper(self.__on_e._on_startup,self))
                loop.run_forever()
            except Exception as e:
                _logger.error(f"Event loop exited unexpectedly: {e}", extra={'kind': 'manager'})

            loop.run_until_complete(_call_helper(self.__on_e._on_shutdown,self))

        self._event_loop:asyncio.AbstractEventLoop = asyncio.new_event_loop()
        self._event_thread = threading.Thread(target=async_loop_thread, args=(self._event_loop,), daemon=False, name='manager')
        self._event_thread.start()

        # Run monitoring loop
        if self.__on_e._on_monitor[0]:
            self.__monitoring_fn = self._event_loop.create_task(self.__monitor(),name='@monitoring')

    def stop(self):
        """
        Stop event loop and shutdown the manager
        """
        if self._event_loop is not None:
            self._event_loop.call_soon_threadsafe(self._event_loop.stop)
        if self._event_thread is not None:
            self._event_thread.join()
        if self._event_loop is not None:
            self._event_loop.close()

    @property
    def on(self) -> _OnManager:
        return self.__on_e