import orsa, asyncio, aiofiles, json, pathlib, uuid, pydantic
from otypes import OrderItem

mgr:orsa.Manager = orsa.Manager()

_sagaItems = {}
_sagaDbFile = pathlib.Path('saga.db.json')

async def WriteDB(Db: list):
    class Encoder(json.JSONEncoder):
        def default(self, obj):
            if isinstance(obj, uuid.UUID):
                return str(obj)
            if isinstance(obj, pydantic.BaseModel):
                return obj.model_dump(by_alias=True)
            return super().default(obj)

    async with aiofiles.open(_sagaDbFile, mode='w',encoding='utf-8') as f:
        await f.write(json.dumps(Db, indent=4, cls=Encoder))

async def ReadDB() -> list:
    class Decoder(json.JSONDecoder):
        def __init__(self, *args, **kwargs):
            super().__init__(object_hook=self.object_hook, *args, **kwargs)

        def object_hook(self, obj):
            if "sku" in obj:
                return OrderItem(**obj)
            return obj

    if _sagaDbFile.exists():
        async with aiofiles.open(_sagaDbFile, mode='r',encoding='utf-8') as f:
            _sagaSnapshot = json.loads(await f.read(), cls=Decoder)
            return _sagaSnapshot if type(_sagaSnapshot) == list else []
    return []

@mgr.saga.store
async def _saga_store(self: orsa.Manager, saga: orsa.Saga):
    _sagaItems[str(saga.uid)] = saga.state
    await WriteDB(list(_sagaItems.values()))
    

@mgr.saga.abort
async def _saga_abort(self: orsa.Manager,saga: orsa.Saga, reason):
    self.logger.info(f"Saga:{saga.uid} ... aborted")
    _sagaItems.pop(str(saga.uid))
    await WriteDB(list(_sagaItems.values()))

@mgr.saga.complete
async def _saga_complete(self: orsa.Manager,saga: orsa.Saga):
    self.logger.info(f"Saga:{saga.uid} ... complete")
    _sagaItems.pop(str(saga.uid))
    await WriteDB(list(_sagaItems.values()))

@mgr.startup
async def _startup(self: orsa.Manager):
    _sagaItems = {_state['@uid']: _state for _state in await ReadDB()}
    for _uid, _state in _sagaItems.items():
        _uid, _name = await self._restore_saga(_state)
        self.logger.debug(f"Saga:{_name} with {_uid} ... is restored")
    self.logger.debug(f"Manager is started")

@mgr.shutdown
async def _shutdown(self):
    self.logger.debug(f"Manager is shutdown")

@mgr.monitor(timeout=20.0)
async def _monitor(self):
    tasks = asyncio.all_tasks(asyncio.get_running_loop())
    self.logger.debug(f"@RUNNING: {[task.get_name() for task in tasks if task.get_name() != '@monitoring']}",extra={'kind':'manager'})

mgr.Start()
