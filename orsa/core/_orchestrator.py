from asyncio import iscoroutinefunction
from ._manager import Manager
from ..context._async import AsyncContext

class Orchestrator:
    def __init__(self, manager=None):
        self._manager = manager

    def __call__(self, func):  # Decorator
        def wrapper(*args, **kwargs):
            if iscoroutinefunction(func):
                try:
                    ctx = AsyncContext(func, args, kwargs, manager=self._manager)
                    if self._manager:
                        async def __schedule():
                            return self._manager._schedule_saga(ctx, kwargs.get('_uid',None), kwargs.get('_state',None))
                        return __schedule()  # Coroutine call
                    else:
                        return ctx()  # Call AsyncContext directly
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

def orchestrator(func = None, manager: Manager = None, **kwargs):
    if func:
        return Orchestrator(manager = manager,kwargs = kwargs)(func)
    else:
        return Orchestrator(manager = manager, kwargs = kwargs)

__all__ = ['orchestrator']