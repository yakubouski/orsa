import httpx
import uuid, json, pathlib
from logging import getLogger
from orsa import orchestrator, Saga, Result

_logger = getLogger('EXAMPLES')

@orchestrator
async def currency_exchange(saga: Saga, amount: float, fromCurrency: str, toCurrency: str):
    @saga.step(retry=3) # Number  of retries for this step
    async def get_exchange_rates() -> dict[str,tuple[float,float]]:
        async with httpx.AsyncClient() as cli:
            res = await cli.get('https://api.nbrb.by/exrates/rates?periodicity=0')
            res.raise_for_status()
            data = res.json()
            _logger.info("Obtain exchange rates ... success (%d)",len(data))
            return { cur['Cur_Abbreviation']: (cur['Cur_OfficialRate'],cur['Cur_Scale']) for cur in data }

    @saga.step
    def register_convert_transaction():
        uidTransaction = uuid.uuid4()
        with open(str(uidTransaction),'tw', encoding='utf-8') as fd:
            fd.write(json.dumps({'uid': str(uidTransaction),'amount': amount, 'from': fromCurrency, 'to': toCurrency}))
            return uidTransaction


    @saga.rollback
    def rollback_register_convert_transaction(uid: Result[uuid.UUID,register_convert_transaction]):
        if pathlib.Path(str(uid)).exists():
            pathlib.Path(str(uid)).unlink()
            _logger.info("Delete incomplete transaction ... success (%s)",str(uid))

    @saga.step
    def convert_to_base_currency(ExchRates: Result[dict[str,tuple[float,float]], get_exchange_rates]) -> float:
        _rate, _scale = ExchRates[fromCurrency]
        _baseAmount = amount * (_rate / _scale)

        if amount > 1000.0:
            """
            Emulate exception for rollback testing
            """
            raise ArithmeticError("More than 1000.0")

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