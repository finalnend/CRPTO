"""Chart Analysis Page.

Full-page chart analysis interface with toolbar controls.
"""

from __future__ import annotations

from collections import deque
from datetime import datetime
from typing import Dict, List, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QPen, QBrush, QLinearGradient, QPainter
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QToolBar,
    QComboBox,
    QPushButton,
    QLabel,
    QFrame,
)
from PySide6.QtCharts import (
    QChart,
    QChartView,
    QLineSeries,
    QAreaSeries,
    QCandlestickSeries,
    QCandlestickSet,
    QValueAxis,
    QDateTimeAxis,
    QBarCategoryAxis,
)


class ChartAnalysisPage(QWidget):
    """Full-page chart analysis interface.
    
    Displays a full-width chart with toolbar controls for timeframe
    and symbol selection.
    
    Signals:
        symbolChanged: Emitted when the symbol is changed
        timeframeChanged: Emitted when the timeframe is changed
    """
    
    symbolChanged = Signal(str)
    timeframeChanged = Signal(str)
    
    TIMEFRAMES = ["1m", "5m", "15m", "1h", "4h", "1d"]
    
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        
        self._current_symbol: str = ""
        self._current_timeframe: str = "1m"
        self._symbols: List[str] = []
        self._price_history: Dict[str, deque] = {}
        self._kline_data: List[dict] = []
        self._accent_color = QColor("#0A84FF")
        self._chart_mode = "line"  # "line" or "candle"
        
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        """Set up the page UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Toolbar
        toolbar = self._create_toolbar()
        layout.addWidget(toolbar)
        
        # Chart container
        chart_container = QFrame()
        chart_container.setStyleSheet("QFrame { background-color: transparent; }")
        chart_layout = QVBoxLayout(chart_container)
        chart_layout.setContentsMargins(8, 8, 8, 8)
        
        # Main chart
        self._chart = QChart()
        self._chart.setBackgroundVisible(False)
        self._chart.legend().hide()
        self._chart.setTitle("Select a symbol to view chart")
        
        # Line series
        self._series_main = QLineSeries()
        self._series_ma_fast = QLineSeries()  # 7-period MA
        self._series_ma_slow = QLineSeries()  # 25-period MA
        
        # Area fill under main series
        self._area_fill = QAreaSeries(self._series_main)
        
        # Candlestick series
        self._candle_series = QCandlestickSeries()
        self._candle_series.setIncreasingColor(QColor("#30D158"))
        self._candle_series.setDecreasingColor(QColor("#FF453A"))
        
        # Add series to chart
        self._chart.addSeries(self._area_fill)
        self._chart.addSeries(self._series_main)
        self._chart.addSeries(self._series_ma_fast)
        self._chart.addSeries(self._series_ma_slow)
        self._chart.addSeries(self._candle_series)
        
        # Hide candle series by default
        self._candle_series.setVisible(False)
        
        # Axes
        self._axis_x = QDateTimeAxis()
        self._axis_x.setFormat("HH:mm")
        self._axis_x.setTitleText("Time")
        self._chart.addAxis(self._axis_x, Qt.AlignBottom)
        
        self._axis_y = QValueAxis()
        self._axis_y.setTitleText("Price")
        self._chart.addAxis(self._axis_y, Qt.AlignLeft)
        
        # Attach axes to series
        for series in [self._series_main, self._series_ma_fast, self._series_ma_slow, self._area_fill]:
            series.attachAxis(self._axis_x)
            series.attachAxis(self._axis_y)
        
        self._candle_series.attachAxis(self._axis_x)
        self._candle_series.attachAxis(self._axis_y)
        
        # Chart view
        self._chart_view = QChartView(self._chart)
        self._chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        chart_layout.addWidget(self._chart_view)
        
        layout.addWidget(chart_container, 1)
        
        # Apply initial styling
        self._apply_chart_style()
    
    def _create_toolbar(self) -> QToolBar:
        """Create the chart toolbar."""
        toolbar = QToolBar()
        toolbar.setMovable(False)
        toolbar.setStyleSheet("""
            QToolBar {
                background-color: rgba(30, 30, 30, 0.9);
                border-bottom: 1px solid #3a3a3a;
                padding: 8px;
                spacing: 12px;
            }
        """)
        
        # Symbol selector
        toolbar.addWidget(QLabel("Symbol:"))
        self._symbol_combo = QComboBox()
        self._symbol_combo.setMinimumWidth(120)
        self._symbol_combo.currentTextChanged.connect(self._on_symbol_changed)
        toolbar.addWidget(self._symbol_combo)
        
        toolbar.addSeparator()
        
        # Timeframe selector
        toolbar.addWidget(QLabel("Timeframe:"))
        self._timeframe_combo = QComboBox()
        self._timeframe_combo.addItems(self.TIMEFRAMES)
        self._timeframe_combo.setCurrentText(self._current_timeframe)
        self._timeframe_combo.currentTextChanged.connect(self._on_timeframe_changed)
        toolbar.addWidget(self._timeframe_combo)
        
        toolbar.addSeparator()
        
        # Chart type selector
        toolbar.addWidget(QLabel("Type:"))
        self._chart_type_combo = QComboBox()
        self._chart_type_combo.addItems(["Line", "Candle"])
        self._chart_type_combo.currentTextChanged.connect(self._on_chart_type_changed)
        toolbar.addWidget(self._chart_type_combo)
        
        toolbar.addSeparator()
        
        # Reset zoom button
        reset_btn = QPushButton("Reset Zoom")
        reset_btn.clicked.connect(self._reset_zoom)
        toolbar.addWidget(reset_btn)
        
        # Spacer
        spacer = QWidget()
        spacer.setSizePolicy(spacer.sizePolicy().horizontalPolicy(), spacer.sizePolicy().verticalPolicy())
        toolbar.addWidget(spacer)
        
        return toolbar
    
    def _apply_chart_style(self) -> None:
        """Apply styling to the chart."""
        # Main series pen
        main_pen = QPen(self._accent_color)
        main_pen.setWidth(2)
        self._series_main.setPen(main_pen)
        
        # MA pens
        fast_pen = QPen(QColor(self._accent_color.red(), self._accent_color.green(), 
                               self._accent_color.blue(), 180))
        fast_pen.setWidth(1)
        self._series_ma_fast.setPen(fast_pen)
        
        slow_pen = QPen(QColor(self._accent_color.red(), self._accent_color.green(),
                               self._accent_color.blue(), 110))
        slow_pen.setWidth(1)
        self._series_ma_slow.setPen(slow_pen)
        
        # Area fill gradient
        grad = QLinearGradient(0, 0, 0, 1)
        grad.setCoordinateMode(QLinearGradient.ObjectBoundingMode)
        col_top = QColor(self._accent_color.red(), self._accent_color.green(),
                        self._accent_color.blue(), 90)
        col_bot = QColor(self._accent_color.red(), self._accent_color.green(),
                        self._accent_color.blue(), 10)
        grad.setColorAt(0.0, col_top)
        grad.setColorAt(1.0, col_bot)
        self._area_fill.setBrush(QBrush(grad))
        self._area_fill.setPen(Qt.NoPen)
        
        # Axis styling
        text_col = QColor("#E6E6E6")
        grid_col = QColor("#2a2a2a")
        grid_pen = QPen(grid_col)
        grid_pen.setWidth(1)
        
        self._axis_x.setLabelsBrush(text_col)
        self._axis_y.setLabelsBrush(text_col)
        self._axis_x.setGridLinePen(grid_pen)
        self._axis_y.setGridLinePen(grid_pen)
        self._chart.setTitleBrush(text_col)
    
    def _on_symbol_changed(self, symbol: str) -> None:
        """Handle symbol selection change."""
        if symbol and symbol != self._current_symbol:
            self._current_symbol = symbol
            self._update_chart()
            self.symbolChanged.emit(symbol)
    
    def _on_timeframe_changed(self, timeframe: str) -> None:
        """Handle timeframe selection change."""
        if timeframe != self._current_timeframe:
            self._current_timeframe = timeframe
            self._update_chart()
            self.timeframeChanged.emit(timeframe)
    
    def _on_chart_type_changed(self, chart_type: str) -> None:
        """Handle chart type change."""
        is_candle = chart_type == "Candle"
        self._chart_mode = "candle" if is_candle else "line"
        
        # Toggle series visibility
        self._candle_series.setVisible(is_candle)
        self._series_main.setVisible(not is_candle)
        self._series_ma_fast.setVisible(not is_candle)
        self._series_ma_slow.setVisible(not is_candle)
        self._area_fill.setVisible(not is_candle)
        
        self._update_chart()
    
    def _reset_zoom(self) -> None:
        """Reset chart zoom."""
        self._chart.zoomReset()
        self._update_chart()
    
    def set_symbols(self, symbols: List[str]) -> None:
        """Set the available symbols.
        
        Args:
            symbols: List of trading pair symbols
        """
        self._symbols = symbols
        current = self._symbol_combo.currentText()
        
        self._symbol_combo.blockSignals(True)
        self._symbol_combo.clear()
        self._symbol_combo.addItems(symbols)
        
        # Restore selection if possible
        if current in symbols:
            self._symbol_combo.setCurrentText(current)
        elif symbols:
            self._symbol_combo.setCurrentText(symbols[0])
        
        self._symbol_combo.blockSignals(False)
        
        # Trigger update if selection changed
        new_current = self._symbol_combo.currentText()
        if new_current != self._current_symbol:
            self._on_symbol_changed(new_current)
    
    def set_symbol(self, symbol: str) -> None:
        """Set the chart symbol.
        
        Args:
            symbol: Trading pair symbol
        """
        if symbol in self._symbols or not self._symbols:
            self._symbol_combo.setCurrentText(symbol)
    
    def set_timeframe(self, timeframe: str) -> None:
        """Set the chart timeframe.
        
        Args:
            timeframe: Timeframe string (e.g., "1m", "5m", "1h")
        """
        if timeframe in self.TIMEFRAMES:
            self._timeframe_combo.setCurrentText(timeframe)
    
    def update_data(self, data: List[dict]) -> None:
        """Update chart data.
        
        Args:
            data: List of OHLCV data dictionaries with keys:
                  timestamp, open, high, low, close, volume
        """
        self._kline_data = data
        self._update_chart()
    
    def add_price_point(self, symbol: str, timestamp_ms: float, price: float) -> None:
        """Add a price point to the history.
        
        Args:
            symbol: Trading pair symbol
            timestamp_ms: Timestamp in milliseconds
            price: Price value
        """
        if symbol not in self._price_history:
            self._price_history[symbol] = deque(maxlen=500)
        
        self._price_history[symbol].append((timestamp_ms, price))
        
        if symbol == self._current_symbol:
            self._update_chart()
    
    def _update_chart(self) -> None:
        """Update the chart display."""
        if not self._current_symbol:
            return
        
        self._chart.setTitle(f"{self._current_symbol} - {self._current_timeframe}")
        
        if self._chart_mode == "candle" and self._kline_data:
            self._update_candle_chart()
        else:
            self._update_line_chart()
    
    def _update_line_chart(self) -> None:
        """Update the line chart with price history."""
        history = self._price_history.get(self._current_symbol, deque())
        
        self._series_main.clear()
        self._series_ma_fast.clear()
        self._series_ma_slow.clear()
        
        if not history:
            return
        
        prices = []
        min_price = float('inf')
        max_price = float('-inf')
        min_time = float('inf')
        max_time = float('-inf')
        
        for ms, price in history:
            self._series_main.append(ms, price)
            prices.append(price)
            min_price = min(min_price, price)
            max_price = max(max_price, price)
            min_time = min(min_time, ms)
            max_time = max(max_time, ms)
        
        # Calculate moving averages
        if len(prices) >= 7:
            for i in range(6, len(prices)):
                ma7 = sum(prices[i-6:i+1]) / 7
                ms = list(history)[i][0]
                self._series_ma_fast.append(ms, ma7)
        
        if len(prices) >= 25:
            for i in range(24, len(prices)):
                ma25 = sum(prices[i-24:i+1]) / 25
                ms = list(history)[i][0]
                self._series_ma_slow.append(ms, ma25)
        
        # Update axes
        if min_price != float('inf'):
            margin = (max_price - min_price) * 0.1 or 1.0
            self._axis_y.setRange(min_price - margin, max_price + margin)
            self._axis_x.setRange(
                datetime.fromtimestamp(min_time / 1000),
                datetime.fromtimestamp(max_time / 1000)
            )
    
    def _update_candle_chart(self) -> None:
        """Update the candlestick chart."""
        self._candle_series.clear()
        
        if not self._kline_data:
            return
        
        min_price = float('inf')
        max_price = float('-inf')
        min_time = float('inf')
        max_time = float('-inf')
        
        for kline in self._kline_data:
            ts = kline.get("timestamp", 0)
            o = kline.get("open", 0)
            h = kline.get("high", 0)
            l = kline.get("low", 0)
            c = kline.get("close", 0)
            
            candle = QCandlestickSet(o, h, l, c, ts)
            self._candle_series.append(candle)
            
            min_price = min(min_price, l)
            max_price = max(max_price, h)
            min_time = min(min_time, ts)
            max_time = max(max_time, ts)
        
        # Update axes
        if min_price != float('inf'):
            margin = (max_price - min_price) * 0.1 or 1.0
            self._axis_y.setRange(min_price - margin, max_price + margin)
            self._axis_x.setRange(
                datetime.fromtimestamp(min_time / 1000),
                datetime.fromtimestamp(max_time / 1000)
            )
    
    def set_accent_color(self, color: QColor) -> None:
        """Set the accent color for the chart.
        
        Args:
            color: The accent color to use
        """
        self._accent_color = color
        self._apply_chart_style()
    
    def on_container_width_changed(self, width: int) -> None:
        """Handle container width changes for responsive layout.
        
        Implements Requirements 7.3, 7.4: Adjust layout based on available width.
        
        Args:
            width: The new available width in pixels
        """
        # Adjust toolbar layout based on width
        # In narrow mode, hide some labels to save space
        narrow_mode = width < 600
        
        # Adjust axis format based on width
        if narrow_mode:
            self._axis_x.setFormat("HH:mm")
            self._axis_x.setTitleVisible(False)
            self._axis_y.setTitleVisible(False)
        else:
            self._axis_x.setFormat("HH:mm:ss")
            self._axis_x.setTitleVisible(True)
            self._axis_y.setTitleVisible(True)
