from typing import Generic, TypeVar, TypeAlias, Any, NamedTuple,get_origin, get_args
from types import GenericAlias
import inspect

"""
Definition of the parameters for step retry algorithm
"""
Retry = NamedTuple("Retry", [('count', int), ('timeout', float), ('scale', float)])

T = TypeVar('T')

class Result(Generic[T]):
    """
    Custom type for Annotated like syntaxis support for pass previous result to saga step
    Example:
    @self.step
    async def step_1() -> str:
        return "step_1 result"

    @self.step
    async def step_2(res: Result[str,step_1]) -> str:
        return f"step_2 argument({res})"
    """
    def __class_getitem__(cls, params) -> TypeAlias:
        if isinstance(params, tuple) and len(params) == 2:
            type_hint, step_fn = params
            # Custom annotation
            return GenericAlias(cls, (type_hint, step_fn))
        return super().__class_getitem__(params)