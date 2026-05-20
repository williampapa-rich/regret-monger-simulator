"""Binance Spot 어댑터 — USDT 페어 일봉.

티커 포맷: 'BTCUSDT', 'ETHUSDT' 등 (Binance symbol).
무인증으로 공개 캔들 호출 가능.
크립토는 24시간 시장 → adj_close = close (배당/액면분할 없음).
시간대는 UTC 자정 기준 캔들.
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal

import pandas as pd

from regret.data.base import OHLC_COLUMNS, PriceFetcher


def _normalize_symbol(ticker: str) -> str:
    """소문자/슬래시/공백을 Binance 형식으로 정규화. 'btc/usdt' → 'BTCUSDT'."""
    return ticker.replace("/", "").replace("-", "").replace(" ", "").upper()


class BinanceAdapter(PriceFetcher):
    def get_ohlc(self, ticker: str, start: date, end: date) -> pd.DataFrame:
        from binance.client import Client

        ticker = _normalize_symbol(ticker)
        client = Client()
        start_ms = int(datetime.combine(start, time(0, 0), tzinfo=timezone.utc).timestamp() * 1000)
        end_ms = int(datetime.combine(end + timedelta(days=1), time(0, 0), tzinfo=timezone.utc).timestamp() * 1000)

        klines = client.get_historical_klines(
            ticker,
            Client.KLINE_INTERVAL_1DAY,
            start_str=start_ms,
            end_str=end_ms,
        )
        if not klines:
            return _empty_frame()

        df = pd.DataFrame(klines, columns=[
            "open_time", "open", "high", "low", "close", "volume",
            "close_time", "_qav", "_trades", "_tbav", "_tqav", "_ignore",
        ])
        df.index = pd.to_datetime(df["open_time"], unit="ms", utc=True).dt.tz_convert(None).dt.normalize()
        df.index.name = "date"
        for col in ("open", "high", "low", "close", "volume"):
            df[col] = df[col].astype(float)
        df["adj_close"] = df["close"]
        return df[OHLC_COLUMNS]

    def get_current_price(self, ticker: str) -> Decimal:
        from binance.client import Client

        ticker_data = Client().get_symbol_ticker(symbol=_normalize_symbol(ticker))
        return Decimal(str(ticker_data["price"]))


def _empty_frame() -> pd.DataFrame:
    df = pd.DataFrame(columns=OHLC_COLUMNS)
    df.index = pd.DatetimeIndex([], name="date")
    return df
