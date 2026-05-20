"""일시매수 입력 폼."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from PyQt6 import QtCore, QtWidgets

from regret.data.ticker_directory import Entry
from regret.domain.enums import AmountType, Currency, Market, PriceBasis
from regret.ui.benchmark_panel import market_currency
from regret.ui.widgets.ticker_combo import TickerCombo


class PurchaseForm(QtWidgets.QGroupBox):
    """매수 입력 — 'Load 차트' 와 '추가' 두 가지 액션을 노출.

    시그널
    - load_chart_requested(market, ticker, start, end)
    - purchase_submitted(market, ticker, date, basis, amount_type, amount_value, currency)
    """

    load_chart_requested = QtCore.pyqtSignal(Market, str, date, date)
    purchase_submitted = QtCore.pyqtSignal(Market, str, date, PriceBasis, AmountType, Decimal, Currency)

    def __init__(self, parent=None):
        super().__init__("매수 입력", parent=parent)
        layout = QtWidgets.QFormLayout(self)

        self.market_combo = QtWidgets.QComboBox()
        for m in Market:
            self.market_combo.addItem(m.value, m)
        layout.addRow("마켓", self.market_combo)

        self.ticker_combo = TickerCombo()
        self.ticker_combo.setMinimumWidth(280)
        layout.addRow("종목", self.ticker_combo)
        self.market_combo.currentIndexChanged.connect(self._on_market_changed)

        self.start_edit = QtWidgets.QDateEdit(calendarPopup=True)
        self.start_edit.setDisplayFormat("yyyy-MM-dd")
        self.start_edit.setDate(QtCore.QDate.currentDate().addYears(-1))
        layout.addRow("차트 시작", self.start_edit)

        self.end_edit = QtWidgets.QDateEdit(calendarPopup=True)
        self.end_edit.setDisplayFormat("yyyy-MM-dd")
        self.end_edit.setDate(QtCore.QDate.currentDate())
        layout.addRow("차트 종료", self.end_edit)

        self.load_button = QtWidgets.QPushButton("차트 불러오기")
        layout.addRow(self.load_button)

        layout.addRow(QtWidgets.QLabel("─" * 30))

        self.purchase_date_edit = QtWidgets.QDateEdit(calendarPopup=True)
        self.purchase_date_edit.setDisplayFormat("yyyy-MM-dd")
        self.purchase_date_edit.setDate(QtCore.QDate.currentDate().addMonths(-6))
        layout.addRow("매수일", self.purchase_date_edit)

        basis_box = QtWidgets.QHBoxLayout()
        self.basis_open = QtWidgets.QRadioButton("시가")
        self.basis_close = QtWidgets.QRadioButton("종가")
        self.basis_avg = QtWidgets.QRadioButton("평균")
        self.basis_close.setChecked(True)
        for b in (self.basis_open, self.basis_close, self.basis_avg):
            basis_box.addWidget(b)
        layout.addRow("매수가 기준", basis_box)

        self.amount_type_combo = QtWidgets.QComboBox()
        self.amount_type_combo.addItem("수량 (주/코인)", AmountType.QUANTITY)
        self.amount_type_combo.addItem("금액 (통화)", AmountType.AMOUNT)
        layout.addRow("입력 방식", self.amount_type_combo)

        self.amount_edit = QtWidgets.QLineEdit()
        layout.addRow("값", self.amount_edit)

        self.add_button = QtWidgets.QPushButton("매수 추가")
        layout.addRow(self.add_button)

        self.load_button.clicked.connect(self._emit_load)
        self.add_button.clicked.connect(self._emit_submit)
        self.amount_type_combo.currentIndexChanged.connect(self._on_amount_type_changed)
        self.amount_edit.textEdited.connect(self._on_amount_text_edited)
        self._on_amount_type_changed()

    def _market(self) -> Market:
        return self.market_combo.currentData()

    def _basis(self) -> PriceBasis:
        if self.basis_open.isChecked():
            return PriceBasis.OPEN
        if self.basis_avg.isChecked():
            return PriceBasis.AVERAGE
        return PriceBasis.CLOSE

    def _emit_load(self) -> None:
        ticker = self.ticker_combo.selected_ticker()
        if not ticker:
            QtWidgets.QMessageBox.warning(self, "입력 필요", "종목을 선택하세요")
            return
        start = self.start_edit.date()
        # 매수일을 차트 시작일로 자동 갱신
        self.purchase_date_edit.setDate(start)
        self.load_chart_requested.emit(
            self._market(),
            ticker,
            start.toPyDate(),
            self.end_edit.date().toPyDate(),
        )

    def _emit_submit(self) -> None:
        ticker = self.ticker_combo.selected_ticker()
        if not ticker:
            QtWidgets.QMessageBox.warning(self, "입력 필요", "종목을 선택하세요")
            return
        raw = self.amount_edit.text().strip().replace(",", "")
        try:
            value = Decimal(raw)
        except Exception:
            QtWidgets.QMessageBox.warning(self, "입력 오류", "값은 숫자여야 합니다")
            return
        market = self._market()
        self.purchase_submitted.emit(
            market,
            ticker,
            self.purchase_date_edit.date().toPyDate(),
            self._basis(),
            self.amount_type_combo.currentData(),
            value,
            market_currency(market),
        )

    def set_purchase_date(self, d: date) -> None:
        self.purchase_date_edit.setDate(QtCore.QDate(d.year, d.month, d.day))

    def _on_market_changed(self) -> None:
        # 모든 마켓에서 directory를 MainWindow가 주입함.
        pass

    def set_directory(self, entries: list[Entry]) -> None:
        """현재 선택된 마켓의 종목 디렉터리를 주입."""
        self.ticker_combo.set_entries(entries)

    # ---- 금액 입력 천단위 콤마 ---------------------------------------------

    def _on_amount_type_changed(self) -> None:
        if self.amount_type_combo.currentData() == AmountType.AMOUNT:
            self.amount_edit.setPlaceholderText("예: 1,000,000")
        else:
            self.amount_edit.setPlaceholderText("예: 10")
        # 모드 전환 시 기존 입력 재포맷
        self._on_amount_text_edited(self.amount_edit.text())

    def _on_amount_text_edited(self, text: str) -> None:
        formatted, new_caret = _format_with_commas(text, self.amount_edit.cursorPosition())
        if formatted == text:
            return
        self.amount_edit.blockSignals(True)
        self.amount_edit.setText(formatted)
        self.amount_edit.setCursorPosition(new_caret)
        self.amount_edit.blockSignals(False)


def _format_with_commas(text: str, caret: int) -> tuple[str, int]:
    """천단위 콤마 자동 삽입. 캐럿 위치를 보존하기 위해 콤마 제외 위치 기준으로 재계산."""
    # 콤마 제외 위치(캐럿이 가리키는 '실제 숫자' 인덱스)
    digits_before_caret = sum(1 for ch in text[:caret] if ch != ",")
    # 정수부/소수부 분리
    raw = text.replace(",", "")
    if not raw:
        return "", 0
    # 허용 문자만: 숫자와 점
    allowed = "".join(ch for ch in raw if ch.isdigit() or ch == ".")
    if not allowed:
        return "", 0
    if "." in allowed:
        int_part, _, frac_part = allowed.partition(".")
        # 추가 점은 제거
        frac_part = frac_part.replace(".", "")
    else:
        int_part, frac_part = allowed, None
    # 정수부 콤마
    int_part = int_part.lstrip("0") or "0"
    int_with_commas = f"{int(int_part):,}" if int_part.isdigit() else int_part
    formatted = int_with_commas if frac_part is None else f"{int_with_commas}.{frac_part}"

    # 캐럿: 콤마 제외 N번째 위치를 콤마 포함 문자열에서 찾음
    new_caret = 0
    seen = 0
    for i, ch in enumerate(formatted):
        if seen >= digits_before_caret:
            new_caret = i
            break
        if ch != ",":
            seen += 1
        new_caret = i + 1
    return formatted, new_caret
