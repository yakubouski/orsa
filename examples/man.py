import orsa, asyncio

mgr = orsa.Manager()

@mgr.on.startup
async def startup(self):
    self.logger.debug(f"Manager is started")

@mgr.on.shutdown
async def shutdown(self):
    self.logger.debug(f"Manager is shutdown")

@mgr.on.monitor(timeout=20.0)
async def monitor(self):
    tasks = asyncio.all_tasks(asyncio.get_running_loop())
    self.logger.debug(f"@RUNNING: {[task.get_name() for task in tasks if task.get_name() != '@monitoring']}",extra={'kind':'manager'})

mgr.start()
