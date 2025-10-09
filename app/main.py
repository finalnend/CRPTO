from __future__ import annotations
import sys
from collections import deque
from datetime import datetime
from typing import Dict, List
from PySide6.QtCore import QObject, Qt, QThread, QTimer, Signal, Slot, QDateTime
from PySide6.QtGui import QAction, QColor, QPainter
from PySide6.QtWidgets import (
    QApplication,
    QHeaderView,
    QLineEdit,
    QMainWindow,

    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QToolBar,
    QComboBox,
    QMenu,
    QInputDialog,
    QSystemTrayIcon,
    QStyle,
    QColorDialog,
    QDockWidget,
    QWidget,
    QVBoxLayout,
    QGroupBox,
    QCheckBox,
    QHBoxLayout,
    QScrollArea,
)
from PySide6.QtCharts import (
    QChart,
    QChartView,
    QLineSeries,
    QValueAxis,
    QDateTimeAxis,
    QAreaSeries,
    QCandlestickSeries,
    QCandlestickSet,
    QBarSeries,
    QBarSet,
    QBarCategoryAxis,
)
from PySide6.QtCore import QPointF
from PySide6.QtWidgets import QGraphicsLineItem, QGraphicsSimpleTextItem
class ChartViewCrosshair(QChartView):
    def __init__(self, chart: QChart, parent=None) -> None:
        super().__init__(chart, parent)
        self.setMouseTracking(True)
        self.series_ref: QLineSeries | None = None
        self.vline = QGraphicsLineItem()
        self.hline = QGraphicsLineItem()
        for ln in (self.vline, self.hline):
            ln.setZValue(1000)
            self.scene().addItem(ln)
            ln.hide()
        self.label = QGraphicsSimpleTextItem("")
        self.label.setZValue(1001)
        self.scene().addItem(self.label)
        self.label.hide()
    def setSeries(self, s: QLineSeries) -> None:
        self.series_ref = s
    def mouseMoveEvent(self, event):  # type: ignore[override]
        if not self.series_ref or self.series_ref.count() == 0:
            super().mouseMoveEvent(event)
            return
        chart = self.chart()
        pos = event.position() if hasattr(event, 'position') else event.posF()
        chart_pos = chart.mapToValue(pos, self.series_ref)
        plot_rect = chart.plotArea()
        x = pos.x()
        y = pos.y()
        # Constrain within plot area
        if not plot_rect.contains(pos):
            self.vline.hide(); self.hline.hide(); self.label.hide()
            super().mouseMoveEvent(event)
            return
        self.vline.setLine(x, plot_rect.top(), x, plot_rect.bottom())
        self.hline.setLine(plot_rect.left(), y, plot_rect.right(), y)
        self.vline.show(); self.hline.show()
        # Label
        self.label.setText(f"{chart_pos.y():.6f}")
        self.label.setPos(plot_rect.left() + 6, y - 12)
        self.label.show()
        super().mouseMoveEvent(event)
    def leaveEvent(self, event):  # type: ignore[override]
        self.vline.hide(); self.hline.hide(); self.label.hide()
        return super().leaveEvent(event)
    # Basic zoom/pan
    def wheelEvent(self, event):  # type: ignore[override]
        delta = event.angleDelta().y() if hasattr(event, 'angleDelta') else 0
        if delta > 0:
            self.chart().zoomIn()
        else:
            self.chart().zoomOut()
        super().wheelEvent(event)
    def mousePressEvent(self, event):  # type: ignore[override]
        self._last_pos = event.position() if hasattr(event, 'position') else event.posF()
        super().mousePressEvent(event)
    def mouseMoveEvent(self, event):  # type: ignore[override]
        # Crosshair update
        super().mouseMoveEvent(event)
        # Middle-button pan
        if event.buttons() & Qt.MiddleButton:
            pos = event.position() if hasattr(event, 'position') else event.posF()
            dx = pos.x() - self._last_pos.x()
            dy = pos.y() - self._last_pos.y()
            self.chart().scroll(-dx, dy)
            self._last_pos = pos
