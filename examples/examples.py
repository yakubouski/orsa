import asyncio, logging, threading
from shared.manager import manager as ManagerSaga
from _1_sample_saga import currency_exchange as SampleSaga
from _2_rollback_saga import currency_exchange as SampleSagaWithRollback
from _3_sample_saga_manager import currency_exchange as SampleSagaWithManager

logging.basicConfig(level=logging.INFO)

async def wait_enter(prompt: str = "Нажмите Enter..."):
    loop = asyncio.get_running_loop()
    print(f"[{threading.get_ident()}] run MAIN {prompt}", flush=True)
    await loop.run_in_executor(None, input)

async def add_task():
    await SampleSaga(45.12,'USD','CNY')
    await SampleSagaWithRollback(145.12,'USD','CNY')
    
    try:
        await SampleSagaWithRollback(1003.12,'USD','CNY')
    except:
        ...

    await SampleSagaWithManager(89.23,'CNY','USD')
    await SampleSagaWithManager(4679.45,'CNY','EUR')

    #await create_order("ИП Дом", [OrderItem(sku="Товар 1", cost=34.78, quantity=2.67),OrderItem(sku="Товар 2", cost=1.78, quantity=0.56)])
    #await create_order("ИП Зоо", [OrderItem(sku="Зоо Товар 1", cost=14.28, quantity=1.67),OrderItem(sku="Зоо Товар 2", cost=0.78, quantity=5.56)])
    
    await wait_enter()

if __name__ == "__main__":
    asyncio.run(add_task())
    ManagerSaga.Stop()