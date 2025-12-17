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
    klinesReady = Signal(str, str, list)  # symbol, interval, list[dict]
    klineError = Signal(str)
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

    @Slot(str, str, int)
    def fetch_klines(self, symbol: str, interval: str, limit: int) -> None:
        try:
            data = self._provider.fetch_klines(symbol, interval=interval, limit=limit)
            self.klinesReady.emit(symbol, interval, data)
        except Exception as e:
            self.klineError.emit(str(e))
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

# Paper trading imports
from app.trading.portfolio import PortfolioManager, PortfolioSerializer
from app.trading.orders import OrderService, BinanceDataProviderAdapter
from app.ui.paper_trading import PaperTradingDockContent
from app.storage.storage import JsonFileStorage

# Acrylic effect imports
from app.ui.acrylic import AcrylicPanel
# Animation imports
from app.ui.animations import PulseAnimator, AnimatedTableItem

# Navigation imports
from app.ui.navigation import PageType, NavigationSidebar
from app.ui.page_container import PageContainer
from app.ui.pages.market_overview import MarketOverviewPage
from app.ui.pages.paper_trading_page import PaperTradingFullPage
from app.ui.pages.chart_analysis import ChartAnalysisPage
from app.ui.pages.settings import SettingsPage, SYMBOLS_STORAGE_KEY, DEFAULT_TRACKED_SYMBOLS

from decimal import Decimal
from pathlib import Path
import logging

