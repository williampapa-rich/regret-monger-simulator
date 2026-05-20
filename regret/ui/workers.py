"""백그라운드 fetch — Qt 메인스레드 차단 회피."""
from __future__ import annotations

from datetime import date
from typing import Any, Callable

import pandas as pd
from PyQt6 import QtCore


class _Signals(QtCore.QObject):
    finished = QtCore.pyqtSignal(object)
    failed = QtCore.pyqtSignal(str)


class FetchOHLCJob(QtCore.QRunnable):
    def __init__(self, fn: Callable[[], pd.DataFrame]):
        super().__init__()
        self._fn = fn
        self.signals = _Signals()

    def run(self) -> None:
        try:
            result = self._fn()
        except Exception as exc:  # noqa: BLE001
            self.signals.failed.emit(f"{type(exc).__name__}: {exc}")
            return
        self.signals.finished.emit(result)


class CallableJob(QtCore.QRunnable):
    """임의의 콜러블을 백그라운드에서 실행."""

    def __init__(self, fn: Callable[[], Any]):
        super().__init__()
        self._fn = fn
        self.signals = _Signals()

    def run(self) -> None:
        try:
            result = self._fn()
        except Exception as exc:  # noqa: BLE001
            self.signals.failed.emit(f"{type(exc).__name__}: {exc}")
            return
        self.signals.finished.emit(result)
