from asyncio import iscoroutinefunction, get_running_loop, create_task
from ._manager import Manager
from ..context._async import AsyncContext

class Orchestrator:
    def __init__(self, manager=None):
        self._manager = manager

    def __call__(self, func):  # Decorator
        def wrapper(*args, **kwargs):
            if iscoroutinefunction(func):
                try:
                    _manager = self._manager or kwargs.pop('__manager',None)
                    ctx = AsyncContext(func, args, kwargs, manager=_manager, state = kwargs.pop('__state',None))
                    if _manager:
                        async def __schedule():
                            return _manager._schedule_saga(ctx)
                        return __schedule()  # Coroutine call
                    else:
                        fut = get_running_loop().create_future()
                        create_task(ctx(fut))
                        return fut
                except Exception as e:
                    print(f"Error orchestrating coroutine {func.__name__}: {e}") # Add error handling
                    return None # Return None in case of error
            else:
                # Sync call
                try:
                    return func(*args, **kwargs)  # Просто выполняем функцию
                except Exception as e:
                    print(f"Error executing synchronous function {func.__name__}: {e}")
                    return None
        return wrapper

def orchestrator(func = None, manager: Manager = None):
    if func:
        return Orchestrator(manager = manager)(func)
    else:
        return Orchestrator(manager = manager)

__all__ = ['orchestrator']