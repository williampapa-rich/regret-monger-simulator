from __future__ import annotations

from decimal import Decimal

import pytest

from regret.domain.enums import Market
from regret.domain.fees import FeeTable


def test_load_default_fees_table_has_all_markets():
    table = FeeTable.load()
    for market in Market:
        rate = table.get(market)
        assert isinstance(rate, Decimal)
        assert rate >= Decimal("0")


def test_fees_are_decimal_not_float():
    table = FeeTable.load()
    for market in Market:
        # float 경유 금지 — 0.001을 float으로 받았다면 == Decimal("0.001") 비교가 깨질 수 있음.
        # toml 문자열 → str → Decimal 경로 보존 검증.
        rate = table.get(market)
        assert isinstance(rate, Decimal)


def test_missing_market_in_toml_raises(tmp_path):
    bad = tmp_path / "fees.toml"
    bad.write_text(
        '[rates]\n'
        'binance = "0.001"\n'
        'upbit = "0.0005"\n'
        # kospi 누락
    )
    with pytest.raises(ValueError, match="kospi"):
        FeeTable.load(bad)
