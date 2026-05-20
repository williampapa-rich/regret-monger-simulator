"""휴장일 → 직전/직후 영업일 선택 다이얼로그."""
from __future__ import annotations

from datetime import date

from PyQt6 import QtWidgets


class HolidayDialog(QtWidgets.QDialog):
    """target이 휴장일일 때 before/after 중 선택. 사용자가 취소하면 None 반환."""

    def __init__(
        self,
        target: date,
        before: date | None,
        after: date | None,
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle("휴장일 보정")
        self.setModal(True)
        self._chosen: date | None = None

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(QtWidgets.QLabel(
            f"{target}은 데이터가 없는 일자입니다.\n어느 영업일로 보정할까요?"
        ))

        button_box = QtWidgets.QHBoxLayout()
        if before is not None:
            btn_before = QtWidgets.QPushButton(f"직전 ({before})")
            btn_before.clicked.connect(lambda: self._choose(before))
            button_box.addWidget(btn_before)
        if after is not None:
            btn_after = QtWidgets.QPushButton(f"직후 ({after})")
            btn_after.clicked.connect(lambda: self._choose(after))
            button_box.addWidget(btn_after)
        layout.addLayout(button_box)

        cancel = QtWidgets.QPushButton("취소")
        cancel.clicked.connect(self.reject)
        layout.addWidget(cancel)

    def _choose(self, d: date) -> None:
        self._chosen = d
        self.accept()

    def chosen(self) -> date | None:
        return self._chosen
