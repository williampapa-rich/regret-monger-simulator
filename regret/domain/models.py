from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from regret.domain.enums import AmountType, Currency, Market, PriceBasis


class Purchase(BaseModel):
    """매수 한 건. fee_rate를 시점별로 박아두어 정책 변경 후에도 재현 가능."""

    id: UUID = Field(default_factory=uuid4)
    market: Market
    ticker: str
    purchase_date: date
    price_basis: PriceBasis
    amount_type: AmountType
    amount_value: Decimal
    currency: Currency
    fee_rate: Decimal
    memo: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)


class OHLCRow(BaseModel):
    """매수일 시·종·평균가 결정에 필요한 한 캔들의 raw OHLC."""

    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal


class PurchaseValuation(BaseModel):
    """Purchase 한 건의 평가 결과 (계산값)."""

    purchase: Purchase
    applied_buy_price: Decimal
    quantity: Decimal
    invested_amount: Decimal
    cash_remainder: Decimal = Decimal("0")  # 정수매매 마켓에서 매수 후 남은 현금
    current_price: Decimal
    current_value: Decimal
    gross_return_pct: Decimal
    net_return_pct: Decimal


class Portfolio(BaseModel):
    name: str = "내 껄무새"
    purchases: list[Purchase] = Field(default_factory=list)
    benchmark_market: Optional[Market] = None
    benchmark_ticker: Optional[str] = None
