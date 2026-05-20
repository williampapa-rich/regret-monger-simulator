from __future__ import annotations

from decimal import Decimal

import pytest

from regret.domain.enums import AmountType, Currency, Market, PriceBasis
from regret.domain.valuation import evaluate
from tests.conftest import make_purchase


# ---- price_basis -----------------------------------------------------------


def test_price_basis_open(ohlc_100_to_200):
    p = make_purchase(
        amount_type=AmountType.AMOUNT,
        amount_value=Decimal("1000"),
        fee_rate=Decimal("0"),
        price_basis=PriceBasis.OPEN,
    )
    v = evaluate(p, ohlc_100_to_200, current_price=Decimal("100"))
    assert v.applied_buy_price == Decimal("100")


def test_price_basis_close(ohlc_100_to_200):
    p = make_purchase(
        amount_type=AmountType.AMOUNT,
        amount_value=Decimal("1000"),
        fee_rate=Decimal("0"),
        price_basis=PriceBasis.CLOSE,
    )
    v = evaluate(p, ohlc_100_to_200, current_price=Decimal("100"))
    assert v.applied_buy_price == Decimal("200")


def test_price_basis_average(ohlc_100_to_200):
    p = make_purchase(
        amount_type=AmountType.AMOUNT,
        amount_value=Decimal("1000"),
        fee_rate=Decimal("0"),
        price_basis=PriceBasis.AVERAGE,
    )
    v = evaluate(p, ohlc_100_to_200, current_price=Decimal("100"))
    assert v.applied_buy_price == Decimal("150")


# ---- 수수료 0% → gross == net ---------------------------------------------


def test_zero_fee_gross_equals_net(ohlc_flat_100):
    p = make_purchase(
        amount_type=AmountType.AMOUNT,
        amount_value=Decimal("1000000"),
        fee_rate=Decimal("0"),
    )
    v = evaluate(p, ohlc_flat_100, current_price=Decimal("150"))
    assert v.gross_return_pct == v.net_return_pct == Decimal("50")
    assert v.quantity == Decimal("10000")
    assert v.invested_amount == Decimal("1000000")
    assert v.current_value == Decimal("1500000")


# ---- AMOUNT + 수수료 0.1% (손계산 일치) -----------------------------------


def test_amount_integer_market_handcalc(ohlc_flat_100):
    """KOSPI(정수매매), M=1,000,000, fee=0.1%, applied=100.
    unit_cost = 100.1, quantity = floor(1,000,000/100.1) = 9990
    spent = 999,999, cash_remainder = 1
    stock_value = 9990 × 150 × 0.999 = 1,497,001.5
    current_value = 1,497,002.5
    net = 49.70025
    """
    p = make_purchase(
        amount_type=AmountType.AMOUNT,
        amount_value=Decimal("1000000"),
        fee_rate=Decimal("0.001"),
        market=Market.KOSPI,
    )
    v = evaluate(p, ohlc_flat_100, current_price=Decimal("150"))

    assert v.quantity == Decimal("9990")
    assert v.cash_remainder == Decimal("1")
    assert v.invested_amount == Decimal("1000000")
    assert v.current_value == Decimal("1497002.5000")
    assert v.gross_return_pct == Decimal("50")
    assert v.net_return_pct == Decimal("49.70025")


def test_integer_market_with_remainder(ohlc_flat_100):
    """KOSPI, M=1,000, fee=0, applied=300.
    quantity = floor(1000/300) = 3, spent = 900, cash_remainder = 100.
    """
    p = make_purchase(
        amount_type=AmountType.AMOUNT,
        amount_value=Decimal("1000"),
        fee_rate=Decimal("0"),
        market=Market.KOSPI,
    )
    ohlc = ohlc_flat_100.model_copy(update={
        "open": Decimal("300"), "high": Decimal("300"),
        "low": Decimal("300"), "close": Decimal("300"),
    })
    v = evaluate(p, ohlc, current_price=Decimal("400"))
    assert v.quantity == Decimal("3")
    assert v.cash_remainder == Decimal("100")
    assert v.current_value == Decimal("1300")  # 3 × 400 + 100


def test_amount_crypto_allows_fractional(ohlc_flat_100):
    """크립토 마켓은 종전 모델 그대로. cash_remainder 0."""
    p = make_purchase(
        amount_type=AmountType.AMOUNT,
        amount_value=Decimal("1000000"),
        fee_rate=Decimal("0.001"),
        market=Market.BINANCE,
        currency=Currency.USDT,
    )
    v = evaluate(p, ohlc_flat_100, current_price=Decimal("150"))

    assert v.quantity == Decimal("9990")
    assert v.cash_remainder == Decimal("0")
    assert v.invested_amount == Decimal("1000000")
    assert v.current_value == Decimal("1497001.500")
    assert v.net_return_pct == Decimal("49.70015")


# ---- QUANTITY + 수수료 0.1% (손계산 일치) ---------------------------------


def test_quantity_with_fee_handcalc(ohlc_flat_100):
    """
    N = 10주, fee = 0.1%, 매수단가 100원.
    invested = 10 × 100 × 1.001 = 1,001
    현재가 150원, 매도 수수료 0.1%
    current_value = 10 × 150 × 0.999 = 1,498.500
    net = (1,498.5 / 1,001 - 1) × 100
    gross = 50
    """
    p = make_purchase(
        amount_type=AmountType.QUANTITY,
        amount_value=Decimal("10"),
        fee_rate=Decimal("0.001"),
    )
    v = evaluate(p, ohlc_flat_100, current_price=Decimal("150"))

    assert v.quantity == Decimal("10")
    assert v.invested_amount == Decimal("1001.000")
    assert v.current_value == Decimal("1498.500")
    assert v.gross_return_pct == Decimal("50")
    expected_net = (Decimal("1498.500") / Decimal("1001.000") - Decimal("1")) * Decimal("100")
    assert v.net_return_pct == expected_net


# ---- 타입 가드 ------------------------------------------------------------


def test_current_price_must_be_decimal(ohlc_flat_100):
    p = make_purchase(
        amount_type=AmountType.AMOUNT,
        amount_value=Decimal("1000"),
        fee_rate=Decimal("0"),
    )
    with pytest.raises(TypeError):
        evaluate(p, ohlc_flat_100, current_price=150.0)  # type: ignore[arg-type]
