from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from regret.domain.enums import AmountType, Currency, Market, PriceBasis
from regret.domain.models import OHLCRow, Purchase


@pytest.fixture
def ohlc_100_to_200() -> OHLCRow:
    """open=100, close=200 → average=150."""
    return OHLCRow(
        open=Decimal("100"),
        high=Decimal("210"),
        low=Decimal("90"),
        close=Decimal("200"),
    )


@pytest.fixture
def ohlc_flat_100() -> OHLCRow:
    return OHLCRow(
        open=Decimal("100"),
        high=Decimal("100"),
        low=Decimal("100"),
        close=Decimal("100"),
    )


def make_purchase(
    *,
    amount_type: AmountType,
    amount_value: Decimal,
    fee_rate: Decimal,
    price_basis: PriceBasis = PriceBasis.CLOSE,
    market: Market = Market.KOSPI,
    ticker: str = "005930",
    currency: Currency = Currency.KRW,
    purchase_date: date = date(2024, 1, 2),
) -> Purchase:
    return Purchase(
        market=market,
        ticker=ticker,
        purchase_date=purchase_date,
        price_basis=price_basis,
        amount_type=amount_type,
        amount_value=amount_value,
        currency=currency,
        fee_rate=fee_rate,
    )