class FetcherWorker(QObject):
    resultReady = Signal(dict)  # dict[symbol] = Ticker(dict)
    error = Signal(str)
    def __init__(self, provider: BinanceRestProvider) -> None:
        super().__init__()
        self._provider = provider
    @Slot(str, list)
    def fetch(self, source: str, symbols: List[str]) -> None:
        try:
            res = self._provider.fetch_from(source, symbols)
            packed = {
                k: {
                    "symbol": v.symbol,
                    "last": v.last,
                    "change_pct": v.change_pct,
                    "volume": v.volume,
                    "bid": v.bid,
                    "ask": v.ask,
                    "quote_volume": v.quote_volume,
                    "high": v.high,
                    "low": v.low,
                    "ts": v.ts.isoformat(),
                }
                for k, v in res.items()
            }
            self.resultReady.emit(packed)
        except Exception as e:
            self.error.emit(str(e))
class NumericItem(QTableWidgetItem):
    def __init__(self, text: str = "", value: float = 0.0):
        super().__init__(text)
        self.value = value
        self.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
    def __lt__(self, other):  # type: ignore[override]
        if isinstance(other, NumericItem):
            return self.value < other.value
        try:
            return float(self.text().replace(",", "")) < float(other.text().replace(",", ""))
        except Exception:
            return super().__lt__(other)
