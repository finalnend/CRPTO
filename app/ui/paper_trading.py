"""Paper Trading UI Panel Module.

Provides UI components for paper trading functionality including:
- Order entry form (symbol, quantity, buy/sell buttons)
- Balance and connection status display
- Portfolio view with positions
- Trade history view with performance metrics
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Optional, Callable, Dict, List

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QGroupBox,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QFileDialog,
    QMessageBox,
    QFrame,
)

from app.trading.portfolio import IPortfolioManager, PortfolioManager
from app.trading.orders import IOrderService, OrderService, OrderStatus, IDataProvider
from app.trading.analytics import PerformanceAnalytics, PerformanceMetrics
from app.trading.models import Transaction, Position


class PaperTradingPanel(QWidget):
    """Main paper trading panel widget.
    
    Contains order entry form, balance display, and connection status.
    Emits signals when orders are submitted.
    
    Signals:
        orderSubmitted: Emitted when an order is successfully submitted
        balanceChanged: Emitted when balance changes after order execution
    """
    
    orderSubmitted = Signal(str, str, object, object)  # symbol, order_type, quantity, price
    balanceChanged = Signal(object)  # new balance as Decimal
    
    def __init__(
        self,
        portfolio: IPortfolioManager,
        order_service: IOrderService,
        data_provider: IDataProvider,
        parent: Optional[QWidget] = None,
    ) -> None:
        """Initialize the paper trading panel.
        
        Args:
            portfolio: Portfolio manager for balance/holdings
            order_service: Order service for submitting orders
            data_provider: Data provider for connection status and prices
            parent: Parent widget
        """
        super().__init__(parent)
        
        self._portfolio = portfolio
        self._order_service = order_service
        self._data_provider = data_provider
        
        self._setup_ui()
        self._update_balance_display()
        self._update_connection_status()

    def _setup_ui(self) -> None:
        """Set up the UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # Connection warning banner (hidden by default)
        # Implements Requirements 7.3: Display warning when data connection lost
        self._warning_banner = QFrame()
        self._warning_banner.setStyleSheet(
            "QFrame { background-color: #FFC107; border-radius: 4px; padding: 8px; }"
        )
        warning_layout = QHBoxLayout(self._warning_banner)
        warning_layout.setContentsMargins(8, 4, 8, 4)
        self._warning_icon = QLabel("⚠")
        self._warning_icon.setStyleSheet("font-size: 16px;")
        warning_layout.addWidget(self._warning_icon)
        self._warning_text = QLabel("Data connection lost - Order submission paused until reconnected")
        self._warning_text.setStyleSheet("color: #000; font-weight: bold;")
        warning_layout.addWidget(self._warning_text)
        warning_layout.addStretch()
        self._warning_banner.hide()
        layout.addWidget(self._warning_banner)
        
        # Status section
        self._status_frame = QFrame()
        status_layout = QHBoxLayout(self._status_frame)
        status_layout.setContentsMargins(0, 0, 0, 0)
        
        self._balance_label = QLabel("Balance: $0.00")
        self._balance_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        status_layout.addWidget(self._balance_label)
        
        status_layout.addStretch()
        
        self._connection_indicator = QLabel("●")
        self._connection_label = QLabel("Disconnected")
        status_layout.addWidget(self._connection_indicator)
        status_layout.addWidget(self._connection_label)
        
        layout.addWidget(self._status_frame)
        
        # Order entry group
        order_group = QGroupBox("Place Order")
        order_layout = QVBoxLayout(order_group)
        
        # Symbol input
        symbol_layout = QHBoxLayout()
        symbol_layout.addWidget(QLabel("Symbol:"))
        self._symbol_input = QLineEdit()
        self._symbol_input.setPlaceholderText("e.g., BTCUSDT")
        self._symbol_input.textChanged.connect(self._on_symbol_changed)
        symbol_layout.addWidget(self._symbol_input)
        order_layout.addLayout(symbol_layout)
        
        # Current price display
        price_layout = QHBoxLayout()
        price_layout.addWidget(QLabel("Current Price:"))
        self._price_label = QLabel("--")
        self._price_label.setStyleSheet("font-weight: bold;")
        price_layout.addWidget(self._price_label)
        price_layout.addStretch()
        order_layout.addLayout(price_layout)
        
        # Quantity input
        qty_layout = QHBoxLayout()
        qty_layout.addWidget(QLabel("Quantity:"))
        self._quantity_input = QLineEdit()
        self._quantity_input.setPlaceholderText("0.00")
        self._quantity_input.textChanged.connect(self._on_quantity_changed)
        qty_layout.addWidget(self._quantity_input)
        order_layout.addLayout(qty_layout)
        
        # Order value display
        value_layout = QHBoxLayout()
        value_layout.addWidget(QLabel("Order Value:"))
        self._order_value_label = QLabel("$0.00")
        value_layout.addWidget(self._order_value_label)
        value_layout.addStretch()
        order_layout.addLayout(value_layout)
        
        # Buy/Sell buttons
        buttons_layout = QHBoxLayout()
        self._buy_button = QPushButton("BUY")
        self._buy_button.setStyleSheet(
            "QPushButton { background-color: #28A745; color: white; font-weight: bold; padding: 10px; }"
            "QPushButton:hover { background-color: #218838; }"
            "QPushButton:disabled { background-color: #6c757d; }"
        )
        self._buy_button.clicked.connect(self._on_buy_clicked)
        
        self._sell_button = QPushButton("SELL")
        self._sell_button.setStyleSheet(
            "QPushButton { background-color: #DC3545; color: white; font-weight: bold; padding: 10px; }"
            "QPushButton:hover { background-color: #C82333; }"
            "QPushButton:disabled { background-color: #6c757d; }"
        )
        self._sell_button.clicked.connect(self._on_sell_clicked)
        
        buttons_layout.addWidget(self._buy_button)
        buttons_layout.addWidget(self._sell_button)
        order_layout.addLayout(buttons_layout)
        
        # Status message
        self._status_message = QLabel("")
        self._status_message.setWordWrap(True)
        order_layout.addWidget(self._status_message)
        
        layout.addWidget(order_group)
        layout.addStretch()
    
    def _on_symbol_changed(self, text: str) -> None:
        """Handle symbol input change."""
        symbol = text.strip().upper()
        if symbol:
            price = self._data_provider.get_current_price(symbol)
            if price is not None:
                self._price_label.setText(f"${price:,.8f}".rstrip('0').rstrip('.'))
            else:
                self._price_label.setText("--")
        else:
            self._price_label.setText("--")
        self._update_order_value()
    
    def _on_quantity_changed(self, text: str) -> None:
        """Handle quantity input change."""
        self._update_order_value()
    
    def _update_order_value(self) -> None:
        """Update the displayed order value."""
        symbol = self._symbol_input.text().strip().upper()
        qty_text = self._quantity_input.text().strip()
        
        try:
            quantity = Decimal(qty_text) if qty_text else Decimal("0")
            price = self._data_provider.get_current_price(symbol)
            if price is not None and quantity > 0:
                value = quantity * price
                self._order_value_label.setText(f"${value:,.2f}")
            else:
                self._order_value_label.setText("$0.00")
        except InvalidOperation:
            self._order_value_label.setText("$0.00")
    
    def _on_buy_clicked(self) -> None:
        """Handle buy button click."""
        self._submit_order("BUY")
    
    def _on_sell_clicked(self) -> None:
        """Handle sell button click."""
        self._submit_order("SELL")
    
    def _submit_order(self, order_type: str) -> None:
        """Submit an order.
        
        Args:
            order_type: "BUY" or "SELL"
        """
        symbol = self._symbol_input.text().strip().upper()
        qty_text = self._quantity_input.text().strip()
        
        if not symbol:
            self._show_status("Please enter a symbol", error=True)
            return
        
        try:
            quantity = Decimal(qty_text)
            if quantity <= 0:
                self._show_status("Quantity must be greater than zero", error=True)
                return
        except (InvalidOperation, ValueError):
            self._show_status("Invalid quantity", error=True)
            return
        
        # Check connection - Requirements 7.3: Pause order execution when disconnected
        if not self._data_provider.is_connected():
            self._show_status("Cannot place order: Data connection lost. Waiting for reconnection...", error=True)
            return
        
        # Submit order
        if order_type == "BUY":
            result = self._order_service.submit_buy(symbol, quantity)
        else:
            result = self._order_service.submit_sell(symbol, quantity)
        
        if result.status == OrderStatus.EXECUTED:
            self._show_status(result.message, error=False)
            self._update_balance_display()
            self.orderSubmitted.emit(
                symbol, 
                order_type, 
                quantity, 
                result.transaction.price if result.transaction else None
            )
            self.balanceChanged.emit(self._portfolio.get_balance())
            # Clear inputs
            self._quantity_input.clear()
        else:
            self._show_status(result.message, error=True)
    
    def _show_status(self, message: str, error: bool = False) -> None:
        """Show a status message.
        
        Args:
            message: Message to display
            error: If True, show as error (red text)
        """
        color = "#DC3545" if error else "#28A745"
        self._status_message.setStyleSheet(f"color: {color};")
        self._status_message.setText(message)
    
    def _update_balance_display(self) -> None:
        """Update the balance display."""
        balance = self._portfolio.get_balance()
        self._balance_label.setText(f"Balance: ${balance:,.2f}")
    
    def _update_connection_status(self) -> None:
        """Update the connection status indicator and warning banner.
        
        Implements Requirements 7.3 and 7.4:
        - 7.3: When connection lost, disable order submission and show warning
        - 7.4: When connection restored, resume normal operations
        """
        connected = self._data_provider.is_connected()
        if connected:
            # Connection restored - resume normal paper trading operations
            self._connection_indicator.setStyleSheet("color: #28A745; font-size: 16px;")
            self._connection_label.setText("Connected")
            self._connection_label.setStyleSheet("color: #28A745;")
            self._buy_button.setEnabled(True)
            self._sell_button.setEnabled(True)
            self._warning_banner.hide()
        else:
            # Connection lost - pause order execution and display warning
            self._connection_indicator.setStyleSheet("color: #DC3545; font-size: 16px;")
            self._connection_label.setText("Disconnected")
            self._connection_label.setStyleSheet("color: #DC3545;")
            self._buy_button.setEnabled(False)
            self._sell_button.setEnabled(False)
            self._warning_banner.show()
    
    def refresh(self) -> None:
        """Refresh the panel display."""
        self._update_balance_display()
        self._update_connection_status()
        self._on_symbol_changed(self._symbol_input.text())
    
    def set_symbol(self, symbol: str) -> None:
        """Set the symbol in the order entry form.
        
        Args:
            symbol: Trading pair symbol
        """
        self._symbol_input.setText(symbol)


