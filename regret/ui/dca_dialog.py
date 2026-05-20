"""DCA 입력 모달.

확인 시 DCASpec을 반환한다. 실제 Purchase 펼치기와 휴장일 스냅은 호출자가 수행.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from PyQt6 import QtCore, QtWidgets

from regret.domain.dca import DCASpec, Frequency
from regret.domain.enums import Currency, Market, PriceBasis
from regret.ui.purchase_form import _format_with_commas


class DCADialog(QtWidgets.QDialog):
    def __init__(
        self,
        market: Market,
        ticker: str,
        currency: Currency,
        fee_rate: Decimal,
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle("DCA(분할매수) 추가")
        self.setModal(True)

        self._market = market
        self._ticker = ticker
        self._currency = currency
        self._fee_rate = fee_rate
        self._result: DCASpec | None = None

        layout = QtWidgets.QFormLayout(self)
        layout.addRow("마켓 / 티커", QtWidgets.QLabel(f"{market.value} / {ticker}"))

        self.start_edit = QtWidgets.QDateEdit(calendarPopup=True)
        self.start_edit.setDisplayFormat("yyyy-MM-dd")
        self.start_edit.setDate(QtCore.QDate.currentDate().addYears(-1))
        layout.addRow("시작일", self.start_edit)

        self.end_edit = QtWidgets.QDateEdit(calendarPopup=True)
        self.end_edit.setDisplayFormat("yyyy-MM-dd")
        self.end_edit.setDate(QtCore.QDate.currentDate())
        layout.addRow("종료일", self.end_edit)

        self.freq_combo = QtWidgets.QComboBox()
        self.freq_combo.addItem("매일", "daily")
        self.freq_combo.addItem("매주", "weekly")
        self.freq_combo.addItem("매월", "monthly")
        self.freq_combo.setCurrentIndex(2)
        layout.addRow("주기", self.freq_combo)

        self.amount_edit = QtWidgets.QLineEdit()
        self.amount_edit.setPlaceholderText("회차당 금액 (예: 100,000)")
        layout.addRow(f"회차 금액 ({currency.value})", self.amount_edit)
        self.amount_edit.textEdited.connect(self._on_amount_text_edited)

        self.basis_combo = QtWidgets.QComboBox()
        self.basis_combo.addItem("종가", PriceBasis.CLOSE)
        self.basis_combo.addItem("시가", PriceBasis.OPEN)
        self.basis_combo.addItem("평균", PriceBasis.AVERAGE)
        layout.addRow("매수가 기준", self.basis_combo)

        self.fee_label = QtWidgets.QLabel(f"{fee_rate * 100:.4f}%  (시점에 박힘)")
        layout.addRow("수수료율", self.fee_label)

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok
            | QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def _on_amount_text_edited(self, text: str) -> None:
        formatted, caret = _format_with_commas(text, self.amount_edit.cursorPosition())
        if formatted == text:
            return
        self.amount_edit.blockSignals(True)
        self.amount_edit.setText(formatted)
        self.amount_edit.setCursorPosition(caret)
        self.amount_edit.blockSignals(False)

    def _accept(self) -> None:
        try:
            amount = Decimal(self.amount_edit.text().strip().replace(",", ""))
        except Exception:
            QtWidgets.QMessageBox.warning(self, "입력 오류", "회차 금액은 숫자여야 합니다")
            return
        if amount <= 0:
            QtWidgets.QMessageBox.warning(self, "입력 오류", "금액은 0보다 커야 합니다")
            return
        start: date = self.start_edit.date().toPyDate()
        end: date = self.end_edit.date().toPyDate()
        if start > end:
            QtWidgets.QMessageBox.warning(self, "입력 오류", "시작일이 종료일보다 늦습니다")
            return

        self._result = DCASpec(
            market=self._market,
            ticker=self._ticker,
            start=start,
            end=end,
            frequency=self.freq_combo.currentData(),  # type: ignore[arg-type]
            per_period_amount=amount,
            currency=self._currency,
            price_basis=self.basis_combo.currentData(),
            fee_rate=self._fee_rate,
        )
        self.accept()

    def result_spec(self) -> DCASpec | None:
        return self._result
