from __future__ import annotations

from enum import Enum


class Market(str, Enum):
    BINANCE = "binance"
    UPBIT = "upbit"
    KOSPI = "kospi"
    KOSDAQ = "kosdaq"
    NASDAQ = "nasdaq"
    NYSE = "nyse"


class PriceBasis(str, Enum):
    OPEN = "open"
    CLOSE = "close"
    AVERAGE = "average"  # (open + close) / 2


class AmountType(str, Enum):
    QUANTITY = "quantity"
    AMOUNT = "amount"


class Currency(str, Enum):
    KRW = "KRW"
    USD = "USD"
    USDT = "USDT"


# 소수점 매매 불가 (정수 주식 매매) 마켓.
# 크립토(BINANCE/UPBIT)는 소수점 매매 가능.
INTEGER_QUANTITY_MARKETS: frozenset[Market] = frozenset({
    Market.KOSPI, Market.KOSDAQ, Market.NASDAQ, Market.NYSE,
})
