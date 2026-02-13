from typing import get_type_hints, get_args, get_origin
from inspect import signature, iscoroutinefunction
from asyncio import sleep as async_sleep
from time import sleep as sync_sleep
from uuid import UUID
from ._types import Retry, Result
from ._logger import getLogger

_logger = getLogger("orsa",True)

class Callee:
    """
    Proxy class of the called function
    """
    def __init__(self, fn, saga, returns: dict, retry: Retry | int = None, name: str = None):
        self._fn = fn
        self._saga = saga;
        self._name = self._fn.__name__ if not name else name
        self._returns = returns
        """
        Expand Retry parameter
        """
        if retry is None:
            self._retry_config = Retry(0, 0.0, 0.0)
        elif isinstance(retry, int):
            self._retry_config = Retry(retry, 3.0, 1.0)
        elif isinstance(retry, Retry):
            self._retry_config = retry
        else:
            raise TypeError(f"retry must be None, int or Retry, got {type(retry_config)}")

    def _bind_context(self,context, args):
        """
        Bind call params context with signature of the function
        """
        kwargs = {**context}
        for vn, tp in get_type_hints(self._fn, include_extras=True).items():
            if get_origin(tp) is Result:
                _type, _step = get_args(tp)
                kwargs[vn] = self._returns.get(_step.__name__,None)
        sig = signature(self._fn)
        params = sig.bind(*args, **{k: kwargs[k] for k, v in sig.parameters.items() if k in kwargs})
        params.apply_defaults()
        return params

    def _repeat(self, attempt, ex):
        """
        Calculate the next delay if attempts do not exceed the limit; otherwise, re-raise the exception
        """
        if attempt < self._retry_config.count:
            current_delay = self._retry_config.timeout * (self._retry_config.scale ** attempt)
            _logger.warning(f"Exception: {ex}. Repeating {attempt}/{self._retry_config.count} after {current_delay:.1f} sec", exc_info=False, extra={'saga' : self._name,'kind' : f'{self._saga}.'})
        else:
            _logger.error(f"Exception: {ex}. Failed after {attempt}/{self._retry_config.count} attempts.", exc_info=False, extra={'saga' : self._name,'kind' : f'{self._saga}.'})
            raise ex

        return current_delay

    def __call__(self, context, args=[]):
        sig = self._bind_context(context, args)
        attempt = 0
        while True:
            try:
                attempt += 1
                return self._fn(*sig.args, **sig.kwargs)
            except Exception as ex:
                sync_sleep(self._repeat(attempt, ex))

    async def __call__(self, context, args=[]):
        sig = self._bind_context(context,args)
        attempt = 0
        while True:
            try:
                attempt += 1
                if iscoroutinefunction(self._fn):
                    return await self._fn(*sig.args, **sig.kwargs)
                else:
                    return self._fn(*sig.args, **sig.kwargs)
            except Exception as ex:
                await async_sleep(self._repeat(attempt, ex))
