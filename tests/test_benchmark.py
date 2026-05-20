from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from regret.domain.benchmark import compare
from regret.domain.enums import AmountType, Currency, Market, PriceBasis
from regret.domain.models import OHLCRow
from tests.conftest import make_purchase


def _flat(open_=100, close_=100):
    return OHLCRow(
        open=Decimal(str(open_)),
        high=Decimal(str(close_)),
        low=Decimal(str(open_)),
        close=Decimal(str(close_)),
    )


def test_currency_mismatch_raises():
    p = make_purchase(
        amount_type=AmountType.AMOUNT,
        amount_value=Decimal("1000000"),
        fee_rate=Decimal("0"),
        currency=Currency.KRW,
        market=Market.KOSPI,
        purchase_date=date(2024, 1, 2),
    )
    with pytest.raises(ValueError, match="통화 불일치"):
        compare(
            purchases=[p],
            portfolio_ohlc={date(2024, 1, 2): _flat(100, 100)},
            portfolio_current_price=Decimal("150"),
            benchmark_market=Market.NASDAQ,
            benchmark_ticker="SPY",
            benchmark_currency=Currency.USD,  # KRW vs USD
            benchmark_ohlc={date(2024, 1, 2): _flat(400, 400)},
            benchmark_current_price=Decimal("500"),
            fee_rate_benchmark=Decimal("0"),
        )


def test_compare_return_pcts_zero_fee():
    """KRW 단일자산 +50%, KOSPI200 +25% → delta = 25."""
    p = make_purchase(
        amount_type=AmountType.AMOUNT,
        amount_value=Decimal("1000000"),
        fee_rate=Decimal("0"),
        currency=Currency.KRW,
        market=Market.KOSPI,
        purchase_date=date(2024, 1, 2),
        price_basis=PriceBasis.CLOSE,
    )
    cmp = compare(
        purchases=[p],
        portfolio_ohlc={date(2024, 1, 2): _flat(100, 100)},
        portfolio_current_price=Decimal("150"),
        benchmark_market=Market.KOSPI,
        benchmark_ticker="069500.KS",
        benchmark_currency=Currency.KRW,
        benchmark_ohlc={date(2024, 1, 2): _flat(400, 400)},
        benchmark_current_price=Decimal("500"),
        fee_rate_benchmark=Decimal("0"),
    )
    assert cmp.portfolio_return_pct == Decimal("50")
    assert cmp.benchmark_return_pct == Decimal("25")
    assert cmp.delta_pct == Decimal("25")


def test_compare_empty_raises():
    with pytest.raises(ValueError, match="비어"):
        compare(
            purchases=[],
            portfolio_ohlc={},
            portfolio_current_price=Decimal("100"),
            benchmark_market=Market.KOSPI,
            benchmark_ticker="X",
            benchmark_currency=Currency.KRW,
            benchmark_ohlc={},
            benchmark_current_price=Decimal("100"),
            fee_rate_benchmark=Decimal("0"),
        )


def test_compare_missing_benchmark_ohlc_raises():
    p = make_purchase(
        amount_type=AmountType.AMOUNT,
        amount_value=Decimal("1000"),
        fee_rate=Decimal("0"),
        currency=Currency.KRW,
        market=Market.KOSPI,
        purchase_date=date(2024, 1, 2),
    )
    with pytest.raises(ValueError, match="벤치마크 OHLC"):
        compare(
            purchases=[p],
            portfolio_ohlc={date(2024, 1, 2): _flat()},
            portfolio_current_price=Decimal("100"),
            benchmark_market=Market.KOSPI,
            benchmark_ticker="X",
            benchmark_currency=Currency.KRW,
            benchmark_ohlc={},  # 누락
            benchmark_current_price=Decimal("100"),
            fee_rate_benchmark=Decimal("0"),
        )
