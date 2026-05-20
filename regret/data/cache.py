"""디스크 OHLC 캐시 — parquet 기반.

캐시 위치: ~/.regret/cache/
키: '{market}_{safe_ticker}_{start}_{end}.parquet'
TTL: end >= today → 24h (오늘 캔들이 갱신될 수 있음)
     end <  today → 영구 (과거 캔들은 불변)

네트워크 실패 시 폴백
- 캐시가 만료되었더라도 페처가 예외를 던지면 stale 캐시를 반환한다.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd

from regret.data.base import PriceFetcher
from regret.domain.enums import Market

DEFAULT_CACHE_DIR = Path.home() / ".regret" / "cache"
FRESH_TTL = timedelta(hours=24)
_TICKER_SAFE = re.compile(r"[^A-Za-z0-9._-]")


def _safe(ticker: str) -> str:
    return _TICKER_SAFE.sub("_", ticker)


@dataclass
class OHLCCache:
    cache_dir: Path = DEFAULT_CACHE_DIR

    def __post_init__(self) -> None:
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, market: Market, ticker: str, start: date, end: date) -> Path:
        return self.cache_dir / f"{market.value}_{_safe(ticker)}_{start.isoformat()}_{end.isoformat()}.parquet"

    def _is_fresh(self, path: Path, end: date) -> bool:
        if not path.exists():
            return False
        if end < date.today():
            return True  # 종결 윈도우는 영구
        mtime = datetime.fromtimestamp(path.stat().st_mtime)
        return datetime.now() - mtime < FRESH_TTL

    def get_or_fetch(
        self,
        market: Market,
        ticker: str,
        start: date,
        end: date,
        fetcher: PriceFetcher,
    ) -> pd.DataFrame:
        path = self._path(market, ticker, start, end)

        if self._is_fresh(path, end):
            return pd.read_parquet(path)

        try:
            df = fetcher.get_ohlc(ticker, start, end)
        except Exception:
            if path.exists():
                # stale fallback
                return pd.read_parquet(path)
            raise

        df.to_parquet(path)
        return df
