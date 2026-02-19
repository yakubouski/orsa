"""
Python saga orchestrator (ORSA)
"""
from logging import Logger
from .core._types import Result, Retry
from .core._context import Context as Saga
from .core._orchestrator import orchestrator
from .core._manager import Manager
from .core._logger import getLogger

def logger() -> Logger:
    return getLogger('orsa',True)

__all__ = ['Saga', 'Result', 'Retry', 'Manager','orchestrator','logger']