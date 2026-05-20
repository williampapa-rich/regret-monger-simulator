"""yfinance 어댑터 — 한국 주식·미국 주식·지수.

티커 포맷
- KOSPI: '005930.KS'
- KOSDAQ: '091990.KQ'
- 미국: 'AAPL', '^GSPC' 등 그대로
호출자가 .KS/.KQ 접미사를 붙여 전달한다고 가정. 본 어댑터는 변환하지 않음.
"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pandas as pd

from regret.data.base import OHLC_COLUMNS, PriceFetcher


class YFinanceAdapter(PriceFetcher):
    def get_ohlc(self, ticker: str, start: date, end: date) -> pd.DataFrame:
        import yfinance as yf

        # yfinance의 end는 exclusive — 하루 더해 inclusive로 맞춘다.
        raw = yf.download(
            ticker,
            start=start.isoformat(),
            end=(end + timedelta(days=1)).isoformat(),
            progress=False,
            auto_adjust=False,
            actions=False,
        )
        if raw is None or raw.empty:
            return _empty_frame()

        # MultiIndex 컬럼 평탄화
        if isinstance(raw.columns, pd.MultiIndex):
            raw.columns = raw.columns.get_level_values(0)

        df = pd.DataFrame(index=raw.index.normalize().tz_localize(None))
        df["open"] = raw["Open"].astype(float)
        df["high"] = raw["High"].astype(float)
        df["low"] = raw["Low"].astype(float)
        df["close"] = raw["Close"].astype(float)
        df["adj_close"] = raw["Adj Close"].astype(float) if "Adj Close" in raw.columns else df["close"]
        df["volume"] = raw["Volume"].astype(float) if "Volume" in raw.columns else 0.0
        df = df[OHLC_COLUMNS]
        df.index.name = "date"
        return df

    def get_current_price(self, ticker: str) -> Decimal:
        import yfinance as yf

        info = yf.Ticker(ticker).fast_info
        # fast_info.last_price 는 SDK 버전에 따라 키 이름이 다를 수 있음
        price = getattr(info, "last_price", None) or info.get("lastPrice")
        if price is None:
            raise RuntimeError(f"yfinance: cannot fetch current price for {ticker}")
        return Decimal(str(price))


def _empty_frame() -> pd.DataFrame:
    df = pd.DataFrame(columns=OHLC_COLUMNS)
    df.index = pd.DatetimeIndex([], name="date")
    return df
