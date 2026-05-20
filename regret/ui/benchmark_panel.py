"""벤치마크 비교 패널.

동일 통화 자산만 허용 — 통화 불일치 시 'Compare' 버튼 비활성화.
"""
from __future__ import annotations

from decimal import Decimal

from PyQt6 import QtCore, QtWidgets

from regret.data.ticker_directory import Entry
from regret.domain.benchmark import BenchmarkComparison
from regret.domain.enums import Currency, Market
from regret.ui.widgets.ticker_combo import TickerCombo

# 마켓별 통화 (단일 통화 마켓 가정)
_MARKET_CURRENCY: dict[Market, Currency] = {
    Market.BINANCE: Currency.USDT,
    Market.UPBIT: Currency.KRW,
    Market.KOSPI: Currency.KRW,
    Market.KOSDAQ: Currency.KRW,
    Market.NASDAQ: Currency.USD,
    Market.NYSE: Currency.USD,
}

def market_currency(market: Market) -> Currency:
    return _MARKET_CURRENCY[market]


class BenchmarkPanel(QtWidgets.QGroupBox):
    compare_requested = QtCore.pyqtSignal(Market, str)

    def __init__(self, parent=None):
        super().__init__("벤치마크 비교", parent=parent)
        layout = QtWidgets.QFormLayout(self)

        self.market_combo = QtWidgets.QComboBox()
        for m in Market:
            self.market_combo.addItem(m.value, m)
        layout.addRow("벤치마크 마켓", self.market_combo)

        self.ticker_combo = TickerCombo()
        self.ticker_combo.setMinimumWidth(280)
        layout.addRow("벤치마크 종목", self.ticker_combo)

        self.compare_button = QtWidgets.QPushButton("비교")
        layout.addRow(self.compare_button)

        self.result_label = QtWidgets.QLabel("결과 없음")
        self.result_label.setWordWrap(True)
        layout.addRow(self.result_label)

        self._portfolio_currency: Currency | None = None
        self.market_combo.currentIndexChanged.connect(self._refresh_button_state)
        self.market_combo.currentIndexChanged.connect(self._on_market_changed)
        self.compare_button.clicked.connect(self._emit_compare)

    def _on_market_changed(self) -> None:
        # 모든 마켓에서 directory를 MainWindow가 주입함.
        pass

    def set_directory(self, entries: list[Entry]) -> None:
        self.ticker_combo.set_entries(entries)

    def market(self) -> Market:
        return self.market_combo.currentData()

    def set_portfolio_currency(self, currency: Currency | None) -> None:
        self._portfolio_currency = currency
        self._refresh_button_state()

    def _refresh_button_state(self) -> None:
        if self._portfolio_currency is None:
            self.compare_button.setEnabled(False)
            self.result_label.setText("매수가 비어있습니다")
            return
        b_currency = market_currency(self.market_combo.currentData())
        if b_currency != self._portfolio_currency:
            self.compare_button.setEnabled(False)
            self.result_label.setText(
                f"통화 불일치: 포트폴리오 {self._portfolio_currency.value} vs 벤치마크 {b_currency.value}"
            )
        else:
            self.compare_button.setEnabled(True)
            self.result_label.setText("준비")

    def _emit_compare(self) -> None:
        ticker = self.ticker_combo.selected_ticker()
        if not ticker:
            QtWidgets.QMessageBox.warning(self, "입력 필요", "벤치마크 종목을 선택하세요")
            return
        self.compare_requested.emit(self.market_combo.currentData(), ticker)

    def show_result(self, cmp: BenchmarkComparison) -> None:
        text = (
            f"포트폴리오: {_pct(cmp.portfolio_return_pct)}  "
            f"투입 {_n(cmp.portfolio_invested)} → 평가 {_n(cmp.portfolio_value)}\n"
            f"벤치마크 : {_pct(cmp.benchmark_return_pct)}  "
            f"투입 {_n(cmp.benchmark_invested)} → 평가 {_n(cmp.benchmark_value)}\n"
            f"Δ (포트폴리오 - 벤치마크): {_pct(cmp.delta_pct)}"
        )
        self.result_label.setText(text)


def _n(d: Decimal) -> str:
    return f"{d.quantize(Decimal('0.01')):,}"


def _pct(d: Decimal) -> str:
    return f"{d.quantize(Decimal('0.0001'))}%"