class PortfolioView(QWidget):
    """Widget displaying portfolio positions and value.
    
    Shows a table of positions with symbol, quantity, average cost,
    current value, and unrealized PnL. Also displays total portfolio
    value and total unrealized PnL.
    """
    
    def __init__(
        self,
        portfolio: IPortfolioManager,
        data_provider: IDataProvider,
        parent: Optional[QWidget] = None,
    ) -> None:
        """Initialize the portfolio view.
        
        Args:
            portfolio: Portfolio manager for position data
            data_provider: Data provider for current prices
            parent: Parent widget
        """
        super().__init__(parent)
        
        self._portfolio = portfolio
        self._data_provider = data_provider
        
        self._setup_ui()
        self.refresh()
    
    def _setup_ui(self) -> None:
        """Set up the UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # Summary section
        summary_frame = QFrame()
        summary_layout = QHBoxLayout(summary_frame)
        summary_layout.setContentsMargins(0, 0, 0, 0)
        
        self._total_value_label = QLabel("Total Value: $0.00")
        self._total_value_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        summary_layout.addWidget(self._total_value_label)
        
        summary_layout.addStretch()
        
        self._unrealized_pnl_label = QLabel("Unrealized P&L: $0.00")
        self._unrealized_pnl_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        summary_layout.addWidget(self._unrealized_pnl_label)
        
        layout.addWidget(summary_frame)
        
        # Positions table
        self._positions_table = QTableWidget()
        self._positions_table.setColumnCount(5)
        self._positions_table.setHorizontalHeaderLabels([
            "Symbol", "Qty", "Avg Cost", "Value", "P&L"
        ])
        self._positions_table.verticalHeader().setVisible(False)
        self._positions_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._positions_table.setSelectionBehavior(QTableWidget.SelectRows)
        self._positions_table.setAlternatingRowColors(True)
        # Use ResizeToContents for most columns, stretch for last
        header = self._positions_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.Stretch)
        
        layout.addWidget(self._positions_table)
    
    def refresh(self) -> None:
        """Refresh the portfolio display with current data."""
        positions = self._portfolio.get_positions()
        prices = self._get_current_prices(list(positions.keys()))
        
        # Update positions table
        self._positions_table.setRowCount(len(positions))
        
        total_value = self._portfolio.get_balance()
        total_unrealized_pnl = Decimal("0")
        
        for row, (symbol, position) in enumerate(positions.items()):
            current_price = prices.get(symbol, position.average_cost)
            current_value = position.quantity * current_price
            unrealized_pnl = self._portfolio.get_unrealized_pnl(symbol, current_price)
            
            total_value += current_value
            total_unrealized_pnl += unrealized_pnl
            
            # Symbol
            self._positions_table.setItem(row, 0, QTableWidgetItem(symbol))
            
            # Quantity
            qty_item = QTableWidgetItem(f"{position.quantity:,.8f}".rstrip('0').rstrip('.'))
            qty_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self._positions_table.setItem(row, 1, qty_item)
            
            # Average Cost
            cost_item = QTableWidgetItem(f"${position.average_cost:,.8f}".rstrip('0').rstrip('.'))
            cost_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self._positions_table.setItem(row, 2, cost_item)
            
            # Current Value
            value_item = QTableWidgetItem(f"${current_value:,.2f}")
            value_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self._positions_table.setItem(row, 3, value_item)
            
            # P&L
            pnl_item = QTableWidgetItem(f"${unrealized_pnl:,.2f}")
            pnl_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            if unrealized_pnl > 0:
                pnl_item.setForeground(QColor("#28A745"))
            elif unrealized_pnl < 0:
                pnl_item.setForeground(QColor("#DC3545"))
            self._positions_table.setItem(row, 4, pnl_item)
        
        # Update summary
        self._total_value_label.setText(f"Total Value: ${total_value:,.2f}")
        
        pnl_color = "#28A745" if total_unrealized_pnl >= 0 else "#DC3545"
        pnl_sign = "+" if total_unrealized_pnl > 0 else ""
        self._unrealized_pnl_label.setText(f"Unrealized P&L: {pnl_sign}${total_unrealized_pnl:,.2f}")
        self._unrealized_pnl_label.setStyleSheet(f"font-weight: bold; font-size: 14px; color: {pnl_color};")
    
    def _get_current_prices(self, symbols: List[str]) -> Dict[str, Decimal]:
        """Get current prices for symbols.
        
        Args:
            symbols: List of symbols to get prices for
            
        Returns:
            Dictionary mapping symbols to prices
        """
        prices = {}
        for symbol in symbols:
            price = self._data_provider.get_current_price(symbol)
            if price is not None:
                prices[symbol] = price
        return prices


class TradeHistoryView(QWidget):
    """Widget displaying trade history and performance metrics.
    
    Shows a table of all transactions sorted by timestamp (descending),
    performance metrics (win rate, realized PnL), and export functionality.
    """
    
    def __init__(
        self,
        portfolio: IPortfolioManager,
        parent: Optional[QWidget] = None,
    ) -> None:
        """Initialize the trade history view.
        
        Args:
            portfolio: Portfolio manager for transaction history
            parent: Parent widget
        """
        super().__init__(parent)
        
        self._portfolio = portfolio
        self._analytics = PerformanceAnalytics()
        
        self._setup_ui()
        self.refresh()
    
    def _setup_ui(self) -> None:
        """Set up the UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # Performance metrics section
        metrics_group = QGroupBox("Performance Metrics")
        metrics_layout = QHBoxLayout(metrics_group)
        
        self._total_trades_label = QLabel("Total Trades: 0")
        metrics_layout.addWidget(self._total_trades_label)
        
        self._win_rate_label = QLabel("Win Rate: 0%")
        self._win_rate_label.setStyleSheet("font-weight: bold;")
        metrics_layout.addWidget(self._win_rate_label)
        
        self._realized_pnl_label = QLabel("Realized P&L: $0.00")
        self._realized_pnl_label.setStyleSheet("font-weight: bold;")
        metrics_layout.addWidget(self._realized_pnl_label)
        
        metrics_layout.addStretch()
        
        layout.addWidget(metrics_group)
        
        # Trade history table
        self._history_table = QTableWidget()
        self._history_table.setColumnCount(6)
        self._history_table.setHorizontalHeaderLabels([
            "Time", "Symbol", "Type", "Qty", "Price", "Value"
        ])
        self._history_table.verticalHeader().setVisible(False)
        self._history_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._history_table.setSelectionBehavior(QTableWidget.SelectRows)
        self._history_table.setAlternatingRowColors(True)
        # Use ResizeToContents for most columns, stretch for last
        hist_header = self._history_table.horizontalHeader()
        hist_header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        hist_header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        hist_header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        hist_header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        hist_header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        hist_header.setSectionResizeMode(5, QHeaderView.Stretch)
        
        layout.addWidget(self._history_table)
        
        # Export button
        export_layout = QHBoxLayout()
        export_layout.addStretch()
        
        self._export_button = QPushButton("Export to CSV")
        self._export_button.clicked.connect(self._on_export_clicked)
        export_layout.addWidget(self._export_button)
        
        layout.addLayout(export_layout)
    
    def refresh(self) -> None:
        """Refresh the trade history display."""
        transactions = self._portfolio.get_transactions()
        
        # Sort by timestamp descending
        sorted_transactions = self._analytics.sort_transactions_by_timestamp(
            transactions, descending=True
        )
        
        # Update table
        self._history_table.setRowCount(len(sorted_transactions))
        
        for row, txn in enumerate(sorted_transactions):
            # Time
            time_item = QTableWidgetItem(txn.timestamp.strftime("%Y-%m-%d %H:%M:%S"))
            self._history_table.setItem(row, 0, time_item)
            
            # Symbol
            self._history_table.setItem(row, 1, QTableWidgetItem(txn.symbol))
            
            # Type
            type_item = QTableWidgetItem(txn.order_type)
            if txn.order_type == "BUY":
                type_item.setForeground(QColor("#28A745"))
            else:
                type_item.setForeground(QColor("#DC3545"))
            self._history_table.setItem(row, 2, type_item)
            
            # Quantity
            qty_item = QTableWidgetItem(f"{txn.quantity:,.8f}".rstrip('0').rstrip('.'))
            qty_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self._history_table.setItem(row, 3, qty_item)
            
            # Price
            price_item = QTableWidgetItem(f"${txn.price:,.8f}".rstrip('0').rstrip('.'))
            price_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self._history_table.setItem(row, 4, price_item)
            
            # Value
            value_item = QTableWidgetItem(f"${txn.total_value:,.2f}")
            value_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self._history_table.setItem(row, 5, value_item)
        
        # Update performance metrics
        if transactions:
            metrics = self._analytics.calculate_metrics(transactions)
            self._total_trades_label.setText(f"Total Trades: {metrics.total_trades}")
            self._win_rate_label.setText(f"Win Rate: {metrics.win_rate:.1f}%")
            
            pnl_color = "#28A745" if metrics.realized_pnl >= 0 else "#DC3545"
            pnl_sign = "+" if metrics.realized_pnl > 0 else ""
            self._realized_pnl_label.setText(f"Realized P&L: {pnl_sign}${metrics.realized_pnl:,.2f}")
            self._realized_pnl_label.setStyleSheet(f"font-weight: bold; color: {pnl_color};")
        else:
            self._total_trades_label.setText("Total Trades: 0")
            self._win_rate_label.setText("Win Rate: 0%")
            self._realized_pnl_label.setText("Realized P&L: $0.00")
            self._realized_pnl_label.setStyleSheet("font-weight: bold;")
    
    def _on_export_clicked(self) -> None:
        """Handle export button click."""
        transactions = self._portfolio.get_transactions()
        
        if not transactions:
            QMessageBox.information(
                self,
                "Export",
                "No transactions to export."
            )
            return
        
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Export Trade History",
            "trade_history.csv",
            "CSV Files (*.csv)"
        )
        
        if filepath:
            try:
                self._analytics.export_to_csv(transactions, filepath)
                QMessageBox.information(
                    self,
                    "Export Successful",
                    f"Trade history exported to:\n{filepath}"
                )
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Export Failed",
                    f"Failed to export trade history:\n{str(e)}"
                )


