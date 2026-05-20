"""평가 결과 테이블 + 합계 표시."""
from __future__ import annotations

from decimal import Decimal

from PyQt6 import QtCore, QtWidgets

from regret.domain.models import PurchaseValuation


_HEADERS = ["일자", "마켓", "티커", "기준", "수량", "투입금액", "현금잔액", "현재가", "평가액", "수익률(net)"]


class ValuationPanel(QtWidgets.QGroupBox):
    clear_requested = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        super().__init__("평가 결과", parent=parent)
        layout = QtWidgets.QVBoxLayout(self)

        self.table = QtWidgets.QTableWidget(0, len(_HEADERS))
        self.table.setHorizontalHeaderLabels(_HEADERS)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        header.setStretchLastSection(True)
        self.table.setEditTriggers(QtWidgets.QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Expanding,
        )
        layout.addWidget(self.table)

        bottom = QtWidgets.QHBoxLayout()
        self.summary = QtWidgets.QLabel("합계: -")
        self.summary.setStyleSheet("font-weight: bold; padding: 6px;")
        bottom.addWidget(self.summary, 1)
        self.clear_button = QtWidgets.QPushButton("초기화")
        self.clear_button.clicked.connect(self.clear_requested)
        bottom.addWidget(self.clear_button)
        layout.addLayout(bottom)

    def set_rows(self, valuations: list[PurchaseValuation]) -> None:
        self.table.setRowCount(len(valuations))
        total_invested = Decimal("0")
        total_value = Decimal("0")
        for r, v in enumerate(valuations):
            p = v.purchase
            self._set(r, 0, p.purchase_date.isoformat())
            self._set(r, 1, p.market.value)
            self._set(r, 2, p.ticker)
            self._set(r, 3, p.price_basis.value)
            self._set(r, 4, _fmt(v.quantity, 6))
            self._set(r, 5, _fmt(v.invested_amount, 1))
            self._set(r, 6, _fmt(v.cash_remainder, 1))
            self._set(r, 7, _fmt(v.current_price, 4))
            self._set(r, 8, _fmt(v.current_value, 1))
            self._set(r, 9, f"{_fmt(v.net_return_pct, 4)}%")
            total_invested += v.invested_amount
            total_value += v.current_value

        if total_invested > 0:
            ret = (total_value / total_invested - Decimal("1")) * Decimal("100")
            self.summary.setText(
                f"합계 — 투입 {_fmt(total_invested, 1)} / 평가 {_fmt(total_value, 1)} / 수익률 {_fmt(ret, 4)}%"
            )
        else:
            self.summary.setText("합계: -")

    def _set(self, row: int, col: int, text: str) -> None:
        item = QtWidgets.QTableWidgetItem(text)
        item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.table.setItem(row, col, item)


def _fmt(d: Decimal, places: int) -> str:
    q = Decimal(10) ** -places
    return f"{d.quantize(q):,}"
