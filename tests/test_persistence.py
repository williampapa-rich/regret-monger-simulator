from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

from regret.domain.enums import AmountType, Currency, Market, PriceBasis
from regret.domain.models import Portfolio, Purchase
from regret.persistence.portfolio_io import load, save


def test_round_trip_portfolio(tmp_path: Path):
    purchase = Purchase(
        market=Market.KOSPI,
        ticker="005930.KS",
        purchase_date=date(2024, 1, 2),
        price_basis=PriceBasis.CLOSE,
        amount_type=AmountType.AMOUNT,
        amount_value=Decimal("1000000"),
        currency=Currency.KRW,
        fee_rate=Decimal("0.00015"),
        memo="삼성전자 1차",
    )
    pf = Portfolio(
        name="테스트 포트폴리오",
        purchases=[purchase],
        benchmark_market=Market.KOSPI,
        benchmark_ticker="069500.KS",
    )
    target = tmp_path / "pf.json"
    save(pf, target)
    restored = load(target)

    assert restored.name == "테스트 포트폴리오"
    assert len(restored.purchases) == 1
    p = restored.purchases[0]
    assert p.amount_value == Decimal("1000000")  # Decimal 보존
    assert p.fee_rate == Decimal("0.00015")
    assert p.purchase_date == date(2024, 1, 2)
    assert p.market is Market.KOSPI
    assert p.memo == "삼성전자 1차"
    assert restored.benchmark_ticker == "069500.KS"
