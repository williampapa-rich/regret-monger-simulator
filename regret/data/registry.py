"""Market enum → PriceFetcher 디스패치."""
from __future__ import annotations

from regret.data.base import PriceFetcher
from regret.data.binance_adapter import BinanceAdapter
from regret.data.upbit_adapter import UpbitAdapter
from regret.data.yfinance_adapter import YFinanceAdapter
from regret.domain.enums import Market

_SINGLETONS: dict[Market, PriceFetcher] = {}


def get_fetcher(market: Market) -> PriceFetcher:
    if market not in _SINGLETONS:
        _SINGLETONS[market] = _build(market)
    return _SINGLETONS[market]


def _build(market: Market) -> PriceFetcher:
    if market is Market.BINANCE:
        return BinanceAdapter()
    if market is Market.UPBIT:
        return UpbitAdapter()
    if market in (Market.KOSPI, Market.KOSDAQ, Market.NASDAQ, Market.NYSE):
        return YFinanceAdapter()
    raise ValueError(f"no fetcher for {market}")
