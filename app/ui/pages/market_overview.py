
from __future__ import annotations

from collections import deque
from datetime import datetime
from typing import Dict, List, Optional

from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QFrame,
)
from PySide6.QtCharts import (
    QChart,
    QChartView,
    QLineSeries,
    QValueAxis,
    QDateTimeAxis,
)

from app.widgets.sparkline import SparklineWidget


class NumericTableItem(QTableWidgetItem):
    """Table item that sorts numerically."""
    
    def __init__(self, text: str = "", value: float = 0.0):
        super().__init__(text)
        self.value = value
        self.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
    
    def __lt__(self, other):
        if isinstance(other, NumericTableItem):
            return self.value < other.value
        try:
            return float(self.text().replace(",", "")) < float(other.text().replace(",", ""))
        except Exception:
            return super().__lt__(other)


class MarketOverviewPage(QWidget):
    """Market overview page with price table and chart.
    
    Displays a table of cryptocurrency prices with a resizable chart panel.
    
    Signals:
        symbolSelected: Emitted when a symbol is selected in the table
    """
    
    symbolSelected = Signal(str)
    
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        
        self._symbols: List[str] = []
        self._price_history: Dict[str, deque] = {}
        self._selected_symbol: Optional[str] = None
        self._accent_color = QColor("#0A84FF")
        
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        """Set up the page UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Create splitter for table and chart
        self._splitter = QSplitter(Qt.Vertical, self)
        
        # Price table
        self._table = QTableWidget()
        self._table.setColumnCount(10)
        self._table.setHorizontalHeaderLabels([
            "Symbol", "Last", "Bid", "Ask", "24h %", 
            "24h High", "24h Low", "24h Vol", "Turnover", "Time"
        ])
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectRows)
        self._table.setAlternatingRowColors(True)
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._table.setSortingEnabled(True)
        self._table.itemSelectionChanged.connect(self._on_selection_changed)
        
        self._splitter.addWidget(self._table)
        
        # Chart panel
        self._chart_frame = QFrame()
        chart_layout = QVBoxLayout(self._chart_frame)
        chart_layout.setContentsMargins(8, 8, 8, 8)
        
        self._chart = QChart()
        self._chart.setBackgroundVisible(False)
        self._chart.legend().hide()
        self._chart.setTitle("Price Chart")
        
        self._series = QLineSeries()
        self._chart.addSeries(self._series)
        
        # Axes
        self._axis_x = QDateTimeAxis()
        self._axis_x.setFormat("HH:mm:ss")
        self._axis_x.setTitleText("Time")
        self._chart.addAxis(self._axis_x, Qt.AlignBottom)
        self._series.attachAxis(self._axis_x)
        
        self._axis_y = QValueAxis()
        self._axis_y.setTitleText("Price")
        self._chart.addAxis(self._axis_y, Qt.AlignLeft)
        self._series.attachAxis(self._axis_y)
        
        self._chart_view = QChartView(self._chart)
        self._chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        chart_layout.addWidget(self._chart_view)
        
        self._splitter.addWidget(self._chart_frame)
        
        # Set initial splitter sizes (70% table, 30% chart)
        self._splitter.setSizes([700, 300])
        
        layout.addWidget(self._splitter)
    
    def set_symbols(self, symbols: List[str]) -> None:
        """Set the list of symbols to display.
        
        Args:
            symbols: List of trading pair symbols
        """
        self._symbols = symbols

        # Drop cached history for removed symbols (widgets are owned by the table and
        # can be deleted when the table is rebuilt/sorted).
        keep = {s.upper() for s in symbols}
        self._price_history = {k: v for k, v in self._price_history.items() if k.upper() in keep}
        if self._selected_symbol and self._selected_symbol.upper() not in keep:
            self._selected_symbol = None
        self._sync_table_rows()
    
    def _sync_table_rows(self) -> None:
        """Synchronize table rows with symbols list."""
        self._table.setRowCount(len(self._symbols))
        
        for row, sym in enumerate(self._symbols):
            self._table.setItem(row, 0, QTableWidgetItem(sym))
            for col in range(1, 9):
                self._table.setItem(row, col, NumericTableItem("-", 0.0))
            self._table.setItem(row, 9, QTableWidgetItem("-"))
            
            # Sparkline widget
            sp = SparklineWidget(color=self._accent_color, left_padding=64)
            self._table.setCellWidget(row, 0, sp)
            
            # Initialize price history
            if sym not in self._price_history:
                self._price_history[sym] = deque(maxlen=100)
    
    def _row_for_symbol(self, sym: str) -> int:
        """Find the row index for a symbol."""
        for row in range(self._table.rowCount()):
            item = self._table.item(row, 0)
            if item and item.text().upper() == sym.upper():
                return row
        return -1
    
    def set_price_data(self, data: Dict) -> None:
        """Update price data in the table.
        
        Args:
            data: Dictionary mapping symbols to price data
        """
        for sym, d in data.items():
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
            ts = self._fmt_time(d.get("ts"))
            
            # Update table items
            self._set_numeric(row, 1, self._fmt_price(last), last)
            self._set_numeric(row, 2, self._fmt_price(bid), bid)
            self._set_numeric(row, 3, self._fmt_price(ask), ask)
            self._set_numeric(row, 4, f"{chg:.2f}%", chg)
            self._set_numeric(row, 5, self._fmt_price(high), high)
            self._set_numeric(row, 6, self._fmt_price(low), low)
            self._set_numeric(row, 7, self._fmt_volume(vol), vol)
            self._set_numeric(row, 8, self._fmt_volume(qvol), qvol)
            self._table.item(row, 9).setText(str(ts))
            
            # Color for change
            color = Qt.green if chg >= 0 else Qt.red
            self._table.item(row, 1).setForeground(color)
            self._table.item(row, 4).setForeground(color)
            
            # Update price history
            now_ms = datetime.now().timestamp() * 1000
            self._price_history.setdefault(sym, deque(maxlen=100)).append((now_ms, last))
            
            # Update sparkline
            sp = self._table.cellWidget(row, 0)
            if isinstance(sp, SparklineWidget):
                try:
                    hist = list(self._price_history.get(sym, []))[-50:]
                    sp.update_data([v for _, v in hist], color=self._accent_color)
                except RuntimeError:
                    pass
            
            # Update chart if this symbol is selected
            if sym == self._selected_symbol:
                self._update_chart(sym)
    
    def _set_numeric(self, row: int, col: int, text: str, value: float) -> None:
        """Set a numeric table item with flash animation."""
        item = self._table.item(row, col)
        if not isinstance(item, NumericTableItem):
            item = NumericTableItem(text, value)
            self._table.setItem(row, col, item)
        else:
            old_value = item.value
            item.setText(text)
            item.value = value
            
            # Flash on price change
            if old_value != value and col in (1, 2, 3):
                flash_color = QColor(0, 200, 0, 80) if value > old_value else QColor(200, 0, 0, 80)
                self._flash_cell(item, flash_color)
    
    def _flash_cell(self, item: QTableWidgetItem, color: QColor, duration_ms: int = 200) -> None:
        """Flash a table cell background color briefly."""
        original_bg = item.background()
        try:
            item.setBackground(color)
        except RuntimeError:
            return

        def _restore() -> None:
            try:
                item.setBackground(original_bg)
            except RuntimeError:
                pass

        QTimer.singleShot(duration_ms, self, _restore)
    
    def _fmt_price(self, v: float) -> str:
        """Format a price value."""
        if v >= 100:
            return f"{v:,.2f}"
        if v >= 1:
            return f"{v:,.4f}"
        return f"{v:.8f}".rstrip("0").rstrip(".")
    
    def _fmt_volume(self, v: float) -> str:
        """Format a volume value."""
        units = ["", "K", "M", "B"]
        i = 0
        while v >= 1000 and i < len(units) - 1:
            v /= 1000.0
            i += 1
        return f"{v:.2f}{units[i]}"

    def _fmt_time(self, ts) -> str:
        """Format UNIX timestamp or ISO time to 24-hour time string."""
        now_str = datetime.now().strftime("%H:%M:%S")
        if ts is None:
            return now_str

        if isinstance(ts, (int, float)):
            # Heuristic: milliseconds are ~1e12, seconds are ~1e9.
            seconds = ts / 1000.0 if ts >= 10_000_000_000 else float(ts)
            try:
                return datetime.fromtimestamp(seconds).strftime("%H:%M:%S")
            except Exception:
                return now_str

        if isinstance(ts, str):
            s = ts.strip()
            if not s:
                return now_str
            if s.isdigit():
                try:
                    v = int(s)
                    seconds = v / 1000.0 if v >= 10_000_000_000 else float(v)
                    return datetime.fromtimestamp(seconds).strftime("%H:%M:%S")
                except Exception:
                    return now_str
            if "T" in s:
                try:
                    dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
                    if getattr(dt, "tzinfo", None) is not None:
                        dt = dt.astimezone()
                    return dt.strftime("%H:%M:%S")
                except Exception:
                    return now_str
            return s

        return now_str
    
    def _on_selection_changed(self) -> None:
        """Handle table selection change."""
        rows = self._table.selectionModel().selectedRows()
        if rows:
            row = rows[0].row()
            item = self._table.item(row, 0)
            if item:
                sym = item.text()
                self._selected_symbol = sym
                self._update_chart(sym)
                self.symbolSelected.emit(sym)
    
    def _update_chart(self, symbol: str) -> None:
        """Update the chart with data for the given symbol."""
        self._chart.setTitle(f"{symbol} Price")
        
        history = self._price_history.get(symbol, deque())
        if not history:
            return
        
        self._series.clear()
        
        min_price = float('inf')
        max_price = float('-inf')
        min_time = float('inf')
        max_time = float('-inf')
        
        for ms, price in history:
            self._series.append(ms, price)
            min_price = min(min_price, price)
            max_price = max(max_price, price)
            min_time = min(min_time, ms)
            max_time = max(max_time, ms)
        
        if min_price != float('inf'):
            margin = (max_price - min_price) * 0.1 or 1.0
            self._axis_y.setRange(min_price - margin, max_price + margin)
            self._axis_x.setRange(
                datetime.fromtimestamp(min_time / 1000),
                datetime.fromtimestamp(max_time / 1000)
            )
    
    def get_selected_symbol(self) -> Optional[str]:
        """Get the currently selected symbol.
        
        Returns:
            The selected symbol, or None if nothing is selected
        """
        return self._selected_symbol
    
    def set_accent_color(self, color: QColor) -> None:
        """Set the accent color for sparklines and chart.
        
        Args:
            color: The accent color to use
        """
        self._accent_color = color
        for row in range(self._table.rowCount()):
            sp = self._table.cellWidget(row, 0)
            if isinstance(sp, SparklineWidget):
                try:
                    sp.update_color(color)
                except RuntimeError:
                    pass
    
    def on_container_width_changed(self, width: int) -> None:
        """Handle container width changes for responsive layout.
        
        
        Args:
            width: The new available width in pixels
        """
        # Adjust splitter orientation based on width
        # Below 600px: Stack vertically (chart below table)
        # 600px and above: Side by side or vertical based on preference
        if width < 600:
            self._splitter.setOrientation(Qt.Vertical)
            # Give more space to table in narrow mode
            self._splitter.setSizes([600, 200])
        else:
            self._splitter.setOrientation(Qt.Vertical)
            # Standard 70/30 split
            self._splitter.setSizes([700, 300])
        
        # Hide less important columns in narrow mode
        narrow_mode = width < 800
        # Hide Bid, Ask, High, Low, Turnover columns in narrow mode
        self._table.setColumnHidden(2, narrow_mode)  # Bid
        self._table.setColumnHidden(3, narrow_mode)  # Ask
        self._table.setColumnHidden(5, narrow_mode)  # 24h High
        self._table.setColumnHidden(6, narrow_mode)  # 24h Low
        self._table.setColumnHidden(8, narrow_mode)  # Turnover
