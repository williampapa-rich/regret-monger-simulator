"""PyQtGraph 캔들스틱 차트.

- x축은 정수 인덱스(0..N-1) → 휴장일 자동 회피
- 호버: 십자선이 가장 가까운 캔들에 스냅, 우상단 라벨에 일자/OHLC 표시
- 클릭: candle_clicked 시그널 (date) emit, 클릭 캔들에 노란 하이라이트
- 매수 마커: add_marker (파란 삼각형, 가격 위치)
"""
from __future__ import annotations

from datetime import date

import pandas as pd
import pyqtgraph as pg
from PyQt6 import QtCore, QtGui


class CandlestickItem(pg.GraphicsObject):
    def __init__(self, df: pd.DataFrame):
        super().__init__()
        self._df = df.reset_index(drop=False)
        self._picture = QtGui.QPicture()
        self._draw()

    def _draw(self) -> None:
        painter = QtGui.QPainter(self._picture)
        w = 0.4
        for i, row in self._df.iterrows():
            o, h, l, c = row["open"], row["high"], row["low"], row["close"]
            color = QtGui.QColor("#26a69a") if c >= o else QtGui.QColor("#ef5350")
            painter.setPen(pg.mkPen(color))
            painter.setBrush(pg.mkBrush(color))
            painter.drawLine(QtCore.QPointF(i, l), QtCore.QPointF(i, h))
            top = max(o, c)
            bottom = min(o, c)
            painter.drawRect(QtCore.QRectF(i - w, bottom, w * 2, top - bottom))
        painter.end()

    def paint(self, painter, *args):
        painter.drawPicture(0, 0, self._picture)

    def boundingRect(self):
        return QtCore.QRectF(self._picture.boundingRect())


