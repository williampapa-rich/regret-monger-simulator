"""마켓별 종목명 ↔ 티커 디렉터리.

- 한국 주식: pykrx로 KOSPI/KOSDAQ 전체 종목.
- 미국 주식: NASDAQ Trader의 nasdaqlisted.txt / otherlisted.txt.
- 크립토(Binance/Upbit): 종목명 검색 의미가 약하므로 빈 디렉터리.

디스크 캐시: ~/.regret/cache/tickers/{market}.json (TTL 7일)
"""
from __future__ import annotations

import json
import time
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from regret.domain.enums import Market

CACHE_DIR = Path.home() / ".regret" / "cache" / "tickers"
TTL_SECONDS = 7 * 24 * 3600
NASDAQ_URL = "https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"
NYSE_URL = "https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"


@dataclass(frozen=True)
class Entry:
    ticker: str  # 어댑터에 전달되는 형식 (예: '005930.KS', 'AAPL')
    name: str    # 사용자에게 보이는 종목명


def _cache_path(market: Market) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR / f"{market.value}.json"


def _is_fresh(path: Path) -> bool:
    return path.exists() and (time.time() - path.stat().st_mtime) < TTL_SECONDS


def _load_cache(path: Path) -> list[Entry] | None:
    if not path.exists():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return [Entry(**e) for e in raw]


def _save_cache(path: Path, entries: list[Entry]) -> None:
    path.write_text(
        json.dumps([e.__dict__ for e in entries], ensure_ascii=False),
        encoding="utf-8",
    )


# ---- 마켓별 페치 ---------------------------------------------------------


def _fetch_kospi() -> list[Entry]:
    return _fetch_krx("KOSPI", ".KS")


def _fetch_kosdaq() -> list[Entry]:
    return _fetch_krx("KOSDAQ", ".KQ")


def _fetch_krx(market_name: str, suffix: str) -> list[Entry]:
    from pykrx import stock

    out: list[Entry] = []
    for code in stock.get_market_ticker_list(market=market_name):
        name = stock.get_market_ticker_name(code)
        out.append(Entry(ticker=f"{code}{suffix}", name=name))
    out.sort(key=lambda e: e.name)
    return out


def _fetch_nasdaq() -> list[Entry]:
    return _fetch_nasdaqtrader(NASDAQ_URL, symbol_col=0, name_col=1, etf_col=6)


def _fetch_nyse() -> list[Entry]:
    # otherlisted.txt 컬럼: ACT Symbol|Security Name|Exchange|...|ETF|...
    return _fetch_nasdaqtrader(NYSE_URL, symbol_col=0, name_col=1, etf_col=4, exchange_col=2, exchange_filter="N")


def _fetch_nasdaqtrader(
    url: str,
    symbol_col: int,
    name_col: int,
    etf_col: int,
    exchange_col: int | None = None,
    exchange_filter: str | None = None,
) -> list[Entry]:
    req = urllib.request.Request(url, headers={"User-Agent": "regret-simulator/0.1"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        text = resp.read().decode("utf-8", errors="replace")
    out: list[Entry] = []
    for line in text.strip().split("\n")[1:]:  # 헤더 스킵
        if line.startswith("File Creation Time"):
            break
        parts = line.split("|")
        if len(parts) <= max(symbol_col, name_col, etf_col):
            continue
        if exchange_col is not None and exchange_filter is not None:
            if parts[exchange_col] != exchange_filter:
                continue
        symbol = parts[symbol_col].strip()
        name = parts[name_col].strip()
        if not symbol or "$" in symbol:  # warrant/preferred 제외
            continue
        out.append(Entry(ticker=symbol, name=name))
    out.sort(key=lambda e: e.name)
    return out


def _fetch_upbit() -> list[Entry]:
    import pyupbit

    tickers = pyupbit.get_tickers(fiat="KRW") or []
    out = [Entry(ticker=t, name=t.split("-", 1)[1] if "-" in t else t) for t in tickers]
    out.sort(key=lambda e: e.name)
    return out


def _fetch_binance() -> list[Entry]:
    from binance.client import Client

    info = Client().get_exchange_info()
    out = []
    for s in info["symbols"]:
        if s.get("quoteAsset") == "USDT" and s.get("status") == "TRADING":
            symbol = s["symbol"]
            base = s.get("baseAsset", symbol)
            out.append(Entry(ticker=symbol, name=base))
    out.sort(key=lambda e: e.name)
    return out


_FETCHERS = {
    Market.KOSPI: _fetch_kospi,
    Market.KOSDAQ: _fetch_kosdaq,
    Market.NASDAQ: _fetch_nasdaq,
    Market.NYSE: _fetch_nyse,
    Market.UPBIT: _fetch_upbit,
    Market.BINANCE: _fetch_binance,
}


# ---- 공개 API ------------------------------------------------------------


def get_entries(market: Market, force_refresh: bool = False) -> list[Entry]:
    """종목 디렉터리 반환. 캐시 적중 시 즉시, 미적중·만료 시 페치."""
    if market not in _FETCHERS:
        return []
    path = _cache_path(market)
    if not force_refresh and _is_fresh(path):
        cached = _load_cache(path)
        if cached:
            return cached
    try:
        entries = _FETCHERS[market]()
    except Exception:
        cached = _load_cache(path)
        return cached or []
    _save_cache(path, entries)
    return entries
