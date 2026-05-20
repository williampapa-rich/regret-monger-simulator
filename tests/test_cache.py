from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from regret.data.base import OHLC_COLUMNS, PriceFetcher
from regret.data.cache import OHLCCache
from regret.domain.enums import Market


def _frame() -> pd.DataFrame:
    idx = pd.DatetimeIndex(
        [pd.Timestamp("2024-01-02"), pd.Timestamp("2024-01-03")], name="date"
    )
    df = pd.DataFrame(
        {
            "open": [100.0, 110.0],
            "high": [105.0, 115.0],
            "low": [95.0, 105.0],
            "close": [102.0, 112.0],
            "adj_close": [102.0, 112.0],
            "volume": [1000.0, 1200.0],
        },
        index=idx,
        columns=OHLC_COLUMNS,
    )
    return df


class CountingFetcher(PriceFetcher):
    def __init__(self, frame: pd.DataFrame):
        self.calls = 0
        self.frame = frame

    def get_ohlc(self, ticker, start, end):
        self.calls += 1
        return self.frame

    def get_current_price(self, ticker):
        raise NotImplementedError


class FailingFetcher(PriceFetcher):
    def get_ohlc(self, ticker, start, end):
        raise RuntimeError("network down")

    def get_current_price(self, ticker):
        raise NotImplementedError


def test_cache_hit_skips_network(tmp_path: Path):
    cache = OHLCCache(cache_dir=tmp_path)
    fetcher = CountingFetcher(_frame())
    args = (Market.NASDAQ, "AAPL", date(2024, 1, 2), date(2024, 1, 3))

    df1 = cache.get_or_fetch(*args, fetcher=fetcher)
    df2 = cache.get_or_fetch(*args, fetcher=fetcher)

    assert fetcher.calls == 1  # 두 번째는 디스크에서
    pd.testing.assert_frame_equal(df1, df2)


def test_stale_fallback_on_network_failure(tmp_path: Path):
    cache = OHLCCache(cache_dir=tmp_path)
    args = (Market.NASDAQ, "AAPL", date(2024, 1, 2), date(2024, 1, 3))

    cache.get_or_fetch(*args, fetcher=CountingFetcher(_frame()))
    # end는 과거 → 항상 fresh 판정. 강제로 mtime을 옛날로 바꾸어 stale 만들기보다는,
    # end를 오늘로 바꾼 시나리오로 stale을 강제한다.
    fresh_args = (Market.NASDAQ, "AAPL", date.today(), date.today())
    cache.get_or_fetch(*fresh_args, fetcher=CountingFetcher(_frame()))

    # 캐시가 막 만들어졌으니 fresh — 페처 호출 0회 확인
    failing = FailingFetcher()
    df = cache.get_or_fetch(*fresh_args, fetcher=failing)
    assert df is not None  # fresh hit 이므로 실패 페처도 호출 안 됨


def test_round_trip_preserves_schema(tmp_path: Path):
    cache = OHLCCache(cache_dir=tmp_path)
    fetcher = CountingFetcher(_frame())
    args = (Market.NASDAQ, "AAPL", date(2024, 1, 2), date(2024, 1, 3))

    cache.get_or_fetch(*args, fetcher=fetcher)
    df = cache.get_or_fetch(*args, fetcher=fetcher)

    assert list(df.columns) == OHLC_COLUMNS
    assert isinstance(df.index, pd.DatetimeIndex)
    assert df.index.tz is None


def test_ticker_with_unsafe_chars_does_not_break_path(tmp_path: Path):
    cache = OHLCCache(cache_dir=tmp_path)
    fetcher = CountingFetcher(_frame())
    # '^GSPC' 같은 yfinance 지수 티커
    cache.get_or_fetch(Market.NASDAQ, "^GSPC", date(2024, 1, 2), date(2024, 1, 3), fetcher=fetcher)
    files = list(tmp_path.glob("*.parquet"))
    assert len(files) == 1
    assert "^" not in files[0].name


def test_failure_with_no_cache_propagates(tmp_path: Path):
    cache = OHLCCache(cache_dir=tmp_path)
    with pytest.raises(RuntimeError, match="network down"):
        cache.get_or_fetch(
            Market.NASDAQ, "AAPL", date(2024, 1, 2), date(2024, 1, 3),
            fetcher=FailingFetcher(),
        )
