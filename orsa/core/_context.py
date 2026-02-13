from typing import Any
from uuid import uuid4
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

    def __init__(self, entry, manager = None):
        self._entry = entry
        self._steps:list[Callee] = []
        self._returns = {}
        self._name = self._entry.__name__
        self._step_no = None
        self._uid = uuid4()
        self._lifespan = None
        self._catch = None
        self._manager = manager

    def _expand_arguments(self,args, kwargs, fn):
        _expand_arguments = {**kwargs}
        for narg in range(len(args)):
            params = list(signature(fn).parameters.keys())
            for arg in args:
                _expand_arguments[params[narg]] = arg
        return _expand_arguments

#    @property
#    def current(self) -> Callee:
#        """
#        Saga current step execution context
#        """
#        return self._steps[self._step_no] if self._step_no is not None and (self._step_no>=0 and self._step_no < len(self._steps)) else None
#
    def _get_entry_details(self):
        entrySourceFile = getsourcefile(self._entry)
        entryName = self._entry.__name__
        entryModule = self._entry.__module__
        return (entrySourceFile,entryName,entryModule)

    #def _complete_run(self):
    #    """
    #    Notify manager after complete execute all saga steps
    #    """
    #    if self._manager:
    #        self._manager._onCompleteSaga(self.uid, self.name)
    #
    #def _commit_step(self, step_name: str, result):
    #    """
    #    Save step result
    #    """
    #    if self._manager:
    #        self._manager._onCommitSaga(self.uid, self.name, step_name, result)
    #
    #def _is_step_completed(self, step_name: str) -> bool|None:
    #    """
    #    Check is step completed
    #    """
    #    if self._manager:
    #        return self._manager._onIsStepCompleted(self.uid, self.name, step_name)
    #
    #    return None
    #
    #def _get_step_result(self, step_name: str) -> Any|None:
    #    """
    #    Check is step completed
    #    """
    #    if self._manager:
    #        return self._manager._onGetStepResult(self.uid, self.name, step_name)
    #
    #    return None
    #
    #def _raise_step(self, step_name: str, ex):
    #    """
    #    Step exception raised
    #    """
    #    if self._catch:
    #        self._catch(step_name, ex)
    #    if self._manager:
    #        self._manager._onRaiseSaga(self.uid, self.name, step_name, ex)

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
        Decorator for declare Saga Step Rollback
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

    def lifespan(self, fn):
        """
        Decorator for declare Saga lifespan
        """
        _logger.debug(f"Register lifespan `{fn.__name__}`", extra={'saga' : self._name, 'kind' : 'orchestrator '})
        self._lifespan = fn

    def catch(self, fn):
        """
        Decorator for declare Saga exception handler
        """
        _logger.debug(f"Register catch `{fn.__name__}`", extra={'saga' : self._name, 'kind' : 'orchestrator '})
        self._catch = fn