from app.widgets.sparkline import SparklineWidget
from app.data.providers import BinanceRestProvider
from app.ws.binance import BinanceWsClient, BinanceKlineWsClient
from app.util.env import fix_ssl_env
import app.theme as theme
class MainWindow(QMainWindow):
    requestFetch = Signal(str, list)
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Crypto Ticker - PySide6")
        self.resize(720, 420)
        # State
        self.symbols: List[str] = ["BTCUSDT", "ETHUSDT", "BNBUSDT"]
        self.rest_source: str = "binance"  # for manual or failover
        self.mode: str = "auto"  # auto | binance-ws | binance | coingecko | coinbase
        self._ws_failures = 0
        self._ws_connected = False
        self._tray_first_hide = True
        self._minimize_to_tray = True
        self.alerts: Dict[str, Dict[str, float | bool | None]] = {}
        self._rest_failures = 0
        self._sparks: Dict[str, 'SparklineWidget'] = {}
        # UI
        self._build_toolbar_min()
        self._build_table()
        self._build_sidebar()
        self._build_chart()
        self.theme_mode = "dark"
        self.accent_color = QColor("#0A84FF")
        self._apply_theme(self.theme_mode)
        self._build_tray()
        # Backend
        self._provider = BinanceRestProvider(timeout_s=7)
        self._worker = FetcherWorker(self._provider)
        self._thread = QThread(self)
        self._worker.moveToThread(self._thread)
        self._thread.start()
        # WS client (on UI thread for simplicity)
        self._ws = BinanceWsClient()
        self._ws.tick.connect(self._apply_updates)
        self._ws.error.connect(self._on_ws_error)
        self._ws.connectedChanged.connect(self._on_ws_connected)
        # Kline WS (single active symbol)
        self._kws = BinanceKlineWsClient()
        self._kws.kline.connect(self._on_kline)
        self._kws.error.connect(self._on_ws_error)
        # Wire signals
        self.requestFetch.connect(self._worker.fetch)
        self._worker.resultReady.connect(self._on_result)
        self._worker.error.connect(self._on_error)
        # Timer for periodic updates
        self._busy = False
        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._tick)
        self._timer.start()
        # Start WS in auto mode
        self._ws.start(self.symbols)
        # Start kline for first selection if candle mode chosen later
        # Initial render rows
        self._sync_table_rows()
    # ----- UI Build -----
    def _build_toolbar_min(self) -> None:
        # Keep toolbar minimal; main controls live in the sidebar.
        tb = QToolBar("Toolbar", self)
        tb.setMovable(False)
        self.addToolBar(Qt.TopToolBarArea, tb)
    def _build_sidebar(self) -> None:
        dock = QDockWidget("Controls", self)
        dock.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable)
        scroll = QScrollArea(dock)
        scroll.setWidgetResizable(True)
        panel = QWidget()
        v = QVBoxLayout(panel)
        v.setContentsMargins(10, 10, 10, 10)
        v.setSpacing(10)
        # Symbols
        g_symbols = QGroupBox("Symbols")
        vs = QVBoxLayout(g_symbols)
        self.input = QLineEdit(self)
        self.input.setPlaceholderText("Add symbol e.g. BTCUSDT or BTC/USDT")
        self.input.returnPressed.connect(self._add_symbol_from_input)
        vs.addWidget(self.input)
        hb = QHBoxLayout()
        btn_add = QPushButton("Add", self)
        btn_add.clicked.connect(self._add_symbol_from_input)
        btn_rm = QPushButton("Remove Selected", self)
        btn_rm.clicked.connect(self._remove_selected)
        hb.addWidget(btn_add)
        hb.addWidget(btn_rm)
        vs.addLayout(hb)
        v.addWidget(g_symbols)
        # Data source
        g_src = QGroupBox("Data Source")
        ls = QVBoxLayout(g_src)
        self.source_combo = QComboBox(self)
        self.source_combo.addItems([
            "Auto (WS→REST)",
            "Binance WS",
            "Binance REST",
            "CoinGecko REST",
            "Coinbase REST",
        ])
        self.source_combo.currentIndexChanged.connect(self._on_source_changed)
        ls.addWidget(self.source_combo)
        v.addWidget(g_src)
        # Chart
        g_chart = QGroupBox("Chart")
        lc = QVBoxLayout(g_chart)
        self.chart_mode_combo = QComboBox(self)
        self.chart_mode_combo.addItems(["Line", "Candle (1m)"])
        self.chart_mode_combo.currentIndexChanged.connect(self._on_chart_mode)
        lc.addWidget(self.chart_mode_combo)
        self.act_percent_axis = QCheckBox("Percent Axis", self)
        self.act_percent_axis.toggled.connect(self._on_percent_axis)
        lc.addWidget(self.act_percent_axis)
        btn_reset = QPushButton("Reset Zoom", self)
        btn_reset.clicked.connect(self._reset_zoom)
        lc.addWidget(btn_reset)
        v.addWidget(g_chart)
        # Columns
        g_cols = QGroupBox("Columns")
        lcols = QVBoxLayout(g_cols)
        self._col_actions = {}
        for name in ["Last", "Bid", "Ask", "24h %", "24h High", "24h Low", "24h Vol", "Turnover", "Time"]:
            cb = QCheckBox(name, self)
            cb.setChecked(True)
            cb.toggled.connect(self._toggle_column_visibility)
            lcols.addWidget(cb)
            self._col_actions[name] = cb
        v.addWidget(g_cols)
        # Appearance
        g_app = QGroupBox("Appearance")
        la = QVBoxLayout(g_app)
        self.appearance_combo = QComboBox(self)
        self.appearance_combo.addItems(["Dark", "Light"])
        self.appearance_combo.currentIndexChanged.connect(self._on_theme_changed)
        la.addWidget(self.appearance_combo)
        btn_accent = QPushButton("Accent…", self)
        btn_accent.clicked.connect(self._choose_accent)
        la.addWidget(btn_accent)
        self.act_tray_on_close = QCheckBox("Minimize to tray on close", self)
        self.act_tray_on_close.setChecked(True)
        self.act_tray_on_close.toggled.connect(lambda v: setattr(self, "_minimize_to_tray", v))
        la.addWidget(self.act_tray_on_close)
        v.addWidget(g_app)
        v.addStretch(1)
        scroll.setWidget(panel)
        dock.setWidget(scroll)
        self.addDockWidget(Qt.LeftDockWidgetArea, dock)
        self.sidebar_dock = dock
    def _build_table(self) -> None:
        self.table = QTableWidget(self)
        self.table.setColumnCount(10)
        self.table.setHorizontalHeaderLabels(["Symbol", "Last", "Bid", "Ask", "24h %", "24h High", "24h Low", "24h Vol", "Turnover", "Time"])
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSortingEnabled(True)
        try:
            self.table.verticalHeader().setDefaultSectionSize(34)
        except Exception:
            pass
        # Context menu for alerts
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._on_table_menu)
        self.setCentralWidget(self.table)
        self.table.itemSelectionChanged.connect(self._on_selection_changed)
    # ----- Helpers -----
    def _normalize_symbol(self, s: str) -> str:
        return s.replace("/", "").replace("-", "").replace(" ", "").upper()
    def _sync_table_rows(self) -> None:
        self.table.setRowCount(len(self.symbols))
        for row, sym in enumerate(self.symbols):
            self.table.setItem(row, 0, QTableWidgetItem(sym))
            for col in range(1, 9):
                self.table.setItem(row, col, NumericItem("-", 0.0))
            self.table.setItem(row, 9, QTableWidgetItem("-"))
            # sparkline widget
            sp = SparklineWidget(color=self.accent_color, left_padding=64)
            self.table.setCellWidget(row, 0, sp)
            self._sparks[sym] = sp
    def _row_for_symbol(self, sym: str) -> int:
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item and item.text().upper() == sym.upper():
                return row
        return -1
    def _add_symbol_from_input(self) -> None:
        raw = self.input.text().strip()
        if not raw:
            return
        sym = self._normalize_symbol(raw)
        if sym in self.symbols:
            self.input.clear()
            return
        self.symbols.append(sym)
        self._sync_table_rows()
        self._ws.set_symbols(self.symbols)
        self.input.clear()
    def _remove_selected(self) -> None:
        rows = {idx.row() for idx in self.table.selectionModel().selectedRows()}
        if not rows:
            return
        syms = [self.table.item(r, 0).text() for r in rows]
        self.symbols = [s for s in self.symbols if s not in syms]
        self._sync_table_rows()
        self._ws.set_symbols(self.symbols)
    def _tick(self) -> None:
        # Poll only in REST modes; in auto only when WS not connected
        should_poll = (self.mode in ("binance", "coingecko", "coinbase")) or (
            self.mode == "auto" and not self._ws_connected
        )
        if should_poll:
            if self._busy:
                return
            self._busy = True
            self.requestFetch.emit(self.rest_source, self.symbols)
    def _apply_updates(self, packed: dict) -> None:
        for sym, d in packed.items():
            row = self._row_for_symbol(sym)
            if row < 0:
                continue
            last = float(d.get("last", 0.0))
            chg = float(d.get("change_pct", 0.0))
            bid = float(d.get("bid", 0.0))
            ask = float(d.get("ask", 0.0))
            high = float(d.get("high", 0.0))
            low = float(d.get("low", 0.0))
            vol = float(d.get("volume", 0.0))
            qvol = float(d.get("quote_volume", 0.0))
            ts = datetime.fromisoformat(d["ts"]).strftime("%H:%M:%S") if isinstance(d.get("ts"), str) else datetime.now().strftime("%H:%M:%S")
            # Update numeric items (for sorting)
            self._set_numeric(row, 1, self._fmt_price(last), last)
            self._set_numeric(row, 2, self._fmt_price(bid), bid)
            self._set_numeric(row, 3, self._fmt_price(ask), ask)
            self._set_numeric(row, 4, f"{chg:.2f}%", chg)
            self._set_numeric(row, 5, self._fmt_price(high), high)
            self._set_numeric(row, 6, self._fmt_price(low), low)
            self._set_numeric(row, 7, self._fmt_volume(vol), vol)
            self._set_numeric(row, 8, self._fmt_volume(qvol), qvol)
            self.table.item(row, 9).setText(ts)
            # Change color
            color = Qt.green if chg >= 0 else Qt.red
            self.table.item(row, 1).setForeground(color)
            self.table.item(row, 4).setForeground(color)
            # Alerts
            self._check_alerts(sym, last)
            # History & chart
            self._push_price(sym, last)
            self._update_chart_if_selected(sym)
            # Sparkline update
            sp = self._sparks.get(sym)
            if sp:
                # Use last ~50 points of price history
                hist = list(self.price_history.get(sym, []))[-50:]
                sp.update_data([v for _, v in hist], color=self.accent_color)
    @Slot(dict)
    def _on_result(self, packed: dict) -> None:
        try:
            self._apply_updates(packed)
            self._rest_failures = 0
        finally:
            self._busy = False
    @Slot(str)
    def _on_error(self, msg: str) -> None:
        self._busy = False
        # Avoid modal spam; show a transient status message instead
        self.statusBar().showMessage(f"Fetch error: {msg}", 5000)
        # Simple failover chain when in auto mode
        if self.mode == "auto":
            self._rest_failures += 1
            if self.rest_source == "binance" and self._rest_failures >= 2:
                self.rest_source = "coingecko"
                self.statusBar().showMessage("Fallback to REST (CoinGecko)", 5000)
            elif self.rest_source == "coingecko" and self._rest_failures >= 4:
                self.rest_source = "coinbase"
                self.statusBar().showMessage("Fallback to REST (Coinbase)", 5000)
        else:
            self._rest_failures = 0
    # WS events
    @Slot(bool)
    def _on_ws_connected(self, ok: bool) -> None:
        if ok:
            self.statusBar().showMessage("WS connected", 3000)
            self._ws_failures = 0
            self._ws_connected = True
        else:
            # disconnected
            if self.mode in ("auto", "binance-ws"):
                self._ws_failures += 1
                self.statusBar().showMessage("WS disconnected", 3000)
                self._ws_connected = False
                if self.mode == "auto" and self._ws_failures >= 2:
                    # Fallback to REST
                    self.rest_source = "binance"
                    self.statusBar().showMessage("Fallback to REST (Binance)", 5000)
    @Slot(str)
    def _on_ws_error(self, msg: str) -> None:
        self.statusBar().showMessage(f"WS error: {msg}", 5000)
        if self.mode == "auto":
            self._ws_failures += 1
            if self._ws_failures >= 2:
                self.rest_source = "binance"
                self.statusBar().showMessage("Fallback to REST (Binance)", 5000)
    # ----- Formatters -----
    def _fmt_price(self, v: float) -> str:
        if v >= 100:
            return f"{v:,.2f}"
        if v >= 1:
            return f"{v:,.4f}"
        return f"{v:.8f}".rstrip("0").rstrip(".")
    def _fmt_volume(self, v: float) -> str:
        units = ["", "K", "M", "B"]
        i = 0
        while v >= 1000 and i < len(units) - 1:
            v /= 1000.0
            i += 1
        return f"{v:.2f}{units[i]}"
    def _set_numeric(self, row: int, col: int, text: str, value: float) -> None:
        item = self.table.item(row, col)
        if not isinstance(item, NumericItem):
            item = NumericItem(text, value)
            self.table.setItem(row, col, item)
        else:
            item.setText(text)
            item.value = value
    # ----- Alerts -----
    def _on_table_menu(self, pos) -> None:
        index = self.table.indexAt(pos)
        if not index.isValid():
            return
        row = index.row()
        sym = self.table.item(row, 0).text()
        m = QMenu(self)
        act_up = m.addAction("Set Upper Alert…")
        act_dn = m.addAction("Set Lower Alert…")
        m.addSeparator()
        act_clr = m.addAction("Clear Alerts")
        chosen = m.exec(self.table.viewport().mapToGlobal(pos))
        if chosen == act_up:
            val, ok = QInputDialog.getDouble(self, "Upper Alert", f"Price >= (for {sym})", 0.0, 0.0, 1e12, 6)
            if ok:
                self._set_alert(sym, upper=val)
        elif chosen == act_dn:
            val, ok = QInputDialog.getDouble(self, "Lower Alert", f"Price <= (for {sym})", 0.0, 0.0, 1e12, 6)
            if ok:
                self._set_alert(sym, lower=val)
        elif chosen == act_clr:
            self.alerts.pop(sym, None)
            self.statusBar().showMessage(f"Cleared alerts for {sym}", 3000)
    def _set_alert(self, sym: str, upper: float | None = None, lower: float | None = None) -> None:
        a = self.alerts.get(sym, {"upper": None, "lower": None, "armed_upper": True, "armed_lower": True})
        if upper is not None:
            a["upper"] = upper
            a["armed_upper"] = True
        if lower is not None:
            a["lower"] = lower
            a["armed_lower"] = True
        self.alerts[sym] = a
        self.statusBar().showMessage(f"Alert set for {sym}", 3000)
    def _check_alerts(self, sym: str, price: float) -> None:
        a = self.alerts.get(sym)
        if not a:
            return
        hit = None
        if a.get("upper") is not None and a.get("armed_upper") and price >= float(a["upper"]):
            hit = f"{sym} >= {a['upper']}"
            a["armed_upper"] = False
        if a.get("lower") is not None and a.get("armed_lower") and price <= float(a["lower"]):
            hit = f"{sym} <= {a['lower']}"
            a["armed_lower"] = False
        if hit:
            QApplication.beep()
            if self.tray.isVisible():
                self.tray.showMessage("Crypto Ticker Alert", hit, QSystemTrayIcon.Information, 8000)
    # ----- Columns & Source -----
    def _toggle_column_visibility(self) -> None:
        names = ["Last", "Bid", "Ask", "24h %", "24h High", "24h Low", "24h Vol", "Turnover", "Time"]
        for i, n in enumerate(names, start=1):
            act = self._col_actions[n]
            self.table.setColumnHidden(i, not act.isChecked())
    def _on_source_changed(self) -> None:
        idx = self.source_combo.currentIndex()
        opts = ["auto", "binance-ws", "binance", "coingecko", "coinbase"]
        self.mode = opts[idx]
        if self.mode == "binance-ws":
            self._ws.start(self.symbols)
        elif self.mode == "auto":
            self._ws.start(self.symbols)
            self.rest_source = "binance"
        else:
            # REST modes
            self.rest_source = self.mode
            self.statusBar().showMessage(f"REST source: {self.rest_source}", 3000)
    def _on_chart_mode(self) -> None:
        mode = self.chart_mode_combo.currentIndex()
        is_candle = mode == 1
        self.candle_series.setVisible(is_candle)
        self.series_main.setVisible(not is_candle)
        self.series_ma_fast.setVisible(not is_candle)
        self.series_ma_slow.setVisible(not is_candle)
        self.area_fill.setVisible(not is_candle)
        self.act_percent_axis.setEnabled(not is_candle)
        rows = self.table.selectionModel().selectedRows()
        sym = self.table.item(rows[0].row(), 0).text() if rows else self.symbols[0]
        if is_candle:
            self._ensure_kline(sym)
        self._update_chart(sym)
    def _on_percent_axis(self) -> None:
        rows = self.table.selectionModel().selectedRows()
        if rows:
            sym = self.table.item(rows[0].row(), 0).text()
        else:
            sym = self.symbols[0]
        self._update_chart(sym)
    def _reset_zoom(self) -> None:
        self.chart.zoomReset()
        self.vol_chart.zoomReset()
        rows = self.table.selectionModel().selectedRows()
        sym = self.table.item(rows[0].row(), 0).text() if rows else self.symbols[0]
        self._update_chart(sym)
    # ----- Tray & Theme -----
    def _build_tray(self) -> None:
        self.tray = QSystemTrayIcon(self)
        icon = self.style().standardIcon(QStyle.SP_ComputerIcon)
        self.tray.setIcon(icon)
        self.setWindowIcon(icon)
        menu = QMenu()
        act_show = QAction("Show", self)
        act_quit = QAction("Quit", self)
        act_show.triggered.connect(self.showNormal)
        act_quit.triggered.connect(QApplication.instance().quit)
        menu.addAction(act_show)
        menu.addAction(act_quit)
        self.tray.setContextMenu(menu)
        self.tray.show()
        self.tray.activated.connect(self._on_tray_activated)
    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            if self.isHidden():
                self.showNormal()
            else:
                self.hide()
    # ----- Chart -----
    def _build_chart(self) -> None:
        # History: symbol -> deque of (ms, price)
        self.price_history: Dict[str, deque[tuple[float, float]]] = {}
        self.chart = QChart()
        self.chart.setBackgroundVisible(False)
        self.chart.legend().hide()
        # Series
        self.series_main = QLineSeries()
        self.series_ma_fast = QLineSeries()
        self.series_ma_slow = QLineSeries()
        self.series_base = QLineSeries()  # for area fill baseline
        self.area_fill = QAreaSeries(self.series_main, self.series_base)
        self.area_fill.setOpacity(0.25)
        # Candles
        self.candle_series = QCandlestickSeries()
        self.candle_series.setIncreasingColor(QColor('#00C853'))
        self.candle_series.setDecreasingColor(QColor('#FF5252'))
        # Axes
        self.axisX = QDateTimeAxis()
        self.axisX.setFormat("HH:mm:ss")
        self.axisX.setTickCount(6)
        self.axisY = QValueAxis()
        self.axisY.setLabelFormat("%.2f")
        # Add series in order (fill under main, then main and MAs)
        for s in (self.area_fill, self.series_main, self.series_ma_fast, self.series_ma_slow, self.candle_series):
            self.chart.addSeries(s)
        self.chart.addAxis(self.axisX, Qt.AlignBottom)
        self.chart.addAxis(self.axisY, Qt.AlignLeft)
        for s in (self.area_fill, self.series_main, self.series_ma_fast, self.series_ma_slow, self.candle_series):
            s.attachAxis(self.axisX)
            s.attachAxis(self.axisY)
        # Toggle visibility initially (line mode default)
        self.candle_series.setVisible(False)
        # View with crosshair
        view = ChartViewCrosshair(self.chart)
        view.setRenderHint(QPainter.Antialiasing)
        view.setSeries(self.series_main)
        view.setRubberBand(QChartView.RectangleRubberBand)
        dock = QDockWidget("Chart", self)
        dock.setWidget(view)
        dock.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable)
        self.addDockWidget(Qt.RightDockWidgetArea, dock)
        self.chart_view = view
        self.chart_dock = dock
        # Volume sub chart (bars)
        self.vol_chart = QChart()
        self.vol_chart.setBackgroundVisible(False)
        self.vol_chart.legend().hide()
        self.vol_series = QBarSeries()
        self.vol_set = QBarSet("")
        self.vol_series.append(self.vol_set)
        self.vol_axisX = QBarCategoryAxis()
        self.vol_axisY = QValueAxis()
        self.vol_axisY.setLabelFormat("%.0f")
        self.vol_chart.addSeries(self.vol_series)
        self.vol_chart.addAxis(self.vol_axisX, Qt.AlignBottom)
        self.vol_chart.addAxis(self.vol_axisY, Qt.AlignLeft)
        self.vol_series.attachAxis(self.vol_axisX)
        self.vol_series.attachAxis(self.vol_axisY)
        vol_view = QChartView(self.vol_chart)
        vol_view.setRenderHint(QPainter.Antialiasing)
        vol_dock = QDockWidget("Volume", self)
        vol_dock.setWidget(vol_view)
        vol_dock.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable)
        self.addDockWidget(Qt.RightDockWidgetArea, vol_dock)
        self.vol_view = vol_view
        self.vol_dock = vol_dock
    def _push_price(self, sym: str, price: float, max_points: int = 600) -> None:
        dq = self.price_history.get(sym)
        if dq is None:
            dq = deque(maxlen=max_points)
            self.price_history[sym] = dq
        ms = int(datetime.now().timestamp() * 1000)
        dq.append((ms, price))
    def _on_selection_changed(self) -> None:
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return
        sym = self.table.item(rows[0].row(), 0).text()
        if self.chart_mode_combo.currentIndex() == 1:  # Candle
            self._ensure_kline(sym)
        self._update_chart(sym)
    def _update_chart_if_selected(self, sym: str) -> None:
        rows = self.table.selectionModel().selectedRows()
        if rows and self.table.item(rows[0].row(), 0).text() == sym:
            self._update_chart(sym)
    def _update_chart(self, sym: str) -> None:
        if self.chart_mode_combo.currentIndex() == 1:
            # Candle mode
            self._update_candle_chart(sym)
            return
        data = list(self.price_history.get(sym, []))
        if not data:
            self.series_main.clear(); self.series_ma_fast.clear(); self.series_ma_slow.clear(); self.series_base.clear()
            return
        xs = [x for x, _ in data]
        ys = [y for _, y in data]
        # Percent axis support
        if self.act_percent_axis.isChecked():
            base = ys[0]
            ys_disp = [((y / base) - 1.0) * 100.0 for y in ys]
            label = lambda v: f"{v:.2f}%"
        else:
            ys_disp = ys
            label = self._fmt_price
        pts = [QPointF(x, y) for x, y in zip(xs, ys_disp)]
        self.series_main.replace(pts)
        # Axis ranges
        x0, x1 = xs[0], xs[-1]
        lo, hi = min(ys_disp), max(ys_disp)
        pad = (hi - lo) * 0.05 if hi != lo else (hi or 1) * 0.01
        self.axisX.setRange(QDateTime.fromMSecsSinceEpoch(int(x0)), QDateTime.fromMSecsSinceEpoch(int(x1)))
        self.axisY.setRange(lo - pad, hi + pad)
        # Label format
        if self.act_percent_axis.isChecked():
            self.axisY.setLabelFormat("%.2f%")
        else:
            ref = ys[-1]
            if ref >= 100:
                self.axisY.setLabelFormat("%.2f")
            elif ref >= 1:
                self.axisY.setLabelFormat("%.4f")
            else:
                self.axisY.setLabelFormat("%.8f")
        # Area baseline at current low
        base_pts = [QPointF(x, lo - pad) for x in xs]
        self.series_base.replace(base_pts)
        # Moving averages
        def sma(values: List[float], window: int) -> List[float]:
            out: List[float] = []
            s = 0.0
            q: deque[float] = deque()
            for v in values:
                s += v; q.append(v)
                if len(q) > window:
                    s -= q.popleft()
                out.append(s / len(q))
            return out
        fast = 20
        slow = 60
        ma_f = sma(ys_disp, fast)
        ma_s = sma(ys_disp, slow)
        self.series_ma_fast.replace([QPointF(x, y) for x, y in zip(xs, ma_f)])
        self.series_ma_slow.replace([QPointF(x, y) for x, y in zip(xs, ma_s)])
        # Last price/percent label near last point
        last_pt = QPointF(xs[-1], ys_disp[-1])
        pos = self.chart.mapToPosition(last_pt, self.series_main)
        if not hasattr(self, "_last_label"):
            self._last_label = QGraphicsSimpleTextItem("")
            self._last_label.setZValue(1002)
            self.chart.scene().addItem(self._last_label)
        self._last_label.setText(label(ys_disp[-1]))
        self._last_label.setPos(pos.x() + 6, pos.y() - 16)
        self.chart.setTitle(sym)
    def _ensure_kline(self, sym: str) -> None:
        # Start kline stream for selected symbol
        self._kws.start(sym, "1m")
        if not hasattr(self, "ohlc_history"):
            self.ohlc_history: Dict[str, List[dict]] = {}
    @Slot(dict)
    def _on_kline(self, d: dict) -> None:
        sym = d.get("symbol", "")
        arr = self.ohlc_history.get(sym)
        if arr is None:
            arr = []
            self.ohlc_history[sym] = arr
        # maintain up to 120 candles
        if arr and arr[-1].get("t") == d["t"]:
            arr[-1] = d
        else:
            arr.append(d)
            if len(arr) > 120:
                del arr[0: len(arr) - 120]
        self._update_candle_chart(sym)
    def _update_candle_chart(self, sym: str) -> None:
        data = self.ohlc_history.get(sym, [])
        self.candle_series.clear()
        if not data:
            return
        # Build candle sets and volume bars
        categories = []
        vols = []
        for k in data:
            cs = QCandlestickSet(k["o"], k["h"], k["l"], k["c"], k["t"])  # timestamp as timestamp
            self.candle_series.append(cs)
            ts = datetime.fromtimestamp(k["t"] / 1000.0).strftime("%H:%M")
            categories.append(ts)
            vols.append(k.get("q", 0.0))
        # X/Y ranges
        xs = [k["t"] for k in data]
        ys = [k["o"] for k in data] + [k["h"] for k in data] + [k["l"] for k in data] + [k["c"] for k in data]
        lo, hi = min(ys), max(ys)
        pad = (hi - lo) * 0.05 if hi != lo else (hi or 1) * 0.01
        self.axisX.setRange(QDateTime.fromMSecsSinceEpoch(int(xs[0])), QDateTime.fromMSecsSinceEpoch(int(xs[-1])))
        self.axisY.setRange(lo - pad, hi + pad)
        self.axisY.setLabelFormat("%.2f")
        # Update bottom volume chart
        self.vol_series.clear()
        if vols:
            self.vol_set = QBarSet("")
            self.vol_set.append(vols)
            self.vol_series.append(self.vol_set)
            self.vol_axisX.clear()
            self.vol_axisX.append(categories)
            vhi = max(vols)
            self.vol_axisY.setRange(0.0, vhi * 1.2)
    # ----- Theme -----
    def _apply_theme(self, mode: str = "dark") -> None:
        self.theme_mode = mode
        # Build and apply global stylesheet via theme module
        style = theme.build_stylesheet(mode, self.accent_color)
        self.setStyleSheet(style)
        # Chart theming
        theme.apply_chart_theme(
            self.chart,
            self.chart_view,
            self.series_main,
            self.series_ma_fast,
            self.series_ma_slow,
            self.area_fill,
            self.axisX,
            self.axisY,
            (self.vol_axisX, self.vol_axisY),
            mode,
            self.accent_color,
        )
        # Update sparklines with new color
        for sp in getattr(self, "_sparks", {}).values():
            sp.update_color(self.accent_color)
    def _on_theme_changed(self) -> None:
        idx = self.appearance_combo.currentIndex()
        self._apply_theme("dark" if idx == 0 else "light")
    def _choose_accent(self) -> None:
        col = QColorDialog.getColor(self.accent_color, self, "Choose Accent Color")
        if col.isValid():
            self.accent_color = col
            self._apply_theme(self.theme_mode)
    # ----- Lifecycle -----
    def closeEvent(self, event):  # type: ignore[override]
        if self._minimize_to_tray and QSystemTrayIcon.isSystemTrayAvailable():
            event.ignore()
            self.hide()
            if self._tray_first_hide:
                self.tray.showMessage("Crypto Ticker", "Still running in system tray", QSystemTrayIcon.Information, 4000)
                self._tray_first_hide = False
            return
        self._timer.stop()
        self._thread.quit()
        self._thread.wait(2000)
        try:
            self._provider._client.close()
        except Exception:
            pass
        self._ws.stop()
        return super().closeEvent(event)
def main() -> int:
    # Fix potential invalid SSL env vars and prefer OS trust store
    try:
        fix_ssl_env()
    except Exception:
        pass
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    return app.exec()
if __name__ == "__main__":
    raise SystemExit(main())






