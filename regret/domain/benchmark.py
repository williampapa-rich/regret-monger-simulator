"""벤치마크 비교 — 같은 시점·금액으로 벤치마크 자산을 샀다면.

v1 결정사항: 동일 통화 자산만 허용 (환율 회피).

도메인 레이어이므로 OHLC 데이터는 외부에서 dict[date, OHLCRow]로 주입받는다.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel

from regret.domain.enums import AmountType, Currency, Market, PriceBasis
from regret.domain.models import OHLCRow, Purchase
from regret.domain.valuation import evaluate


class BenchmarkComparison(BaseModel):
    portfolio_invested: Decimal
    portfolio_value: Decimal
    portfolio_return_pct: Decimal
    benchmark_invested: Decimal
    benchmark_value: Decimal
    benchmark_return_pct: Decimal
    delta_pct: Decimal  # portfolio - benchmark


def compare(
    purchases: list[Purchase],
    portfolio_ohlc: dict[date, OHLCRow],
    portfolio_current_price: Decimal,
    benchmark_market: Market,
    benchmark_ticker: str,
    benchmark_currency: Currency,
    benchmark_ohlc: dict[date, OHLCRow],
    benchmark_current_price: Decimal,
    fee_rate_benchmark: Decimal,
) -> BenchmarkComparison:
    """포트폴리오와 벤치마크 비교.

    - purchases: 단일 자산에 대한 매수 리스트 (DCA 포함). 통화는 모두 동일하다고 가정.
    - benchmark_currency가 purchases의 통화와 다르면 ValueError.
    - 각 Purchase의 (시점, 금액) 그대로 벤치마크 자산을 매수했다고 본다 (price_basis는 종가로 통일,
      AMOUNT 타입으로 변환). QUANTITY 타입 매수는 invested_amount를 기준으로 환산.
    """
    if not purchases:
        raise ValueError("purchases가 비어있음")
    portfolio_currency = purchases[0].currency
    if any(p.currency != portfolio_currency for p in purchases):
        raise ValueError("포트폴리오 내 통화가 일치하지 않음")
    if benchmark_currency != portfolio_currency:
        raise ValueError(
            f"통화 불일치: 포트폴리오={portfolio_currency.value}, 벤치마크={benchmark_currency.value}"
        )

    p_invested = Decimal("0")
    p_value = Decimal("0")
    b_invested = Decimal("0")
    b_value = Decimal("0")

    for p in purchases:
        # 포트폴리오 측
        p_ohlc = portfolio_ohlc[p.purchase_date]
        pv = evaluate(p, p_ohlc, portfolio_current_price)
        p_invested += pv.invested_amount
        p_value += pv.current_value

        # 벤치마크 측 — 같은 시점 같은 금액 (AMOUNT) 매수, 종가 기준
        if p.purchase_date not in benchmark_ohlc:
            raise ValueError(f"벤치마크 OHLC에 {p.purchase_date} 누락")
        b_purchase = Purchase(
            market=benchmark_market,
            ticker=benchmark_ticker,
            purchase_date=p.purchase_date,
            price_basis=PriceBasis.CLOSE,
            amount_type=AmountType.AMOUNT,
            amount_value=pv.invested_amount,  # 동일 투입금액
            currency=benchmark_currency,
            fee_rate=fee_rate_benchmark,
        )
        bv = evaluate(b_purchase, benchmark_ohlc[p.purchase_date], benchmark_current_price)
        b_invested += bv.invested_amount
        b_value += bv.current_value

    p_ret = (p_value / p_invested - Decimal("1")) * Decimal("100")
    b_ret = (b_value / b_invested - Decimal("1")) * Decimal("100")
    return BenchmarkComparison(
        portfolio_invested=p_invested,
        portfolio_value=p_value,
        portfolio_return_pct=p_ret,
        benchmark_invested=b_invested,
        benchmark_value=b_value,
        benchmark_return_pct=b_ret,
        delta_pct=p_ret - b_ret,
    )
