"""Purchase 한 건의 평가 계산.

도메인 레이어는 네트워크에 무지하다 — 매수일 OHLC와 현재가를 외부에서 주입받는다.

수익률 정의
- gross_return_pct: 가격 변동만 본 수익률 (수수료 무시).
- net_return_pct: 수수료 + 정수매매 잔돈 모두 반영한 실제 손익 비율.
  invested(=총 투입) 대비 (주식 평가액 + 현금잔액).

수수료 / 정수매매 규칙
- 정수매매 마켓(주식)은 quantity가 정수.
  AMOUNT 입력 시: quantity = floor(M / applied), 매수 실제지출 = q × applied × (1+fee),
  cash_remainder = M - 매수 실제지출. 음수가 되면 한 주 덜 사도록 자동 조정.
- 소수점 매매 가능 마켓(크립토): 종전 로직 유지.
- QUANTITY 입력은 사용자가 명시적으로 정수 N주를 지정한 것.
- 매도 측: current_value = quantity × current_price × (1 - fee_rate) + cash_remainder.
"""
from __future__ import annotations

from decimal import Decimal

from regret.domain.enums import INTEGER_QUANTITY_MARKETS, AmountType, PriceBasis
from regret.domain.models import OHLCRow, Purchase, PurchaseValuation

_TWO = Decimal("2")
_HUNDRED = Decimal("100")
_ONE = Decimal("1")
_ZERO = Decimal("0")


def _applied_price(ohlc: OHLCRow, basis: PriceBasis) -> Decimal:
    if basis is PriceBasis.OPEN:
        return ohlc.open
    if basis is PriceBasis.CLOSE:
        return ohlc.close
    if basis is PriceBasis.AVERAGE:
        return (ohlc.open + ohlc.close) / _TWO
    raise ValueError(f"unknown basis: {basis}")


def evaluate(
    purchase: Purchase,
    ohlc_at_buy: OHLCRow,
    current_price: Decimal,
) -> PurchaseValuation:
    if not isinstance(current_price, Decimal):
        raise TypeError("current_price must be Decimal")

    fee = purchase.fee_rate
    applied = _applied_price(ohlc_at_buy, purchase.price_basis)
    integer_only = purchase.market in INTEGER_QUANTITY_MARKETS

    cash_remainder = _ZERO

    if purchase.amount_type is AmountType.QUANTITY:
        quantity = purchase.amount_value
        if integer_only:
            # 사용자가 입력한 수량이 소수면 정수로 절단.
            quantity = quantity.to_integral_value(rounding="ROUND_DOWN")
        invested = quantity * applied * (_ONE + fee)
    else:
        target_amount = purchase.amount_value
        if integer_only:
            # floor로 한 주 단위 매수. 수수료 포함해도 target을 넘지 않도록 보정.
            unit_cost = applied * (_ONE + fee)
            quantity = (target_amount / unit_cost).to_integral_value(rounding="ROUND_DOWN")
            spent = quantity * unit_cost
            cash_remainder = target_amount - spent
            invested = target_amount  # 사용자가 투입한 총액 (현금잔액 포함)
        else:
            invested = target_amount
            quantity = (invested * (_ONE - fee)) / applied

    stock_value = quantity * current_price * (_ONE - fee)
    current_value = stock_value + cash_remainder

    gross_return_pct = (current_price / applied - _ONE) * _HUNDRED
    if invested > 0:
        net_return_pct = (current_value / invested - _ONE) * _HUNDRED
    else:
        net_return_pct = _ZERO

    return PurchaseValuation(
        purchase=purchase,
        applied_buy_price=applied,
        quantity=quantity,
        invested_amount=invested,
        cash_remainder=cash_remainder,
        current_price=current_price,
        current_value=current_value,
        gross_return_pct=gross_return_pct,
        net_return_pct=net_return_pct,
    )
