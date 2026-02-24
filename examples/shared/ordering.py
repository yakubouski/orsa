import asyncio,aiofiles
from logging import Logger
import uuid, json, threading
from orsa import orchestrator, Saga, Result, logger
from otypes import OrderItem
from man import mgr

_logger:Logger = logger()

@orchestrator(manager=mgr)
async def create_order(saga: Saga, merchantId: str, orderItems: list[OrderItem]):
    @saga.readiness
    async def check_services():
        _logger.info(f"[{threading.get_ident()}] Wait for other services is startup")
        await asyncio.sleep(3)

    @saga.catch
    async def catch_exception(step, ex):
        _logger.exception(f"Catch `{ex}` at step {step}",exc_info=ex)

    @saga.step
    def get_order_uid() -> uuid.UUID:
        uid = uuid.uuid5(uuid.NAMESPACE_X500, merchantId)
        _logger.info(f"New orderId {uid}")
        return uid

    @saga.step
    def calc_order_total(orderId: Result[uuid.UUID, get_order_uid]) -> float:
        total = sum(item.total for item in orderItems)
        _logger.info(f"Order {orderId} total amount: {total}")
        return total

    @saga.rollback
    def clean_order_data(orderId: Result[uuid.UUID, get_order_uid]) -> bool:
        _logger.info(f"Order {orderId} is rollback")

    @saga.step(retry=3)
    async def save_order(orderTotal: Result[float, calc_order_total], orderId: Result[uuid.UUID, get_order_uid]) -> int:
        
        if str(orderId) == '94f522fc-f802-54d2-a280-b62ae2fa66a4':
            raise Exception('simulate_exception')
        else:
            _logger.info('Wait for 60 sec')
            await asyncio.sleep(60)

        async with aiofiles.open(str(orderId), mode='w',encoding='utf-8') as f:
            await f.write(json.dumps(
                {"merchant": merchantId, "uid":str(orderId),"total": orderTotal, "items": [o.dict() for o in orderItems]}, indent=4))

        _logger.info(f"Successfully wrote to {str(orderId)}")

