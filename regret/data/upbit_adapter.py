"""Upbit 어댑터 — KRW 페어 일봉.

티커 포맷: 'KRW-BTC', 'KRW-ETH' 등 (Upbit symbol).
pyupbit는 무인증으로 캔들 호출 가능.
시간대는 KST 자정 기준이지만 본 어댑터는 tz-naive date로 normalize.
"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pandas as pd

from regret.data.base import OHLC_COLUMNS, PriceFetcher


class UpbitAdapter(PriceFetcher):
    def get_ohlc(self, ticker: str, start: date, end: date) -> pd.DataFrame:
        import pyupbit

        days = (end - start).days + 1
        # pyupbit.get_ohlcv: count는 'to' 시점 기준 이전 N일.
        to_str = (end + timedelta(days=1)).strftime("%Y%m%d")
        raw = pyupbit.get_ohlcv(ticker, count=days, to=to_str, interval="day")
        if raw is None or raw.empty:
            return _empty_frame()

        # pyupbit는 이미 open/high/low/close/volume 컬럼을 갖고 있고
        # 인덱스는 KST 자정(09:00 UTC) timestamp. .normalize()로 시각 0으로 떨군다.
        df = raw[["open", "high", "low", "close", "volume"]].astype(float).copy()
        df.index = df.index.normalize()
        df.index.name = "date"
        df["adj_close"] = df["close"]
        df = df[OHLC_COLUMNS]
        # start 이전 데이터가 섞여 들어올 수 있어 잘라낸다.
        return df[df.index >= pd.Timestamp(start)]

    def get_current_price(self, ticker: str) -> Decimal:
        import pyupbit

        price = pyupbit.get_current_price(ticker)
        if price is None:
            raise RuntimeError(f"pyupbit: cannot fetch current price for {ticker}")
        return Decimal(str(price))


def _empty_frame() -> pd.DataFrame:
    df = pd.DataFrame(columns=OHLC_COLUMNS)
    df.index = pd.DatetimeIndex([], name="date")
    return df