class PaperTradingDockContent(QWidget):
    """Combined paper trading dock content widget.
    
    Integrates PaperTradingPanel, PortfolioView, and TradeHistoryView
    into a single scrollable widget suitable for a dock panel.
    """
    
    orderSubmitted = Signal(str, str, object, object)  # symbol, order_type, quantity, price
    
    def __init__(
        self,
        portfolio: IPortfolioManager,
        order_service: IOrderService,
        data_provider: IDataProvider,
        parent: Optional[QWidget] = None,
    ) -> None:
        """Initialize the combined paper trading dock content.
        
        Args:
            portfolio: Portfolio manager
            order_service: Order service
            data_provider: Data provider
            parent: Parent widget
        """
        super().__init__(parent)
        
        self._portfolio = portfolio
        self._order_service = order_service
        self._data_provider = data_provider
        
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        """Set up the UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Order entry panel
        self._trading_panel = PaperTradingPanel(
            self._portfolio,
            self._order_service,
            self._data_provider,
            self
        )
        self._trading_panel.orderSubmitted.connect(self._on_order_submitted)
        layout.addWidget(self._trading_panel)
        
        # Portfolio view
        portfolio_group = QGroupBox("Portfolio")
        portfolio_layout = QVBoxLayout(portfolio_group)
        portfolio_layout.setContentsMargins(0, 0, 0, 0)
        self._portfolio_view = PortfolioView(
            self._portfolio,
            self._data_provider,
            self
        )
        portfolio_layout.addWidget(self._portfolio_view)
        layout.addWidget(portfolio_group)
        
        # Trade history view
        history_group = QGroupBox("Trade History")
        history_layout = QVBoxLayout(history_group)
        history_layout.setContentsMargins(0, 0, 0, 0)
        self._history_view = TradeHistoryView(
            self._portfolio,
            self
        )
        history_layout.addWidget(self._history_view)
        layout.addWidget(history_group)
    
    def _on_order_submitted(self, symbol: str, order_type: str, quantity, price) -> None:
        """Handle order submission from trading panel."""
        # Refresh views
        self._portfolio_view.refresh()
        self._history_view.refresh()
        # Forward signal
        self.orderSubmitted.emit(symbol, order_type, quantity, price)
    
    def refresh(self) -> None:
        """Refresh all views."""
        self._trading_panel.refresh()
        self._portfolio_view.refresh()
        self._history_view.refresh()
    
    def set_symbol(self, symbol: str) -> None:
        """Set the symbol in the order entry form.
        
        Args:
            symbol: Trading pair symbol
        """
        self._trading_panel.set_symbol(symbol)
    
    @property
    def trading_panel(self) -> PaperTradingPanel:
        """Get the trading panel widget."""
        return self._trading_panel
    
    @property
    def portfolio_view(self) -> PortfolioView:
        """Get the portfolio view widget."""
        return self._portfolio_view
    
    @property
    def history_view(self) -> TradeHistoryView:
        """Get the trade history view widget."""
        return self._history_view
