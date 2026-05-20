"""메인 윈도우 — 좌(차트) / 우(입력+결과) 레이아웃."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pandas as pd
from PyQt6 import QtCore, QtWidgets

from pathlib import Path

from regret.data.cache import OHLCCache
from regret.data.calendar import nearest_after, nearest_before
from regret.data.registry import get_fetcher
from regret.data.ticker_directory import get_entries
from regret.domain.benchmark import compare as benchmark_compare
from regret.domain.dca import expand as dca_expand
from regret.domain.enums import AmountType, Currency, Market, PriceBasis
from regret.domain.fees import FeeTable
from regret.domain.models import OHLCRow, Portfolio, Purchase
from regret.domain.valuation import evaluate
from regret.persistence.portfolio_io import load as load_portfolio, save as save_portfolio
from regret.ui.chart_widget import ChartWidget
from regret.ui.dca_dialog import DCADialog
from regret.ui.holiday_dialog import HolidayDialog
from regret.ui.benchmark_panel import BenchmarkPanel, market_currency
from regret.ui.purchase_form import PurchaseForm
from regret.ui.regret_mascot import RegretMascot
from regret.ui.valuation_panel import ValuationPanel
from regret.ui.workers import CallableJob


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("껄무새 시뮬레이터")
        self.resize(1400, 800)

        self._fees = FeeTable.load()
        self._cache = OHLCCache()
        self._pool = QtCore.QThreadPool.globalInstance()
        self._portfolio = Portfolio()
        # job을 명시적으로 들고 있지 않으면 _Signals가 GC돼서 finished가 사라진다.
        self._active_jobs: list[CallableJob] = []
        # 마켓별 종목 디렉터리 메모리 캐시
        self._directory_memo: dict[Market, list] = {}
        self._chart_df: pd.DataFrame | None = None
        self._chart_market: Market | None = None
        self._chart_ticker: str | None = None

        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        root = QtWidgets.QVBoxLayout(central)

        # 상단: 차트(좌) + 입력 패널(우)
        top = QtWidgets.QWidget()
        top_layout = QtWidgets.QHBoxLayout(top)
        top_layout.setContentsMargins(0, 0, 0, 0)
        self.chart = ChartWidget()
        top_layout.addWidget(self.chart, 3)

        right = QtWidgets.QVBoxLayout()
        self.form = PurchaseForm()
        self.dca_button = QtWidgets.QPushButton("DCA(분할매수) 추가…")
        self.benchmark_panel = BenchmarkPanel()
        right.addWidget(self.form, 1)
        right.addWidget(self.dca_button)
        right.addWidget(self.benchmark_panel)
        right.addStretch(1)
        top_layout.addLayout(right, 2)

        # 하단: 평가 결과 (가로 전체)
        self.valuation_panel = ValuationPanel()

        # QSplitter로 상하 분할 — 드래그로 평가결과 영역 동적 확장 가능
        splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Vertical)
        splitter.addWidget(top)
        splitter.addWidget(self.valuation_panel)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        splitter.setSizes([600, 400])
        root.addWidget(splitter)

        # 차트 위에 떠있는 마스코트 오버레이 (parent를 chart로)
        self.mascot = RegretMascot(parent=self.chart)
        self.mascot.raise_()
        self.chart.installEventFilter(self)
        self._reposition_mascot()

        self._build_menu()
        self.statusBar().showMessage("준비")

        self.form.load_chart_requested.connect(self._on_load_chart)
        self.form.purchase_submitted.connect(self._on_purchase_submitted)
        self.dca_button.clicked.connect(self._on_dca)
        self.chart.candle_clicked.connect(self.form.set_purchase_date)
        self.chart.candle_hovered.connect(self._on_chart_hover)
        self.benchmark_panel.compare_requested.connect(self._on_benchmark)
        self.valuation_panel.clear_requested.connect(self._on_clear_valuations)

        # 마켓 변경 시 디렉터리 백그라운드 로딩
        self.form.market_combo.currentIndexChanged.connect(
            lambda: self._load_directory(self.form._market(), target="form")
        )
        self.benchmark_panel.market_combo.currentIndexChanged.connect(
            lambda: self._load_directory(self.benchmark_panel.market(), target="benchmark")
        )
        # 초기 로딩
        self.form._on_market_changed()
        self.benchmark_panel._on_market_changed()
        QtCore.QTimer.singleShot(0, lambda: self._load_directory(self.form._market(), target="form"))
        QtCore.QTimer.singleShot(0, lambda: self._load_directory(self.benchmark_panel.market(), target="benchmark"))

    # ---- 메뉴 --------------------------------------------------------------

    def _build_menu(self) -> None:
        menu = self.menuBar().addMenu("파일")
        save_action = menu.addAction("저장…")
        save_action.triggered.connect(self._save_portfolio)
        load_action = menu.addAction("불러오기…")
        load_action.triggered.connect(self._load_portfolio)

    def _save_portfolio(self) -> None:
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "저장", filter="JSON (*.json)")
        if not path:
            return
        save_portfolio(self._portfolio, Path(path))
        self.statusBar().showMessage(f"저장 완료: {path}")

    def _load_portfolio(self) -> None:
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "불러오기", filter="JSON (*.json)")
        if not path:
            return
        self._portfolio = load_portfolio(Path(path))
        self._refresh_valuations()
        self.statusBar().showMessage(f"불러오기 완료: {path}")

    # ---- 차트 로딩 ---------------------------------------------------------

    def _start_job(self, fn, on_finished, on_failed=None) -> None:
        job = CallableJob(fn)
        self._active_jobs.append(job)

        def cleanup(*_):
            if job in self._active_jobs:
                self._active_jobs.remove(job)

        job.signals.finished.connect(on_finished)
        job.signals.finished.connect(cleanup)
        job.signals.failed.connect(on_failed or self._on_error)
        job.signals.failed.connect(cleanup)
        self._pool.start(job)

    def _on_load_chart(self, market: Market, ticker: str, start: date, end: date) -> None:
        self.statusBar().showMessage(f"차트 로딩… {market.value} {ticker}")
        fetcher = get_fetcher(market)

        def fetch() -> pd.DataFrame:
            return self._cache.get_or_fetch(market, ticker, start, end, fetcher)

        self._start_job(fetch, lambda df: self._on_chart_loaded(market, ticker, df))

    def _on_chart_loaded(self, market: Market, ticker: str, df: pd.DataFrame) -> None:
        if df.empty:
            self.statusBar().showMessage("데이터 없음 — 티커/기간을 확인하세요")
            return
        self._chart_df = df
        self._chart_market = market
        self._chart_ticker = ticker
        self.chart.set_data(df)
        self.statusBar().showMessage(f"{market.value} {ticker} — 캔들 {len(df)}개")

    # ---- 종목 디렉터리 ---------------------------------------------------

    def _load_directory(self, market: Market, *, target: str) -> None:
        """target은 'form' 또는 'benchmark'."""
        # 메모리에 있으면 즉시 주입
        if market in self._directory_memo:
            self._apply_directory(market, self._directory_memo[market], target)
            return
        self.statusBar().showMessage(f"{market.value} 종목 목록 로딩…")

        def fetch():
            return get_entries(market)

        def on_done(entries):
            self._directory_memo[market] = entries
            self._apply_directory(market, entries, target)
            self.statusBar().showMessage(f"{market.value} 종목 {len(entries)}개 로드")

        self._start_job(fetch, on_done)

    def _apply_directory(self, market: Market, entries, target: str) -> None:
        if target == "form" and self.form._market() == market:
            self.form.set_directory(entries)
        elif target == "benchmark" and self.benchmark_panel.market() == market:
            self.benchmark_panel.set_directory(entries)

    def eventFilter(self, obj, ev) -> bool:
        if obj is self.chart and ev.type() == QtCore.QEvent.Type.Resize:
            self._reposition_mascot()
        return super().eventFilter(obj, ev)

    def _reposition_mascot(self) -> None:
        # 차트 우상단에서 안쪽으로 20px
        margin = 20
        x = max(margin, self.chart.width() - self.mascot.width() - margin)
        self.mascot.move(x, margin)

    def _on_clear_valuations(self) -> None:
        if not self._portfolio.purchases:
            return
        ans = QtWidgets.QMessageBox.question(
            self, "초기화", "모든 매수 내역을 삭제할까요?",
        )
        if ans != QtWidgets.QMessageBox.StandardButton.Yes:
            return
        self._portfolio.purchases.clear()
        self.chart.clear_buy_markers()
        self.valuation_panel.set_rows([])
        self.benchmark_panel.set_portfolio_currency(None)
        self.statusBar().showMessage("매수 내역을 초기화했습니다")

    def _on_chart_hover(self, d: date, ohlc: dict) -> None:
        self.statusBar().showMessage(
            f"{d}  O {ohlc['open']:,.2f}  H {ohlc['high']:,.2f}  "
            f"L {ohlc['low']:,.2f}  C {ohlc['close']:,.2f}"
        )

    # ---- 매수 추가 ---------------------------------------------------------

    def _on_purchase_submitted(
        self,
        market: Market,
        ticker: str,
        purchase_date: date,
        basis: PriceBasis,
        amount_type: AmountType,
        amount_value: Decimal,
        currency: Currency,
    ) -> None:
        if self._chart_df is None:
            QtWidgets.QMessageBox.information(self, "차트 필요", "먼저 차트를 불러오세요")
            return
        if market != self._chart_market or ticker != self._chart_ticker:
            QtWidgets.QMessageBox.warning(
                self, "마켓 불일치",
                "현재 차트와 다른 마켓/티커입니다. 먼저 차트를 다시 불러오세요.",
            )
            return

        snapped = self._snap_to_trading_day(purchase_date)
        if snapped is None:
            return
        purchase_date = snapped

        purchase = Purchase(
            market=market,
            ticker=ticker,
            purchase_date=purchase_date,
            price_basis=basis,
            amount_type=amount_type,
            amount_value=amount_value,
            currency=currency,
            fee_rate=self._fees.get(market),
        )
        self._portfolio.purchases.append(purchase)
        self._refresh_valuations()
        self.mascot.play_buy_sequence()

    # ---- 휴장일 보정 -------------------------------------------------------

    def _snap_to_trading_day(self, target: date) -> date | None:
        """target이 차트 데이터에 있으면 그대로, 없으면 다이얼로그로 보정. 취소 시 None."""
        if self._chart_df is None:
            return None
        if pd.Timestamp(target) in self._chart_df.index:
            return target
        before = nearest_before(target, self._chart_df)
        after = nearest_after(target, self._chart_df)
        if before is None and after is None:
            QtWidgets.QMessageBox.warning(
                self, "데이터 없음",
                "이 일자 근처에 거래일이 없습니다. 차트 기간을 넓히세요.",
            )
            return None
        dlg = HolidayDialog(target, before, after, parent=self)
        if dlg.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            return None
        return dlg.chosen()

    # ---- DCA --------------------------------------------------------------

    def _on_dca(self) -> None:
        if self._chart_df is None or self._chart_market is None or self._chart_ticker is None:
            QtWidgets.QMessageBox.information(self, "차트 필요", "먼저 차트를 불러오세요")
            return
        market = self._chart_market
        ticker = self._chart_ticker
        dlg = DCADialog(
            market=market,
            ticker=ticker,
            currency=market_currency(market),
            fee_rate=self._fees.get(market),
            parent=self,
        )
        if dlg.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            return
        spec = dlg.result_spec()
        if spec is None:
            return

        purchases = dca_expand(spec)
        skipped = 0
        for p in purchases:
            ts = pd.Timestamp(p.purchase_date)
            if ts in self._chart_df.index:
                self._portfolio.purchases.append(p)
                continue
            # 휴장일이면 직후 영업일로 자동 스냅 (DCA는 다이얼로그 매번 띄우지 않음).
            after = nearest_after(p.purchase_date, self._chart_df)
            if after is None:
                skipped += 1
                continue
            self._portfolio.purchases.append(p.model_copy(update={"purchase_date": after}))

        self._refresh_valuations()
        self.mascot.play_buy_sequence()
        msg = f"DCA {len(purchases)}건 중 {len(purchases) - skipped}건 추가"
        if skipped:
            msg += f" / {skipped}건은 차트 범위 외라 제외"
        self.statusBar().showMessage(msg)

    # ---- 평가 갱신 ---------------------------------------------------------

    def _refresh_valuations(self) -> None:
        if self._chart_df is None:
            return
        valuations = []
        latest_close = Decimal(str(self._chart_df["close"].iloc[-1]))
        for p in self._portfolio.purchases:
            if p.market != self._chart_market or p.ticker != self._chart_ticker:
                continue
            row = self._chart_df.loc[pd.Timestamp(p.purchase_date)]
            ohlc = OHLCRow(
                open=Decimal(str(row["open"])),
                high=Decimal(str(row["high"])),
                low=Decimal(str(row["low"])),
                close=Decimal(str(row["close"])),
            )
            v = evaluate(p, ohlc, latest_close)
            valuations.append(v)
            self.chart.add_marker(p.purchase_date, float(v.applied_buy_price))
        self.valuation_panel.set_rows(valuations)
        self._sync_benchmark_currency()

    def _sync_benchmark_currency(self) -> None:
        relevant = [
            p for p in self._portfolio.purchases
            if p.market == self._chart_market and p.ticker == self._chart_ticker
        ]
        currency = relevant[0].currency if relevant else None
        self.benchmark_panel.set_portfolio_currency(currency)

    # ---- 벤치마크 비교 ----------------------------------------------------

    def _on_benchmark(self, b_market: Market, b_ticker: str) -> None:
        if self._chart_df is None or self._chart_market is None or self._chart_ticker is None:
            return
        purchases = [
            p for p in self._portfolio.purchases
            if p.market == self._chart_market and p.ticker == self._chart_ticker
        ]
        if not purchases:
            QtWidgets.QMessageBox.information(self, "매수 없음", "비교할 매수가 없습니다")
            return

        # 벤치마크 OHLC 범위: 매수일 최소 ~ 오늘
        start = min(p.purchase_date for p in purchases)
        end = pd.Timestamp(self._chart_df.index.max()).date()

        self.statusBar().showMessage(f"벤치마크 로딩… {b_market.value} {b_ticker}")
        b_fetcher = get_fetcher(b_market)

        def fetch():
            return self._cache.get_or_fetch(b_market, b_ticker, start, end, b_fetcher)

        self._start_job(
            fetch,
            lambda b_df: self._compute_benchmark(purchases, b_market, b_ticker, b_df),
        )

    def _compute_benchmark(
        self,
        purchases: list[Purchase],
        b_market: Market,
        b_ticker: str,
        b_df: pd.DataFrame,
    ) -> None:
        if b_df.empty:
            QtWidgets.QMessageBox.warning(self, "데이터 없음", "벤치마크 데이터를 가져오지 못했습니다")
            return

        portfolio_ohlc = {
            pd.Timestamp(idx).date(): OHLCRow(
                open=Decimal(str(r["open"])),
                high=Decimal(str(r["high"])),
                low=Decimal(str(r["low"])),
                close=Decimal(str(r["close"])),
            )
            for idx, r in self._chart_df.iterrows()
        }
        # 벤치마크 측: 매수일이 휴장일이면 직후 영업일 OHLC를 채워서 키 매칭.
        b_ohlc: dict = {}
        for p in purchases:
            ts = pd.Timestamp(p.purchase_date)
            if ts in b_df.index:
                row = b_df.loc[ts]
            else:
                after_idx = b_df.index[b_df.index >= ts]
                if len(after_idx) == 0:
                    QtWidgets.QMessageBox.warning(
                        self, "데이터 부족",
                        f"{p.purchase_date} 이후 벤치마크 캔들이 없습니다",
                    )
                    return
                row = b_df.loc[after_idx[0]]
            b_ohlc[p.purchase_date] = OHLCRow(
                open=Decimal(str(row["open"])),
                high=Decimal(str(row["high"])),
                low=Decimal(str(row["low"])),
                close=Decimal(str(row["close"])),
            )

        try:
            cmp = benchmark_compare(
                purchases=purchases,
                portfolio_ohlc=portfolio_ohlc,
                portfolio_current_price=Decimal(str(self._chart_df["close"].iloc[-1])),
                benchmark_market=b_market,
                benchmark_ticker=b_ticker,
                benchmark_currency=market_currency(b_market),
                benchmark_ohlc=b_ohlc,
                benchmark_current_price=Decimal(str(b_df["close"].iloc[-1])),
                fee_rate_benchmark=self._fees.get(b_market),
            )
        except ValueError as e:
            QtWidgets.QMessageBox.warning(self, "비교 실패", str(e))
            return
        self.benchmark_panel.show_result(cmp)
        self.statusBar().showMessage("벤치마크 비교 완료")

    # ---- 에러 --------------------------------------------------------------

    def _on_error(self, msg: str) -> None:
        self.statusBar().showMessage("에러")
        QtWidgets.QMessageBox.critical(self, "에러", msg)
