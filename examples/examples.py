import asyncio, logging, threading

from ordering import create_order, OrderItem
from man import mgr

logging.basicConfig(level=logging.DEBUG)

async def wait_enter(prompt: str = "Нажмите Enter..."):
    loop = asyncio.get_running_loop()
    print(f"[{threading.get_ident()}] run MAIN {prompt}", flush=True)
    await loop.run_in_executor(None, input)

async def add_task():
    await create_order("ИП Дом", [OrderItem(sku="Товар 1", cost=34.78, quantity=2.67),OrderItem(sku="Товар 2", cost=1.78, quantity=0.56)])
    await create_order("ИП Зоо", [OrderItem(sku="Зоо Товар 1", cost=14.28, quantity=1.67),OrderItem(sku="Зоо Товар 2", cost=0.78, quantity=5.56)])
    
    await wait_enter()

asyncio.run(add_task())

mgr.Stop()