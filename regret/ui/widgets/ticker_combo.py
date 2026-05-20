"""자동완성 가능한 종목 선택 위젯.

표시: '삼성전자 (005930.KS)'
값:   '005930.KS' (실제 어댑터로 넘기는 티커)

크립토 등 디렉터리가 없는 마켓은 자유 입력으로 동작.
"""
from __future__ import annotations

from PyQt6 import QtCore, QtGui, QtWidgets

from regret.data.ticker_directory import Entry


class TickerCombo(QtWidgets.QComboBox):
    """종목명으로 검색·선택, 내부적으로 ticker 보유."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setEditable(True)
        self.setInsertPolicy(QtWidgets.QComboBox.InsertPolicy.NoInsert)
        # 입력값과 무관하게 모든 항목을 후보로 두고 substring 매칭
        self._model = QtGui.QStandardItemModel(self)
        self.setModel(self._model)

        completer = QtWidgets.QCompleter(self._model, self)
        completer.setCaseSensitivity(QtCore.Qt.CaseSensitivity.CaseInsensitive)
        completer.setFilterMode(QtCore.Qt.MatchFlag.MatchContains)
        completer.setCompletionMode(QtWidgets.QCompleter.CompletionMode.PopupCompletion)
        self.setCompleter(completer)

    def set_entries(self, entries: list[Entry]) -> None:
        current_text = self.currentText()
        self._model.clear()
        for e in entries:
            label = f"{e.name} ({e.ticker})"
            item = QtGui.QStandardItem(label)
            item.setData(e.ticker, QtCore.Qt.ItemDataRole.UserRole)
            self._model.appendRow(item)
        self.setCurrentText(current_text)

    def set_free_input(self, placeholder: str) -> None:
        """디렉터리가 없는 마켓 — 항목 비우고 placeholder만."""
        self._model.clear()
        self.setCurrentText("")
        self.lineEdit().setPlaceholderText(placeholder)

    def selected_ticker(self) -> str:
        """현재 선택/입력값에서 ticker 추출.

        디렉터리에 매칭되는 항목이 있으면 그 UserRole 값을 반환,
        아니면 사용자가 직접 입력한 raw 텍스트를 반환 (크립토 케이스).
        """
        text = self.currentText().strip()
        if not text:
            return ""
        # 정확 매칭
        for row in range(self._model.rowCount()):
            item = self._model.item(row)
            if item.text() == text:
                return item.data(QtCore.Qt.ItemDataRole.UserRole)
        # '삼성전자' 만 입력했고 정확히 한 개 매칭되면 그걸 사용
        matches = [
            self._model.item(row)
            for row in range(self._model.rowCount())
            if text.lower() in self._model.item(row).text().lower()
        ]
        if len(matches) == 1:
            return matches[0].data(QtCore.Qt.ItemDataRole.UserRole)
        # raw 입력 (예: 크립토 'BTCUSDT' 또는 미등록 종목)
        return text
