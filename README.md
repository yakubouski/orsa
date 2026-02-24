# ORSA (<u>OR</u>chestrator <u>SA</u>ga)

This module provides a flexible and extensible framework for implementing Saga patterns in Python.  
It enables coordination of complex business transactions spanning multiple services, ensuring eventual consistency through choreography and compensation mechanisms.  

### Key features include:

* **Simplified Saga Declaration** - Streamlined saga declaration using decorators and intuitive syntaxis, enabling rapid creation of complex distributed transactions

* **Saga Orchestration** - Full-featured saga orchestration with support for complex execution scenarios, including parallel and sequential operations

* **Extensible Saga Execution Manager** - Extendable saga execution manager with customizable execution strategies and error handling capabilities

* **Compensation Logic Management** - Automated compensation logic management with support for compensation chains and complex rollback scenarios

* **Asynchronous Execution** - Asynchronous saga execution support with handling of long-running operations and events

* **Readiness Probe Before Saga Execution** - Pre-execution system readiness checks with automatic dependency and resource discovery

### Example

`saga_example.py`

```Python
import httpx
from logging import getLogger
from orsa import orchestrator, Saga, Result

_logger = getLogger('EXAMPLES')

@orchestrator
async def currency_exchange(saga: Saga, amount: float, fromCurrency: str, toCurrency: str):
    """
    Sample Saga. Exchange from currencies
    """
    @saga.step(retry=3) # Number  of retries for this step
    async def get_exchange_rates() -> dict[str,tuple[float,float]]:
        async with httpx.AsyncClient() as cli:
            res = await cli.get('https://api.nbrb.by/exrates/rates?periodicity=0')
            res.raise_for_status()
            data = res.json()
            _logger.info("Obtain exchange rates ... success (%d)",len(data))
            return { cur['Cur_Abbreviation']: (cur['Cur_OfficialRate'],cur['Cur_Scale']) for cur in data }

    @saga.step
    def convert_to_base_currency(ExchRates: Result[dict[str,tuple[float,float]], get_exchange_rates]) -> float:
        _rate, _scale = ExchRates[fromCurrency]
        _baseAmount = amount * (_rate / _scale)

        _logger.info("Convert %.3f (%s) to %.3f (BYN) ... rate (%.3f)",amount, fromCurrency, _baseAmount, (_rate / _scale))

        return _baseAmount

    @saga.step
    def convert_to_dst_currency(
            BaseAmount: Result[float,convert_to_base_currency], 
            ExchRates: Result[dict[str,tuple[float,float]], get_exchange_rates]) -> float:

        _rate, _scale = ExchRates[toCurrency]
        _dstAmount = BaseAmount / (_rate / _scale)

        _logger.info("Convert %.3f (%s) to %.3f (%s)",amount, fromCurrency, _dstAmount, toCurrency)

        return _dstAmount
```

`main.py`
```Python
import asyncio, logging
from saga_example import currency_exchange

logging.basicConfig(level=logging.INFO)

async def add_task():
    await currency_exchange(45.12,'USD','CNY')

if __name__ == "__main__":
    asyncio.run(add_task())
```

[See other examples](https://github.com/yakubouski/orsa/)

### License

[MIT License](LICENSE.txt)