from asyncio import iscoroutinefunction
from ._context import Context
from ._manager import Manager
from ..context._async import AsyncContext

class Orchestrator:
    def __init__(self, manager=None):
        self.manager = manager

    def __call__(self, func):  # Decorator
        def wrapper(*args, **kwargs):
            if iscoroutinefunction(func):
                try:
                    ctx = AsyncContext(func, args, kwargs, manager=self.manager)
                    if self.manager:
                        async def __schedule():
                            return self.manager.schedule(ctx)
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

def orchestrator(func = None, manager: Manager = None):
    if func:
        return Orchestrator(manager = manager)(func)
    else:
        return Orchestrator(manager = manager)

__all__ = ['orchestrator']