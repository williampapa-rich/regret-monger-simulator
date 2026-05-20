from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from regret.domain.dca import DCASpec, expand
from regret.domain.enums import AmountType, Currency, Market, PriceBasis


def _spec(**overrides):
    base = dict(
        market=Market.BINANCE,
        ticker="BTCUSDT",
        start=date(2024, 1, 1),
        end=date(2024, 12, 1),
        frequency="monthly",
        per_period_amount=Decimal("100"),
        currency=Currency.USDT,
        price_basis=PriceBasis.CLOSE,
        fee_rate=Decimal("0.001"),
    )
    base.update(overrides)
    return DCASpec(**base)


def test_monthly_dca_yields_one_purchase_per_month():
    spec = _spec()
    purchases = expand(spec)
    assert len(purchases) == 12
    assert [p.purchase_date.month for p in purchases] == list(range(1, 13))
    assert all(p.purchase_date.day == 1 for p in purchases)


def test_dca_inherits_fee_rate_uniformly():
    spec = _spec(fee_rate=Decimal("0.0007"))
    purchases = expand(spec)
    assert all(p.fee_rate == Decimal("0.0007") for p in purchases)


def test_dca_amounts_sum():
    spec = _spec(per_period_amount=Decimal("100"))
    purchases = expand(spec)
    total = sum((p.amount_value for p in purchases), Decimal("0"))
    assert total == Decimal("1200")


def test_dca_uses_amount_type():
    spec = _spec()
    purchases = expand(spec)
    assert all(p.amount_type is AmountType.AMOUNT for p in purchases)


def test_weekly_frequency():
    spec = _spec(
        start=date(2024, 1, 1),
        end=date(2024, 1, 29),
        frequency="weekly",
    )
    purchases = expand(spec)
    # 1/1, 1/8, 1/15, 1/22, 1/29
    assert [p.purchase_date for p in purchases] == [
        date(2024, 1, 1),
        date(2024, 1, 8),
        date(2024, 1, 15),
        date(2024, 1, 22),
        date(2024, 1, 29),
    ]


def test_daily_frequency():
    spec = _spec(
        start=date(2024, 3, 1),
        end=date(2024, 3, 5),
        frequency="daily",
    )
    purchases = expand(spec)
    assert len(purchases) == 5


def test_monthly_handles_short_month_end():
    """1/31에 시작하면 2/29 (윤년) 또는 2/28로 보정되어야 한다."""
    spec = _spec(
        start=date(2024, 1, 31),  # 2024는 윤년
        end=date(2024, 4, 30),
        frequency="monthly",
    )
    purchases = expand(spec)
    dates = [p.purchase_date for p in purchases]
    assert date(2024, 1, 31) in dates
    assert date(2024, 2, 29) in dates  # 윤년 말일 보정
    assert date(2024, 3, 29) in dates  # 직전 보정값을 따라감


def test_dca_rejects_inverted_range():
    with pytest.raises(ValueError):
        expand(_spec(start=date(2024, 12, 1), end=date(2024, 1, 1)))


def test_dca_single_day_range():
    spec = _spec(start=date(2024, 6, 1), end=date(2024, 6, 1))
    purchases = expand(spec)
    assert len(purchases) == 1
