"""DCA(분할매수) 헬퍼 — DCASpec → list[Purchase].

휴장일 처리는 호출자(UI) 책임. 본 모듈은 캘린더 무지하게
명시된 주기로 일자만 펼친다. 영업일 스냅이 필요하면 펼친 일자에
calendar 헬퍼를 적용해 dataclass-replace로 보정해 호출하면 된다.
"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel

from regret.domain.enums import AmountType, Currency, Market, PriceBasis
from regret.domain.models import Purchase

Frequency = Literal["daily", "weekly", "monthly"]


class DCASpec(BaseModel):
    market: Market
    ticker: str
    start: date
    end: date
    frequency: Frequency
    per_period_amount: Decimal
    currency: Currency
    price_basis: PriceBasis
    fee_rate: Decimal


def _next_date(d: date, freq: Frequency) -> date:
    if freq == "daily":
        return d + timedelta(days=1)
    if freq == "weekly":
        return d + timedelta(days=7)
    if freq == "monthly":
        # 같은 day-of-month 유지. 말일 처리: 해당 월에 그 일자가 없으면 그 월의 말일.
        year = d.year + (1 if d.month == 12 else 0)
        month = 1 if d.month == 12 else d.month + 1
        day = d.day
        # 말일 보정
        while True:
            try:
                return date(year, month, day)
            except ValueError:
                day -= 1
    raise ValueError(f"unknown frequency: {freq}")


def expand(spec: DCASpec) -> list[Purchase]:
    if spec.start > spec.end:
        raise ValueError("DCA start는 end보다 빠르거나 같아야 함")

    purchases: list[Purchase] = []
    d = spec.start
    while d <= spec.end:
        purchases.append(
            Purchase(
                market=spec.market,
                ticker=spec.ticker,
                purchase_date=d,
                price_basis=spec.price_basis,
                amount_type=AmountType.AMOUNT,
                amount_value=spec.per_period_amount,
                currency=spec.currency,
                fee_rate=spec.fee_rate,
            )
        )
        d = _next_date(d, spec.frequency)
    return purchases
