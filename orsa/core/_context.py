from typing import Any
from uuid import UUID, uuid4
from ._callee import Callee
from ._types import Retry
from datetime import datetime
from inspect import getsource, getsourcefile, signature

from ._logger import getLogger

_logger = getLogger("orsa", True)

class Context:
    """
    Base class implement Saga execution context, can be specialized in overloaded Child class|
    """
    class _step(Callee):
        """
        Class implement every step execution context
        """
        def __init__(self, fn, saga, returns, args, kwargs, retry: Retry | int = None):
            super().__init__(fn, saga, returns, retry)
            #self._step_context = (args, kwargs)

    class _rollback(Callee):
        """
        Class implement rollback operation for step
        """
        def __init__(self, fn, saga, returns, args, kwargs, retry: Retry | int = None):
            super().__init__(fn, saga, returns, retry)
            #self._step_context = (args, kwargs)

    def __init__(self, entry, args, kwargs, manager = None):
        self._entry = entry
        self._args = args; self._kwargs = kwargs
        self._steps:list[Callee] = []
        self._returns = {}
        self._name = self._entry.__name__
        self._step_no = None
        self._uid = uuid4()
        self._readiness = None
        self._catch = None
        self._manager = manager
        self._state = {'@uid': self._uid,'@args': self._args, '@kwargs': self._kwargs, **self._get_entry_details(), '@returns': self._returns }

    def _expand_arguments(self,args, kwargs, fn):
        _expand_arguments = {**kwargs}
        for narg in range(len(args)):
            params = list(signature(fn).parameters.keys())
            for arg in args:
                _expand_arguments[params[narg]] = arg
        return _expand_arguments

    @staticmethod
    def _expand_module_entry(state: dict[str,Any]) -> tuple[str]:
        return (state.get('@uid',None),state.get('@args',None),state.get('@kwargs',None),
                state.get('@src',None),state.get('@entry',None),state.get('@module',None))

    @property
    def uid(self) -> UUID:
        """
        Get Saga UUID
        """
        return self._uid

    @property
    def state(self) -> dict[str,Any]:
        """
        Get Saga execution state
        """
        return self._state

    def restore(self, state: dict[str, Any]):
        """
        Restore saga state after restart manager
        """
        self._uid = state.get('@uid',uuid4())
        self._args = state.get('@args',{}); self._kwargs = state.get('@kwargs',{})
        self._returns = state.get('@returns',{})

    def _get_entry_details(self):
        entrySourceFile = getsourcefile(self._entry)
        entryName = self._entry.__name__
        entryModule = self._entry.__module__
        return {'@src': entrySourceFile,'@entry': entryName,'@module': entryModule}

    def step(self, fn = None, retry: Retry | int = None):
        """
        Decorator for declare Saga Step
        """
        def decorator(func):
            _logger.debug(f"Add step `{func.__name__}`", extra={'saga' : self._name, 'kind' : 'orchestrator '})
            self._steps.append(self._step(func, self._name, self._returns, (), {}, retry))
            return func

        if fn is None:
            return decorator
        else:
            _logger.debug(f"Add step `{fn.__name__}`", extra={'saga' : self._name, 'kind' : 'orchestrator '})
            self._steps.append(self._step(fn, self._name, self._returns, (), {}, retry))
            return fn

    def rollback(self, fn = None, retry: Retry | int = None):
        """
        Decorator for declare Rollback for previous Step Saga
        """
        stepFor = None
        for stp in reversed(self._steps):
            if isinstance(stp, Context._step):
                stepFor = stp._name
                break

        def decorator(func):
            _logger.debug(f"Add rollback `{fn.__name__}`{f' for {stepFor}' if stepFor else ''}", extra={'saga': self._name, 'kind': 'orchestrator '})
            self._steps.append(self._rollback(func, self._name, self._returns, (), {}, retry))
            return func

        if fn is None:
            return decorator
        else:
            _logger.debug(f"Add rollback `{fn.__name__}`{f' for {stepFor}' if stepFor else ''}", extra={'saga' : self._name, 'kind' : 'orchestrator '})
            self._steps.append(self._rollback(fn, self._name, self._returns, (), {}, retry))
            return fn

    def readiness(self, fn):
        """
        Decorator for declare Saga readiness callback, executing before start saga
        """
        _logger.debug(f"Register lifespan `{fn.__name__}`", extra={'saga' : self._name, 'kind' : 'orchestrator '})
        self._readiness = fn

    def catch(self, fn):
        """
        Decorator for declare Saga exception handler
        """
        _logger.debug(f"Register catch `{fn.__name__}`", extra={'saga' : self._name, 'kind' : 'orchestrator '})
        self._catch = fn