class _DateAxis(pg.AxisItem):
    def __init__(self, df: pd.DataFrame, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._dates = list(df.index)

    def tickStrings(self, values, scale, spacing):
        out = []
        for v in values:
            i = int(round(v))
            if 0 <= i < len(self._dates):
                out.append(pd.Timestamp(self._dates[i]).strftime("%Y-%m-%d"))
            else:
                out.append("")
        return out


class ChartWidget(pg.PlotWidget):
    candle_clicked = QtCore.pyqtSignal(object)   # date
    candle_hovered = QtCore.pyqtSignal(object, dict)  # date, OHLC

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setBackground("w")
        self._df: pd.DataFrame | None = None
        self._candle: CandlestickItem | None = None
        self._buy_markers: pg.ScatterPlotItem | None = None
        self._selection_marker: pg.ScatterPlotItem | None = None
        self._vline: pg.InfiniteLine | None = None
        self._hline: pg.InfiniteLine | None = None
        self._hover_label: pg.TextItem | None = None
        self._proxy: pg.SignalProxy | None = None

        self.scene().sigMouseClicked.connect(self._on_click)
        self.setMouseTracking(True)

    # ---- 데이터 ------------------------------------------------------------

    def set_data(self, df: pd.DataFrame) -> None:
        self.clear()
        df = df.dropna(subset=["open", "high", "low", "close"])
        df = df[~df.index.isna()]
        self._df = df
        if df.empty:
            return

        bottom = _DateAxis(df, orientation="bottom")
        self.setAxisItems({"bottom": bottom})
        self._candle = CandlestickItem(df)
        self.addItem(self._candle)

        self._buy_markers = pg.ScatterPlotItem(
            size=14, brush=pg.mkBrush(30, 30, 200, 220),
            pen=pg.mkPen("w", width=1), symbol="t",
        )
        self.addItem(self._buy_markers)

        self._selection_marker = pg.ScatterPlotItem(
            size=22, brush=pg.mkBrush(255, 200, 0, 80),
            pen=pg.mkPen(QtGui.QColor("#fbc02d"), width=2), symbol="o",
        )
        self.addItem(self._selection_marker)

        pen = pg.mkPen(QtGui.QColor(120, 120, 120, 160), style=QtCore.Qt.PenStyle.DashLine)
        self._vline = pg.InfiniteLine(angle=90, pen=pen, movable=False)
        self._hline = pg.InfiniteLine(angle=0, pen=pen, movable=False)
        self._vline.setVisible(False)
        self._hline.setVisible(False)
        self.addItem(self._vline, ignoreBounds=True)
        self.addItem(self._hline, ignoreBounds=True)

        self._hover_label = pg.TextItem(
            anchor=(0, 1), color=QtGui.QColor("#222"),
            fill=pg.mkBrush(255, 255, 255, 220),
            border=pg.mkPen(QtGui.QColor(120, 120, 120))
        )
        self._hover_label.setVisible(False)
        self.addItem(self._hover_label, ignoreBounds=True)

        self._proxy = pg.SignalProxy(
            self.scene().sigMouseMoved, rateLimit=60, slot=self._on_mouse_move,
        )

        self.setXRange(0, len(df) - 1)
        self.setYRange(float(df["low"].min()), float(df["high"].max()))

    # ---- 매수 마커 (외부에서 추가) -----------------------------------------

    def add_marker(self, target: date, price: float) -> None:
        if self._df is None or self._buy_markers is None:
            return
        try:
            i = self._df.index.get_loc(pd.Timestamp(target))
        except KeyError:
            return
        self._buy_markers.addPoints(x=[i], y=[price])

    def clear_buy_markers(self) -> None:
        if self._buy_markers is not None:
            self._buy_markers.clear()

    # ---- 클릭 --------------------------------------------------------------

    def _on_click(self, ev) -> None:
        if self._df is None or self._df.empty:
            return
        if ev.button() != QtCore.Qt.MouseButton.LeftButton:
            return
        i = self._index_from_scene_pos(ev.scenePos())
        if i is None:
            return
        ts = self._df.index[i]
        self._highlight(i)
        self.candle_clicked.emit(pd.Timestamp(ts).date())

    def _highlight(self, i: int) -> None:
        if self._df is None or self._selection_marker is None:
            return
        row = self._df.iloc[i]
        mid = (float(row["open"]) + float(row["close"])) / 2
        self._selection_marker.setData(x=[i], y=[mid])

    # ---- 호버 (십자선 + OHLC 라벨) -----------------------------------------

    def _on_mouse_move(self, args) -> None:
        if self._df is None or self._df.empty:
            return
        scene_pos = args[0]
        i = self._index_from_scene_pos(scene_pos)
        if i is None:
            self._hide_crosshair()
            return

        row = self._df.iloc[i]
        ts = pd.Timestamp(self._df.index[i])

        self._vline.setPos(i)
        self._hline.setPos(float(row["close"]))
        self._vline.setVisible(True)
        self._hline.setVisible(True)

        text = (
            f"{ts.strftime('%Y-%m-%d')}\n"
            f"O {_fmt(row['open'])}  H {_fmt(row['high'])}\n"
            f"L {_fmt(row['low'])}   C {_fmt(row['close'])}"
        )
        self._hover_label.setText(text)
        self._hover_label.setPos(i, float(row["high"]))
        self._hover_label.setVisible(True)

        self.candle_hovered.emit(
            ts.date(),
            {"open": float(row["open"]), "high": float(row["high"]),
             "low": float(row["low"]), "close": float(row["close"])},
        )

    def _hide_crosshair(self) -> None:
        for item in (self._vline, self._hline, self._hover_label):
            if item is not None:
                item.setVisible(False)

    # ---- 좌표 변환 ---------------------------------------------------------

    def _index_from_scene_pos(self, scene_pos) -> int | None:
        if self._df is None or self._df.empty:
            return None
        if not self.plotItem.sceneBoundingRect().contains(scene_pos):
            return None
        view_pos = self.plotItem.vb.mapSceneToView(scene_pos)
        i = int(round(view_pos.x()))
        if i < 0 or i >= len(self._df):
            return None
        return i


def _fmt(v) -> str:
    v = float(v)
    if v >= 1000:
        return f"{v:,.0f}"
    if v >= 1:
        return f"{v:,.2f}"
    return f"{v:.6f}"