logger = logging.getLogger(__name__)
class MainWindow(QMainWindow):
    requestFetch = Signal(str, list)
    requestKlines = Signal(str, str, int)
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Crypto Ticker - PySide6")
        self.resize(1200, 700)
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
        self.theme_mode = "dark"
        self.accent_color = QColor("#0A84FF")
        # UI "TIMEFRAME" is treated as a lookback window (e.g. 4h = last 4 hours),
        # while _kline_interval is the candle interval used for Binance kline streams.
        self._kline_window: str = "1m"
        self._kline_interval: str = "1m"
        self._active_kline_symbol: str = ""
        
        # Price history for charts
        self.price_history: Dict[str, deque[tuple[float, float]]] = {}
        
        # Backend setup first (needed for pages)
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
        self.requestKlines.connect(self._worker.fetch_klines)
        self._worker.resultReady.connect(self._on_result)
        self._worker.error.connect(self._on_error)
        self._worker.klinesReady.connect(self._on_klines_ready)
        self._worker.klineError.connect(self._on_kline_error)
        
        # Paper trading setup (before UI so pages can use it)
        self._setup_paper_trading()
        self.symbols = self._load_tracked_symbols()
        
        # UI - New navigation-based layout
        self._build_navigation_ui()
        self._build_tray()
        
        # Apply theme
        self._apply_theme(self.theme_mode)
        
        # Timer for periodic updates
        self._busy = False
        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._tick)
        self._timer.start()
        
        # Start WS in auto mode
        self._ws.start(self.symbols)
        
        # Initialize pages with data
        self._init_page_data()

        # Ensure state is persisted on app quit (e.g., tray "Quit")
        self._shutdown_started = False
        self._portfolio_save_timer = QTimer(self)
        self._portfolio_save_timer.setSingleShot(True)
        self._portfolio_save_timer.setInterval(750)
        self._portfolio_save_timer.timeout.connect(self._save_portfolio)
    # ----- UI Build -----
    def _build_navigation_ui(self) -> None:
        """Build the new navigation-based UI layout.
        
        Implements Requirements 1.1: Navigation sidebar on left edge
        with PageContainer as central widget.
        """
        # Create main container widget
        main_widget = QWidget()
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Create navigation sidebar (Requirements 1.1)
        self._nav_sidebar = NavigationSidebar()
        main_layout.addWidget(self._nav_sidebar)
        
        # Create page container
        self._page_container = PageContainer()
        main_layout.addWidget(self._page_container, 1)
        
        # Create and register pages
        self._create_pages()
        self._register_pages()
        
        # Wire up navigation signals (Requirements 1.3, 1.4, 1.5)
        self._nav_sidebar.pageSelected.connect(self._page_container.switch_to)
        self._page_container.pageChanged.connect(self._nav_sidebar.set_current_page)
        
        # Set default page to MarketOverview
        self._nav_sidebar.set_current_page(PageType.MARKET_OVERVIEW)
        self._page_container.switch_to(PageType.MARKET_OVERVIEW, animate=False)
        
        self.setCentralWidget(main_widget)
    
    def _create_pages(self) -> None:
        """Create all page widgets."""
        # Market Overview Page (Requirements 2.1, 2.2, 2.3)
        self._market_page = MarketOverviewPage()
        self._market_page.symbolSelected.connect(self._on_market_symbol_selected)
        
        # Paper Trading Page (Requirements 3.1, 3.2, 3.3, 3.4)
        self._trading_page = PaperTradingFullPage(
            self._portfolio,
            self._order_service,
            self._data_provider,
        )
        self._trading_page.resetRequested.connect(self._on_reset_paper_trading)
        self._trading_page.orderSubmitted.connect(self._on_paper_trade_executed)
        
        # Chart Analysis Page (Requirements 4.1, 4.2, 4.3, 4.4)
        self._chart_page = ChartAnalysisPage()
        self._chart_page.symbolChanged.connect(self._on_chart_symbol_changed)
        self._chart_page.timeframeChanged.connect(self._on_chart_timeframe_changed)
        
        # Settings Page (Requirements 5.1, 5.2, 5.3, 5.4, 5.5)
        self._settings_page = SettingsPage(storage=self._storage)
        self._settings_page.dataSourceChanged.connect(self._on_data_source_changed)
        self._settings_page.themeChanged.connect(self._on_settings_theme_changed)
        self._settings_page.accentColorChanged.connect(self._on_settings_accent_changed)
        self._settings_page.columnVisibilityChanged.connect(self._on_column_visibility_changed)
        self._settings_page.settingChanged.connect(self._on_setting_changed)
        self._settings_page.symbolsChanged.connect(self._on_tracked_symbols_changed)
        if hasattr(self._settings_page, "symbolsChanged"):
            self._settings_page.symbolsChanged.connect(self._on_symbols_changed)
    
    def _register_pages(self) -> None:
        """Register all pages with the page container."""
        self._page_container.add_page(PageType.MARKET_OVERVIEW, self._market_page)
        self._page_container.add_page(PageType.PAPER_TRADING, self._trading_page)
        self._page_container.add_page(PageType.CHART_ANALYSIS, self._chart_page)
        self._page_container.add_page(PageType.SETTINGS, self._settings_page)
    
    def _init_page_data(self) -> None:
        """Initialize pages with current data."""
        # Set symbols for market overview and chart pages
        self._market_page.set_symbols(self.symbols)
        self._chart_page.set_symbols(self.symbols)
        if hasattr(self, "_trading_page"):
            prices = {}
            if hasattr(self, "_data_provider") and hasattr(self._data_provider, "get_prices_snapshot"):
                try:
                    prices = self._data_provider.get_prices_snapshot()
                except Exception:
                    prices = {}
            self._trading_page.set_symbols(self.symbols, prices)

        # Initialize paper trading symbol dropdown
        try:
            prices = {}
            for sym in self.symbols:
                p = self._data_provider.get_current_price(sym)
                if p is not None:
                    prices[sym] = p
            if hasattr(self, "_trading_page") and hasattr(self._trading_page, "_trading_panel"):
                self._trading_page._trading_panel.update_symbol_list(self.symbols, prices)
        except Exception:
            pass
        
        # Set accent color
        self._market_page.set_accent_color(self.accent_color)
        self._chart_page.set_accent_color(self.accent_color)
    
    def _on_market_symbol_selected(self, symbol: str) -> None:
        """Handle symbol selection from market overview page."""
        # Update trading page with selected symbol
        self._trading_page.set_symbol(symbol)
        # Update chart page with selected symbol
        self._chart_page.set_symbol(symbol)
        # Start kline stream for chart
        self._ensure_kline(symbol)
    
    def _on_chart_symbol_changed(self, symbol: str) -> None:
        """Handle symbol change from chart analysis page."""
        sym = self._normalize_symbol(symbol)
        self._active_kline_symbol = sym
        # Clear old candles immediately so we don't show stale data while backfilling/reconnecting.
        if hasattr(self, "_chart_page"):
            try:
                self._chart_page.update_data([])
            except Exception:
                pass
        self._ensure_kline(sym)

    def _on_chart_timeframe_changed(self, timeframe: str) -> None:
        """Handle timeframe change from chart analysis page."""
        if timeframe and timeframe != self._kline_window:
            self._kline_window = timeframe
            # Pick a candle interval suitable for the selected lookback window.
            self._kline_interval = self._choose_kline_interval(self._kline_window)
            # Clear candle data immediately (ChartAnalysisPage will clear candle series when candle mode is active).
            if hasattr(self, "_chart_page"):
                try:
                    self._chart_page.update_data([])
                except Exception:
                    pass
            # Restart kline stream for active symbol.
            sym = self._active_kline_symbol or (self._chart_page._symbol_combo.currentText() if hasattr(self, "_chart_page") else "")
            if sym:
                self._ensure_kline(sym)
    
    def _on_data_source_changed(self, source: str) -> None:
        """Handle data source change from settings page."""
        self.mode = source
        if self.mode == "binance-ws":
            self._ws.start(self.symbols)
        elif self.mode == "auto":
            self._ws.start(self.symbols)
            self.rest_source = "binance"
        else:
            self.rest_source = self.mode
            self.statusBar().showMessage(f"REST source: {self.rest_source}", 3000)

    def _on_symbols_changed(self, symbols: List[str]) -> None:
        symbols = self._sanitize_symbols(symbols)
        if not symbols:
            return

        self.symbols = symbols

        if hasattr(self, "_market_page"):
            self._market_page.set_symbols(self.symbols)
        if hasattr(self, "_chart_page"):
            self._chart_page.set_symbols(self.symbols)

        if self.mode in ("binance-ws", "auto"):
            self._ws.start(self.symbols)

        # Refresh paper trading symbol dropdown (prices are optional)
        try:
            prices = {}
            for sym in self.symbols:
                p = self._data_provider.get_current_price(sym)
                if p is not None:
                    prices[sym] = p
            if hasattr(self, "_trading_page") and hasattr(self._trading_page, "_trading_panel"):
                self._trading_page._trading_panel.update_symbol_list(self.symbols, prices)
        except Exception:
            pass

    def _on_reset_paper_trading(self) -> None:
        """Reset the paper trading simulation (portfolio + history) and persist it."""
        try:
            initial_balance = self._portfolio.get_initial_balance()
        except Exception:
            initial_balance = Decimal("10000")

        self._portfolio.reset(initial_balance)
        self._save_portfolio()
        if hasattr(self, "_trading_page"):
            self._trading_page.refresh()
        self.statusBar().showMessage("Paper Trading reset", 4000)

    @Slot(str, str, object, object)
    def _on_paper_trade_executed(self, symbol: str, order_type: str, quantity, price) -> None:
        # Debounced to avoid multiple disk writes if UI emits rapidly.
        try:
            self._portfolio_save_timer.start()
        except Exception:
            try:
                self._save_portfolio()
            except Exception:
                pass
    
    def _on_settings_theme_changed(self, theme_mode: str) -> None:
        """Handle theme change from settings page."""
        self._apply_theme(theme_mode)
    
    def _on_settings_accent_changed(self, color: QColor) -> None:
        """Handle accent color change from settings page."""
        self.accent_color = color
        self._apply_theme(self.theme_mode)
        # Update page accent colors
        self._market_page.set_accent_color(color)
        self._chart_page.set_accent_color(color)
    
    def _on_column_visibility_changed(self, column_name: str, visible: bool) -> None:
        """Handle column visibility change from settings page."""
        # Column indices: Last=1, Bid=2, Ask=3, 24h%=4, High=5, Low=6, Vol=7, Turnover=8, Time=9
        col_map = {
            "Last": 1, "Bid": 2, "Ask": 3, "24h %": 4,
            "24h High": 5, "24h Low": 6, "24h Vol": 7, "Turnover": 8, "Time": 9
        }
        col_idx = col_map.get(column_name)
        if col_idx is not None:
            # Update market overview page table visibility
            self._market_page._table.setColumnHidden(col_idx, not visible)
    
    def _on_setting_changed(self, key: str, value) -> None:
        """Handle generic setting change from settings page."""
        if key == "minimize_to_tray":
            self._minimize_to_tray = value

    def _on_tracked_symbols_changed(self, symbols: list) -> None:
        """Apply tracked symbol changes from Settings page."""
        cleaned: List[str] = []
        for s in symbols:
            if not isinstance(s, str):
                continue
            sym = self._normalize_symbol(s)
            if sym and sym not in cleaned:
                cleaned.append(sym)
        if not cleaned:
            cleaned = DEFAULT_TRACKED_SYMBOLS.copy()

        self.symbols = cleaned

        if hasattr(self, "_market_page"):
            self._market_page.set_symbols(self.symbols)
        if hasattr(self, "_chart_page"):
            self._chart_page.set_symbols(self.symbols)
        if hasattr(self, "_trading_page"):
            prices = {}
            if hasattr(self, "_data_provider") and hasattr(self._data_provider, "get_prices_snapshot"):
                try:
                    prices = self._data_provider.get_prices_snapshot()
                except Exception:
                    prices = {}
            self._trading_page.set_symbols(self.symbols, prices)

        if hasattr(self, "_ws"):
            try:
                self._ws.set_symbols(self.symbols)
            except Exception:
                # Fallback to full restart
                try:
                    self._ws.start(self.symbols)
                except Exception:
                    pass
    
    def _build_toolbar_min(self) -> None:
        # Keep toolbar minimal; main controls live in the sidebar.
        tb = QToolBar("Toolbar", self)
        tb.setMovable(False)
        self.addToolBar(Qt.TopToolBarArea, tb)

    # ----- Helpers -----
    def _normalize_symbol(self, s: str) -> str:
        return s.replace("/", "").replace("-", "").replace(" ", "").upper()

    def _sanitize_symbols(self, symbols) -> List[str]:
        if not isinstance(symbols, list):
            return []
        seen: set[str] = set()
        out: List[str] = []
        for x in symbols:
            if not isinstance(x, str):
                continue
            sym = self._normalize_symbol(x.strip())
            if sym and sym not in seen:
                seen.add(sym)
                out.append(sym)
        return out

    def _load_tracked_symbols(self) -> List[str]:
        """Load tracked symbols from storage (fallback to current defaults)."""
        storage = getattr(self, "_storage", None)
        if storage is None:
            cleaned = self._sanitize_symbols(getattr(self, "symbols", None))
            return cleaned or DEFAULT_TRACKED_SYMBOLS.copy()

        try:
            data = storage.load(SYMBOLS_STORAGE_KEY)
        except Exception:
            data = None

        loaded = self._sanitize_symbols(data)
        if loaded:
            self.symbols = loaded
            return self.symbols

        # Persist current defaults if nothing stored yet
        cleaned_defaults = self._sanitize_symbols(getattr(self, "symbols", None))
        self.symbols = cleaned_defaults or DEFAULT_TRACKED_SYMBOLS.copy()
        try:
            storage.save(SYMBOLS_STORAGE_KEY, self.symbols)
        except Exception:
            pass
        return self.symbols
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
        # Update market overview page with price data (Requirements 2.4)
        if hasattr(self, '_market_page'):
            self._market_page.set_price_data(packed)
        
        # Update chart analysis page with price points
        for sym, d in packed.items():
            last = float(d.get("last", 0.0))

            # Keep paper trading price cache in sync even in REST modes.
            if hasattr(self, "_data_provider"):
                try:
                    self._data_provider.update_price(sym, last)
                except Exception:
                    pass
             
            # Push to price history
            self._push_price(sym, last)
            
            # Update chart analysis page
            if hasattr(self, '_chart_page'):
                now_ms = datetime.now().timestamp() * 1000
                self._chart_page.add_price_point(sym, now_ms, last)
            
            # Check alerts
            self._check_alerts(sym, last)
            
            # Update paper trading page price (Requirements 3.4)
            if hasattr(self, '_trading_page'):
                self._trading_page.update_price(sym, Decimal(str(last)))
    @Slot(dict)
    def _on_result(self, packed: dict) -> None:
        try:
            self._apply_updates(packed)
            self._rest_failures = 0
        except Exception as e:
            logger.error(f"Error applying updates: {e}")
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
    # ----- Alerts -----
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
            # Pulse animation for alert row (Requirement 3.4)
            self._pulse_alert_row(sym)
    
    def _pulse_alert_row(self, sym: str, pulse_count: int = 3) -> None:
        """Create pulsing animation for alert (simplified for new UI)."""
        # Alert notification is now handled via tray notification
        pass
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
    def _setup_paper_trading(self) -> None:
        """Set up paper trading components (used by PaperTradingFullPage)."""
        # Initialize storage service
        storage_path = Path.home() / ".crypto_ticker" / "data"
        self._storage = JsonFileStorage(storage_path)
        self._load_tracked_symbols()
        
        # Initialize data provider adapter
        self._data_provider = BinanceDataProviderAdapter()
        
        # Wire WS client to data provider adapter
        self._ws.tick.connect(self._on_tick_for_paper_trading)
        self._ws.connectedChanged.connect(self._on_ws_connected_for_paper_trading)
        
        # Load or create portfolio
        self._portfolio = self._load_portfolio()
        
        # Initialize order service
        self._order_service = OrderService(self._portfolio, self._data_provider)
    
    def _load_portfolio(self) -> PortfolioManager:
        """Load portfolio from storage or create new one.
        
        Returns:
            PortfolioManager instance (restored or new)
        """
        try:
            data = self._storage.load("portfolio")
            if data is not None:
                portfolio = PortfolioSerializer.deserialize(data)
                logger.info("Portfolio restored from storage")
                return portfolio
        except Exception as e:
            logger.error(f"Failed to load portfolio, creating new: {e}")
        
        # Create new portfolio with default balance
        return PortfolioManager(Decimal("10000"))
    
    def _save_portfolio(self) -> None:
        """Save portfolio state to storage."""
        try:
            data = PortfolioSerializer.serialize(self._portfolio)
            self._storage.save("portfolio", data)
            logger.info("Portfolio saved to storage")
        except Exception as e:
            logger.error(f"Failed to save portfolio: {e}")
    
    def _on_tick_for_paper_trading(self, packed: dict) -> None:
        """Update data provider with tick data for paper trading."""
        for sym, d in packed.items():
            price = float(d.get("last", 0.0))
            if price > 0:
                self._data_provider.update_price(sym, price)
        
        # Refresh paper trading page if it exists
        if hasattr(self, "_trading_page"):
            self._trading_page.refresh()
    
    def _on_ws_connected_for_paper_trading(self, connected: bool) -> None:
        """Update data provider connection status."""
        self._data_provider.set_connected(connected)
        
        # Show status bar message for connection state changes
        if connected:
            self.statusBar().showMessage("Paper Trading: Data connection restored", 5000)
        else:
            self.statusBar().showMessage("Paper Trading: Data connection lost - Orders disabled", 8000)
        
        # Update paper trading page connection status
        if hasattr(self, "_trading_page"):
            self._trading_page.refresh()
    
    def _push_price(self, sym: str, price: float, max_points: int = 600) -> None:
        dq = self.price_history.get(sym)
        if dq is None:
            dq = deque(maxlen=max_points)
            self.price_history[sym] = dq
        ms = int(datetime.now().timestamp() * 1000)
        dq.append((ms, price))

    def _window_to_ms(self, window: str) -> int:
        tf = (window or "").strip().lower()
        if not tf:
            return 0
        try:
            n = int(tf[:-1])
        except Exception:
            return 0
        unit = tf[-1]
        if unit == "m":
            return n * 60 * 1000
        if unit == "h":
            return n * 60 * 60 * 1000
        if unit == "d":
            return n * 24 * 60 * 60 * 1000
        return 0

    def _interval_to_ms(self, interval: str) -> int:
        return self._window_to_ms(interval)

    def _choose_kline_interval(self, window: str) -> str:
        w_ms = self._window_to_ms(window)
        if w_ms <= 0:
            return "1m"
        if w_ms <= 4 * 60 * 60 * 1000:
            return "1m"
        if w_ms <= 24 * 60 * 60 * 1000:
            return "5m"
        return "15m"

    def _choose_kline_limit(self, window: str, interval: str, max_limit: int = 120) -> int:
        w_ms = self._window_to_ms(window)
        i_ms = self._interval_to_ms(interval) or 60 * 1000
        if w_ms <= 0:
            return max_limit
        need = int((w_ms + i_ms - 1) // i_ms) + 2  # small buffer
        return max(3, min(max_limit, need))

    def _ensure_kline(self, sym: str) -> None:
        # Start kline stream for selected symbol
        if not hasattr(self, "ohlc_history"):
            self.ohlc_history: Dict[tuple[str, str], List[dict]] = {}
        sym = self._normalize_symbol(sym)
        interval = self._kline_interval or "1m"
        self._active_kline_symbol = sym

        key = (sym, interval)
        arr = self.ohlc_history.get(key)
        if arr:
            # Warm-start the chart from cached history.
            if hasattr(self, "_chart_page") and sym == self._active_kline_symbol and interval == self._kline_interval:
                kline_data = [
                    {
                        "timestamp": k["t"],
                        "open": k["o"],
                        "high": k["h"],
                        "low": k["l"],
                        "close": k["c"],
                        "volume": k.get("q", 0.0),
                    }
                    for k in arr
                ]
                try:
                    self._chart_page.update_data(kline_data)
                except Exception:
                    pass
        else:
            # Ensure the key exists so WS updates can append/replace immediately.
            self.ohlc_history[key] = []

        # Backfill recent candles asynchronously (avoids "timeframe does nothing" / empty chart on first select).
        try:
            limit = self._choose_kline_limit(self._kline_window, interval, max_limit=500)
            self.requestKlines.emit(sym, interval, limit)
        except Exception:
            pass

        self._kws.start(sym, interval)

    @Slot(str, str, list)
    def _on_klines_ready(self, symbol: str, interval: str, data: list) -> None:
        sym = self._normalize_symbol(symbol)
        if not hasattr(self, "ohlc_history"):
            self.ohlc_history = {}
        key = (sym, interval)

        # Normalize/merge/trim to keep memory bounded and match WS format.
        merged_by_t: Dict[int, dict] = {}
        existing = self.ohlc_history.get(key) or []
        for d in existing:
            if not isinstance(d, dict):
                continue
            try:
                t = int(d.get("t", 0))
            except Exception:
                continue
            if t > 0:
                merged_by_t[t] = d

        for d in data or []:
            if not isinstance(d, dict):
                continue
            try:
                t = int(d.get("t", 0))
            except Exception:
                continue
            if t <= 0:
                continue
            merged_by_t[t] = d

        arr = [merged_by_t[t] for t in sorted(merged_by_t.keys())]
        keep = self._choose_kline_limit(self._kline_window, interval, max_limit=500)
        if len(arr) > keep:
            arr = arr[-keep:]
        self.ohlc_history[key] = arr

        if not hasattr(self, "_chart_page"):
            return
        if sym != self._active_kline_symbol or interval != self._kline_interval:
            return

        kline_data = [
            {
                "timestamp": k["t"],
                "open": k["o"],
                "high": k["h"],
                "low": k["l"],
                "close": k["c"],
                "volume": k.get("q", 0.0),
            }
            for k in arr
        ]
        try:
            self._chart_page.update_data(kline_data)
        except Exception:
            pass

    @Slot(str)
    def _on_kline_error(self, msg: str) -> None:
        # Do not participate in REST failover logic; this is an optional backfill.
        self.statusBar().showMessage(f"Kline backfill error: {msg}", 5000)
    @Slot(dict)
    def _on_kline(self, d: dict) -> None:
        """Handle kline data from WebSocket."""
        sym = d.get("symbol", "")
        interval = d.get("i") or self._kline_interval
        if sym and not self._active_kline_symbol:
            self._active_kline_symbol = sym
        if not hasattr(self, "ohlc_history"):
            self.ohlc_history: Dict[tuple[str, str], List[dict]] = {}
        
        key = (sym, interval)
        arr = self.ohlc_history.get(key)
        if arr is None:
            arr = []
            self.ohlc_history[key] = arr
        
        # Maintain up to 120 candles
        if arr and arr[-1].get("t") == d["t"]:
            arr[-1] = d
        else:
            arr.append(d)
            keep = self._choose_kline_limit(self._kline_window, interval, max_limit=500)
            if len(arr) > keep:
                del arr[0: len(arr) - keep]
        
        # Update chart analysis page with kline data
        if hasattr(self, '_chart_page') and sym == self._active_kline_symbol and interval == self._kline_interval:
            kline_data = [
                {
                    "timestamp": k["t"],
                    "open": k["o"],
                    "high": k["h"],
                    "low": k["l"],
                    "close": k["c"],
                    "volume": k.get("q", 0.0),
                }
                for k in arr
            ]
            self._chart_page.update_data(kline_data)
    # ----- Theme -----
    def _apply_theme(self, mode: str = "dark") -> None:
        self.theme_mode = mode
        # Build and apply global stylesheet via theme module
        style = theme.build_stylesheet(mode, self.accent_color)
        self.setStyleSheet(style)
        
        # Update page accent colors
        if hasattr(self, '_market_page'):
            self._market_page.set_accent_color(self.accent_color)
        if hasattr(self, '_chart_page'):
            self._chart_page.set_accent_color(self.accent_color)
    # ----- Responsive Layout -----
    # Breakpoint for responsive sidebar (Requirements 7.1, 7.2)
    RESPONSIVE_BREAKPOINT = 800
    
    def resizeEvent(self, event) -> None:
        """Handle window resize for responsive layout.
        
        Implements Requirements 7.1, 7.2, 7.3, 7.4:
        - Below 800px: Collapse sidebar to icon-only mode
        - 800px or above: Sidebar may expand to show labels
        - Notify pages of width changes for responsive adjustments
        """
        super().resizeEvent(event)
        
        new_width = event.size().width()
        
        # Toggle sidebar collapsed state based on window width
        if hasattr(self, '_nav_sidebar'):
            should_collapse = new_width < self.RESPONSIVE_BREAKPOINT
            self._nav_sidebar.set_collapsed(should_collapse)
        
        # Notify page container of width change for page-level responsive adjustments
        if hasattr(self, '_page_container'):
            # Calculate available width for pages (total width minus sidebar)
            sidebar_width = self._nav_sidebar.get_width() if hasattr(self, '_nav_sidebar') else 60
            page_width = new_width - sidebar_width
            self._page_container.notify_width_changed(page_width)
    
    # ----- Lifecycle -----
    def _shutdown(self) -> None:
        if getattr(self, "_shutdown_started", False):
            return
        self._shutdown_started = True

        self._save_portfolio()

        try:
            self._timer.stop()
        except Exception:
            pass

        try:
            self._thread.quit()
            self._thread.wait(2000)
        except Exception:
            pass

        try:
            self._provider._client.close()
        except Exception:
            pass

        try:
            self._ws.stop()
        except Exception:
            pass

    def _on_about_to_quit(self) -> None:
        self._shutdown()

    def closeEvent(self, event):  # type: ignore[override]
        if self._minimize_to_tray and QSystemTrayIcon.isSystemTrayAvailable():
            event.ignore()
            self.hide()
            if self._tray_first_hide:
                self.tray.showMessage("Crypto Ticker", "Still running in system tray", QSystemTrayIcon.Information, 4000)
                self._tray_first_hide = False
            return

        self._shutdown()
        return super().closeEvent(event)
def main() -> int:
    # Fix potential invalid SSL env vars and prefer OS trust store
    try:
        fix_ssl_env()
    except Exception:
        pass
    app = QApplication(sys.argv)
    w = MainWindow()
    app.aboutToQuit.connect(w._on_about_to_quit)
    w.show()
    return app.exec()
if __name__ == "__main__":
    raise SystemExit(main())







