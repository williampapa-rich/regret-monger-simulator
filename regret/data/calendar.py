"""영업일 캘린더 헬퍼.

별도 휴장일 DB를 두지 않고, OHLC DataFrame의 index 자체를 진실의 원천으로 사용한다.
크립토는 매일이 영업일이므로 모든 일자가 통과한다.
"""
from __future__ import annotations

from datetime import date

import pandas as pd


def is_trading_day(target: date, ohlc: pd.DataFrame) -> bool:
    return pd.Timestamp(target) in ohlc.index


def nearest_before(target: date, ohlc: pd.DataFrame) -> date | None:
    candidates = ohlc.index[ohlc.index <= pd.Timestamp(target)]
    if len(candidates) == 0:
        return None
    return candidates.max().date()


def nearest_after(target: date, ohlc: pd.DataFrame) -> date | None:
    candidates = ohlc.index[ohlc.index >= pd.Timestamp(target)]
    if len(candidates) == 0:
        return None
    return candidates.min().date()
