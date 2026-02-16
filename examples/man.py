import orsa, asyncio

mgr:orsa.Manager = orsa.Manager()

@mgr.saga.store
async def _saga_store(saga: orsa.Saga):
    ...

@mgr.saga.abort
async def _saga_abort(saga: orsa.Saga):
    ...

@mgr.saga.complete
async def _saga_complete(saga: orsa.Saga):
    ...

@mgr.startup
async def startup(self):
    self.logger.debug(f"Manager is started")

@mgr.shutdown
async def shutdown(self):
    self.logger.debug(f"Manager is shutdown")

@mgr.monitor(timeout=20.0)
async def monitor(self):
    tasks = asyncio.all_tasks(asyncio.get_running_loop())
    self.logger.debug(f"@RUNNING: {[task.get_name() for task in tasks if task.get_name() != '@monitoring']}",extra={'kind':'manager'})

mgr.Start()
