"""PriceFetcher 추상 베이스 + 통일 OHLC DataFrame 스키마.

스키마 (어댑터 구현이 반드시 따라야 함)
- index: pandas DatetimeIndex, tz-naive, normalize된 일자 (시간정보 0)
- columns: ['open', 'high', 'low', 'close', 'adj_close', 'volume']
- adj_close가 없는 마켓(크립토)은 close 값을 그대로 복사

수익률 계산은 호출자가 adj_close를 사용한다. 매수단가 표시는 raw close.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date
from decimal import Decimal

import pandas as pd

OHLC_COLUMNS = ["open", "high", "low", "close", "adj_close", "volume"]


class PriceFetcher(ABC):
    @abstractmethod
    def get_ohlc(self, ticker: str, start: date, end: date) -> pd.DataFrame:
        """[start, end] 구간(end 포함)의 일봉 OHLC."""

    @abstractmethod
    def get_current_price(self, ticker: str) -> Decimal:
        """현재 시점 마지막 체결가."""


def validate_ohlc_frame(df: pd.DataFrame) -> None:
    """어댑터 구현·캐시 라운드트립의 스키마 가드 (개발용 sanity check)."""
    if not isinstance(df.index, pd.DatetimeIndex):
        raise ValueError("OHLC index must be DatetimeIndex")
    if df.index.tz is not None:
        raise ValueError("OHLC index must be tz-naive")
    missing = [c for c in OHLC_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"OHLC frame missing columns: {missing}")
