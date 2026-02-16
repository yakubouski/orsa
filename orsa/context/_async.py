from asyncio import iscoroutinefunction
from ..core._context import Context,_logger

class AsyncContext(Context):
    def __init__(self, entry, args, kwargs, manager=None):
        super().__init__(entry, args, kwargs, manager)

    async def __rollback(self, no: int, _context):
        while no > 0:
            no -= 1
            self._step_no = no
            if isinstance(self._steps[no], Context._rollback):
                try:
                    await self._steps[no](_context)
                    _logger.debug(f"Rollback", extra={'saga' : self._steps[no]._name, 'kind' : f"{self._name}."})
                except Exception as ex:
                    _logger.error(f"Rollback error at step {no}", exc_info=ex, extra={'saga': self._steps[no]._name, 'kind' : f'{self._name}.'})
        self._step_no = None

    async def __call__(self):
        await self._run(self._args, self._kwargs)

    async def _run(self, args, kwargs):
        await self._entry(self, *args, **kwargs)
        if self._readiness:
            if iscoroutinefunction(self._readiness):
                await self._readiness()
            else:
                self._readiness()
        await self._execute(args, kwargs)

    async def _execute(self, args, kwargs):
        _arguments = self._expand_arguments(args, kwargs, self._entry)
        for no in range(len(self._steps)):
            self._step_no = no
            if not isinstance(self._steps[no], Context._rollback):
                step_name = self._steps[no]._name
                try:
                    _logger.debug(f"Execute", extra={'saga' : step_name, 'kind' : f"{self._name}."})
                    result = await self._steps[no](_arguments)
                    self._returns[step_name] = result
                    if self._manager:
                        self._manager._store_saga(self)
                except Exception as ex:
                    await self.__rollback(self._step_no,_arguments)
                    if self._catch:
                        if iscoroutinefunction(self._catch):
                            await self._catch(step_name, ex)
                        else:
                            self._catch(step_name, ex)
                    raise
        self._step_no = None