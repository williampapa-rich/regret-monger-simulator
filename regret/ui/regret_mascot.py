"""껄무새 마스코트 — 차트 위 오버레이 애니메이션.

상태
- idle : 졸고 있음 (무한 루프)
- buy  : 살껄! 외치다 블랙홀로 빨려들어감 (1회 재생 후 idle 복귀)

GIF 파일:
  regret/ui/assets/regret_idle.gif   (무한 루프용)
  regret/ui/assets/regret_buy.gif    (1회 재생용)

파일이 없으면 마스코트 자체가 숨겨짐 (앱 동작에는 영향 없음).
"""
from __future__ import annotations

from pathlib import Path

from PyQt6 import QtCore, QtGui, QtWidgets

ASSETS_DIR = Path(__file__).resolve().parent / "assets"
IDLE_GIF = ASSETS_DIR / "regret_idle.gif"
BUY_GIF = ASSETS_DIR / "regret_buy.gif"


class RegretMascot(QtWidgets.QWidget):
    def __init__(self, parent=None, size: int = 220):
        super().__init__(parent)
        self._size = size
        self.setFixedSize(size, size)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground)

        self._idle = self._make_movie(IDLE_GIF)
        self._buy = self._make_movie(BUY_GIF)
        self._current: QtGui.QMovie | None = None

        if self._idle is None and self._buy is None:
            self.hide()
            return

        self._show_idle()

    def _make_movie(self, path: Path) -> QtGui.QMovie | None:
        if not path.exists():
            return None
        m = QtGui.QMovie(str(path))
        m.setScaledSize(QtCore.QSize(self._size, self._size))
        return m

    # ---- public --------------------------------------------------------

    def play_buy_sequence(self) -> None:
        """살껄! → 블랙홀 한 번 재생 후 idle로 복귀."""
        if self._buy is None:
            return
        if self._idle is not None:
            self._idle.stop()

        movie = self._buy
        try:
            movie.frameChanged.disconnect()
        except TypeError:
            pass
        movie.stop()
        movie.jumpToFrame(0)
        last = movie.frameCount() - 1

        def on_frame(i: int) -> None:
            self.update()
            if last > 0 and i >= last:
                movie.stop()
                self._show_idle()

        movie.frameChanged.connect(on_frame)
        self._set_current(movie)
        movie.start()

    # ---- internal ------------------------------------------------------

    def _show_idle(self) -> None:
        if self._idle is None:
            return
        try:
            self._idle.frameChanged.disconnect()
        except TypeError:
            pass
        self._idle.frameChanged.connect(lambda *_: self.update())
        self._set_current(self._idle)
        self._idle.start()

    def _set_current(self, movie: QtGui.QMovie) -> None:
        self._current = movie
        self.update()

    def paintEvent(self, ev) -> None:
        if self._current is None:
            return
        pixmap = self._current.currentPixmap()
        if pixmap.isNull():
            return
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QtGui.QPainter.RenderHint.SmoothPixmapTransform, True)

        # 원형 클립
        path = QtGui.QPainterPath()
        path.addEllipse(0, 0, self._size, self._size)
        painter.setClipPath(path)

        scaled = pixmap.scaled(
            self._size, self._size,
            QtCore.Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            QtCore.Qt.TransformationMode.SmoothTransformation,
        )
        # 중앙 정렬
        x = (self._size - scaled.width()) // 2
        y = (self._size - scaled.height()) // 2
        painter.drawPixmap(x, y, scaled)

        # 테두리
        painter.setClipping(False)
        pen = QtGui.QPen(QtGui.QColor(0, 0, 0, 180))
        pen.setWidth(2)
        painter.setPen(pen)
        painter.setBrush(QtCore.Qt.BrushStyle.NoBrush)
        painter.drawEllipse(1, 1, self._size - 2, self._size - 2)
        painter.end()
