from logging import Logger
import asyncio, threading, sys
from typing import Any
from uuid import UUID
from ._context import Context as Saga
from ._logger import getLogger
import concurrent.futures
import importlib

_logger = getLogger("orsa", True)

async def _call_helper(func,*args, **kwargs):
    if func:
        return await func(*args,**kwargs) if asyncio.iscoroutinefunction(func) else func(*args,**kwargs)
    return None

class _OnSaga():
    def __init__(self):
        self._on_store = None
        self._on_abort = None
        self._on_complete = None

    def store(self, func):
        """
        Decorator to define callback when need store Saga state

        Examples:
            @manager.saga.store
            async def _saga_store(saga: Saga)
                StoreSaga(saga.uid, saga.state)
        """
        self._on_store = func

    def complete(self, func):
        """
        Decorator to define callback when Saga is executing complete wit success state

        Examples:
            @manager.saga.complete
            async def _saga_complete(saga: Saga)
                WriteSagaLog(saga.uid, saga.state,'complete')
                DeleteSagaState(saga.uid)
        """
        self._on_complete = func

    def abort(self, func):
        """
        Decorator to define callback when Saga abort execution

        Examples:
            @manager.saga.abort
            async def _saga_abort(saga: Saga)
                WriteSagaLog(saga.uid, saga.state,'abort')
                DeleteSagaState(saga.uid)
        """
        self._on_abort = func

class Manager():
    """Saga orchestrator manager base class"""
    def __init__(self, threads: int = 1):
        self._event_loop = None
        self._event_thread = None
        self._on_monitor = (None, 10.0)
        self.__monitoring_task = None
        self.__on_startup_fn = None
        self.__on_shutdown_fn = None
        self._on_saga = _OnSaga()

    async def __monitor(self):
        while not self.__monitoring_task.cancelled():
            await _call_helper(self._on_monitor[0],self)
            await asyncio.sleep(self._on_monitor[1])

    def _schedule_saga(self, saga: Saga, uid: UUID = None, state: dict[str,Any] = None):
        """
        Schedule or reschedule Saga
        """
        if uid is not None:
            """
            Restore Saga state by own UID, call callback _on_restore
            """
            self.saga.restore(uid,state)

        task = asyncio.run_coroutine_threadsafe(saga(), loop=self._event_loop)
        def __complete_task(future: asyncio.Future):
            if future.cancelled:
                self.logger.error("Saga is canceled without exception and not be run completed")
            elif future.exception:
                self._event_loop.run_until_complete(_call_helper(self.saga._on_abort,saga,'exception'))
            else:
                self._event_loop.run_until_complete(_call_helper(self.saga._on_complete,saga))
        task.add_done_callback(__complete_task)

    @property
    def logger(self) -> Logger:
        """
        Get Manager logger
        """
        return _logger

    @property
    def saga(self) -> _OnSaga:
        """
        Get property for saga decorator callbacks
        """
        return self._on_saga

    def Start(self):
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
                loop.run_until_complete(_call_helper(self.__on_startup_fn,self))
                loop.run_forever()
            except Exception as e:
                _logger.error(f"Event loop exited unexpectedly: {e}", extra={'kind': 'manager'})

            loop.run_until_complete(_call_helper(self.__on_shutdown_fn,self))

        self._event_loop:asyncio.AbstractEventLoop = asyncio.new_event_loop()
        self._event_thread = threading.Thread(target=async_loop_thread, args=(self._event_loop,), daemon=False, name='manager')
        self._event_thread.start()

        # Run monitoring loop
        if self._on_monitor[0]:
            self.__monitoring_task = self._event_loop.create_task(self.__monitor(),name='@monitoring')

    def Stop(self):
        """
        Stop event loop and shutdown the manager
        """
        if self._event_loop is not None:
            self._event_loop.call_soon_threadsafe(self._event_loop.stop)
        if self._event_thread is not None:
            self._event_thread.join()
        if self._event_loop is not None:
            self._event_loop.close()

    def startup(self, func):
        """
        Decorator called after manager is success init and used to restore Saga execution states

        Examples:
            @manager.startup
            async def _startup(self)
                _incomplete_sagas = LoadIncompleteSagas()
                for saga in _incomplete_sagas:
                    self._restore_saga(saga['uid'],saga['state'])
        """
        self.__on_startup_fn = func

    def shutdown(self, func):
        """
        Decorator called before manager is shutdown
        Examples:
            @manager.shutdown
            async def _shutdown(self)
                _incomplete_sagas = LoadIncompleteSagas()
                DeleteSagaState(saga.uid)
        """
        self.__on_shutdown_fn = func

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

    async def _store_saga(self,saga: Saga):
        """
        Internal method to call saga commit handler
        """
        return await _call_helper(self.saga._on_store,saga)

    async def _restore_saga(self,uid: UUID, state: dict[str,Any]):
        """
        Internal method to restore Saga and continue execution
        """
        _uid, _args, _kwargs,_src, _entry, _module = Saga._expand_module_entry(state)
        if _uid:
            if _module in sys.modules:
                module = sys.modules[_module]
                entry = getattr(module, _entry)
                context = entry(*_args, **_kwargs)
                return context
            else:
                spec = importlib.util.spec_from_file_location(_module, _src)
                module = importlib.util.module_from_spec(spec)
                sys.modules[spec.name] = module
                spec.loader.exec_module(module)

                entry = getattr(module, self.entry)
                context = entry(*_args, **_kwargs, manager=self, _uid=_uid, _state=state)
                
                return context
