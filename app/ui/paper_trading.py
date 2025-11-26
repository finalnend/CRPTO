"""Paper Trading UI Panel Module.

Provides UI components for paper trading functionality including:
- Order entry form (symbol, quantity, buy/sell buttons)
- Balance and connection status display
- Portfolio view with positions
- Trade history view with performance metrics
- Quick preset buttons, quantity slider, input validation
- Order confirmation dialog and toast notifications
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Optional, Callable, Dict, List

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QKeyEvent
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
from app.ui.utils import QuantityCalculator, InputValidator, ValidationState
from app.ui.widgets.symbol_dropdown import SymbolDropdown
from app.ui.widgets.quick_preset_buttons import QuickPresetButtons
from app.ui.widgets.quantity_slider import QuantitySlider
from app.ui.widgets.order_confirmation_dialog import OrderConfirmationDialog
from app.ui.widgets.toast_notification import ToastManager


class PaperTradingPanel(QWidget):
    """Main paper trading panel widget.
    
    Contains order entry form, balance display, and connection status.
    Emits signals when orders are submitted.
    
    Enhanced with:
    - Quick preset buttons (25%, 50%, 75%, 100%)
    - Quantity slider with bidirectional sync
    - Input validation with visual feedback
    - Symbol dropdown for quick selection
    - Keyboard shortcuts (Enter=Buy, Shift+Enter=Sell, Escape=Clear)
    - Order confirmation dialog for large orders
    - Toast notifications for order results
    
    Signals:
        orderSubmitted: Emitted when an order is successfully submitted
        balanceChanged: Emitted when balance changes after order execution
    """
    
    orderSubmitted = Signal(str, str, object, object)  # symbol, order_type, quantity, price
    balanceChanged = Signal(object)  # new balance as Decimal
    
    # Border colors for validation states
    BORDER_COLORS = {
        ValidationState.VALID: "#28A745",      # Green
        ValidationState.WARNING: "#FFC107",    # Orange
        ValidationState.INVALID: "#DC3545",    # Red
        ValidationState.NEUTRAL: "#3a3a3a",    # Default gray
    }
    
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
        
        # Utility classes
        self._input_validator = InputValidator()
        self._current_validation_state = ValidationState.NEUTRAL
        
        # Toast manager (will be initialized after UI setup)
        self._toast_manager: Optional[ToastManager] = None
        
        # Track if we're updating programmatically to avoid loops
        self._updating_slider = False
        self._updating_input = False
        
        self._setup_ui()
        self._update_balance_display()
        self._update_connection_status()
        self._update_preset_buttons_state()

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
        
        # Symbol input with dropdown (Requirements 8.1, 8.2, 8.3, 8.4, 8.5)
        symbol_layout = QHBoxLayout()
        symbol_layout.addWidget(QLabel("Symbol:"))
        self._symbol_input = QLineEdit()
        self._symbol_input.setPlaceholderText("e.g., BTCUSDT")
        self._symbol_input.textChanged.connect(self._on_symbol_changed)
        self._symbol_input.installEventFilter(self)
        symbol_layout.addWidget(self._symbol_input)
        
        # Symbol dropdown button
        self._symbol_dropdown = SymbolDropdown()
        self._symbol_dropdown.symbolSelected.connect(self._on_symbol_selected)
        symbol_layout.addWidget(self._symbol_dropdown)
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
        self._quantity_input.installEventFilter(self)
        qty_layout.addWidget(self._quantity_input)
        order_layout.addLayout(qty_layout)
        
        # Quick preset buttons (Requirements 1.1, 1.2, 1.3, 1.4)
        self._preset_buttons = QuickPresetButtons()
        self._preset_buttons.presetClicked.connect(self._on_preset_clicked)
        order_layout.addWidget(self._preset_buttons)
        
        # Quantity slider (Requirements 2.1, 2.2, 2.3, 2.4)
        self._quantity_slider = QuantitySlider()
        self._quantity_slider.valueChanged.connect(self._on_slider_value_changed)
        order_layout.addWidget(self._quantity_slider)
        
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
        
        # Keyboard shortcuts hint
        shortcuts_label = QLabel("Enter: Buy | Shift+Enter: Sell | Esc: Clear")
        shortcuts_label.setStyleSheet("color: #888; font-size: 10px;")
        shortcuts_label.setAlignment(Qt.AlignCenter)
        order_layout.addWidget(shortcuts_label)
        
        # Status message
        self._status_message = QLabel("")
        self._status_message.setWordWrap(True)
        order_layout.addWidget(self._status_message)
        
        layout.addWidget(order_group)
        layout.addStretch()
        
        # Initialize toast manager
        self._toast_manager = ToastManager(self)
    
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
        self._update_preset_buttons_state()
        self._update_slider_range()
        self._validate_input()
        
        # Filter symbol dropdown as user types
        self._symbol_dropdown.filter_symbols(text)
    
    def _on_symbol_selected(self, symbol: str) -> None:
        """Handle symbol selection from dropdown.
        
        Requirements 8.3: Fill symbol input and update price display.
        
        Args:
            symbol: Selected symbol string
        """
        self._symbol_input.setText(symbol)
        # Price update happens via _on_symbol_changed
    
    def _on_quantity_changed(self, text: str) -> None:
        """Handle quantity input change."""
        self._update_order_value()
        self._validate_input()
        
        # Update slider if not already updating from slider
        if not self._updating_slider:
            self._updating_input = True
            try:
                qty_text = text.strip()
                if qty_text:
                    try:
                        quantity = Decimal(qty_text)
                        if quantity >= Decimal("0"):
                            self._quantity_slider.set_value(quantity)
                    except InvalidOperation:
                        pass
                else:
                    self._quantity_slider.set_value(Decimal("0"))
            finally:
                self._updating_input = False
    
    def _on_preset_clicked(self, percentage: float) -> None:
        """Handle preset button click.
        
        Requirements 1.2, 1.3: Calculate quantity based on percentage.
        
        Args:
            percentage: Percentage as decimal (0.25, 0.5, 0.75, 1.0)
        """
        symbol = self._symbol_input.text().strip().upper()
        price = self._data_provider.get_current_price(symbol)
        
        if price is None:
            return
        
        balance = self._portfolio.get_balance()
        position = self._portfolio.get_position(symbol)
        position_size = position.quantity if position else Decimal("0")
        
        # Determine order type based on which is more relevant
        # If user has a position, assume sell; otherwise assume buy
        if position_size > Decimal("0"):
            # Calculate sell quantity
            quantity = QuantityCalculator.calculate_sell_quantity(position_size, percentage)
        else:
            # Calculate buy quantity
            quantity = QuantityCalculator.calculate_buy_quantity(balance, price, percentage)
        
        # Format quantity and set in input
        qty_str = f"{quantity:,.8f}".rstrip('0').rstrip('.')
        self._quantity_input.setText(qty_str)
    
    def _on_slider_value_changed(self, value: Decimal) -> None:
        """Handle slider value change.
        
        Requirements 2.2: Update quantity input field in real-time.
        
        Args:
            value: New quantity value from slider
        """
        if self._updating_input:
            return
        
        self._updating_slider = True
        try:
            if value > Decimal("0"):
                qty_str = f"{value:,.8f}".rstrip('0').rstrip('.')
                self._quantity_input.setText(qty_str)
            else:
                self._quantity_input.setText("")
        finally:
            self._updating_slider = False
    
    def _update_slider_range(self) -> None:
        """Update slider range based on balance/position.
        
        Requirements 2.4: Slider max represents 100% of available amount.
        """
        symbol = self._symbol_input.text().strip().upper()
        price = self._data_provider.get_current_price(symbol)
        balance = self._portfolio.get_balance()
        position = self._portfolio.get_position(symbol)
        position_size = position.quantity if position else Decimal("0")
        
        # Determine max based on context
        if position_size > Decimal("0"):
            # For sell: max is position size
            max_qty = position_size
        elif price and price > Decimal("0"):
            # For buy: max is balance / price
            max_qty = balance / price
        else:
            max_qty = Decimal("0")
        
        self._quantity_slider.set_range(Decimal("0"), max_qty)
    
    def _update_preset_buttons_state(self) -> None:
        """Update preset buttons enabled state.
        
        Requirements 1.4: Disable presets when price unavailable.
        """
        symbol = self._symbol_input.text().strip().upper()
        price = self._data_provider.get_current_price(symbol) if symbol else None
        self._preset_buttons.set_enabled(price is not None)
    
    def _validate_input(self) -> None:
        """Validate quantity input and update visual feedback.
        
        Requirements 3.1, 3.2, 3.3, 3.4, 3.5: Input validation with visual feedback.
        """
        symbol = self._symbol_input.text().strip().upper()
        qty_text = self._quantity_input.text().strip()
        price = self._data_provider.get_current_price(symbol) if symbol else None
        balance = self._portfolio.get_balance()
        position = self._portfolio.get_position(symbol)
        position_size = position.quantity if position else Decimal("0")
        
        # Determine order type for validation (assume BUY if no position)
        order_type = "SELL" if position_size > Decimal("0") else "BUY"
        
        state, message = self._input_validator.validate_quantity(
            qty_text, order_type, balance, position_size, price
        )
        
        self._current_validation_state = state
        self._apply_validation_style(state, message)
        self._update_buttons_state(state, symbol)
    
    def _apply_validation_style(self, state: ValidationState, message: str) -> None:
        """Apply visual styling based on validation state.
        
        Args:
            state: Current validation state
            message: Validation message for tooltip
        """
        border_color = self.BORDER_COLORS[state]
        self._quantity_input.setStyleSheet(f"""
            QLineEdit {{
                border: 2px solid {border_color};
                border-radius: 4px;
                padding: 4px;
            }}
        """)
        
        if message:
            self._quantity_input.setToolTip(message)
        else:
            self._quantity_input.setToolTip("")
    
    def _update_buttons_state(self, state: ValidationState, symbol: str) -> None:
        """Update buy/sell button enabled state.
        
        Requirements 3.5: Disable buttons when symbol is empty or invalid.
        
        Args:
            state: Current validation state
            symbol: Current symbol
        """
        connected = self._data_provider.is_connected()
        has_symbol = bool(symbol)
        valid_input = state in (ValidationState.VALID, ValidationState.WARNING)
        
        # Enable buttons if connected, has symbol, and input is valid or neutral
        can_submit = connected and has_symbol and (valid_input or state == ValidationState.NEUTRAL)
        
        self._buy_button.setEnabled(can_submit)
        self._sell_button.setEnabled(can_submit)
    
    def _clear_inputs(self) -> None:
        """Clear all input fields.
        
        Requirements 5.3: Escape key clears inputs.
        """
        self._symbol_input.clear()
        self._quantity_input.clear()
        self._quantity_slider.set_value(Decimal("0"))
        self._status_message.clear()
    
    def eventFilter(self, obj, event) -> bool:
        """Handle keyboard events for shortcuts.
        
        Requirements 5.1, 5.2, 5.3: Keyboard shortcuts.
        """
        from PySide6.QtCore import QEvent
        
        if event.type() == QEvent.KeyPress:
            key = event.key()
            modifiers = event.modifiers()
            
            if key == Qt.Key_Return or key == Qt.Key_Enter:
                if modifiers & Qt.ShiftModifier:
                    # Shift+Enter: Sell
                    self._on_sell_clicked()
                    return True
                else:
                    # Enter: Buy
                    self._on_buy_clicked()
                    return True
            elif key == Qt.Key_Escape:
                # Escape: Clear inputs
                self._clear_inputs()
                return True
        
        return super().eventFilter(obj, event)
    
    def update_symbol_list(self, symbols: List[str], prices: Dict[str, Decimal]) -> None:
        """Update the symbol dropdown with available symbols and prices.
        
        Args:
            symbols: List of available symbol strings
            prices: Dictionary mapping symbols to current prices
        """
        self._symbol_dropdown.set_symbols(symbols, prices)
    
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
        
        Requirements 4.1, 4.2, 4.3, 4.4: Order confirmation for large orders.
        Requirements 6.1, 6.2: Toast notifications for order results.
        
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
        
        # Get current price for confirmation check
        price = self._data_provider.get_current_price(symbol)
        if price is None:
            self._show_status("Cannot place order: Price data unavailable", error=True)
            return
        
        total_value = quantity * price
        balance = self._portfolio.get_balance()
        
        # Check if order requires confirmation (Requirements 4.1)
        if OrderConfirmationDialog.requires_confirmation(total_value, balance):
            dialog = OrderConfirmationDialog(
                symbol=symbol,
                order_type=order_type,
                quantity=quantity,
                price=price,
                total_value=total_value,
                parent=self,
            )
            if not dialog.exec():
                # User cancelled (Requirements 4.4)
                self._show_status("Order cancelled", error=False)
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
            
            # Show success toast (Requirements 6.1)
            if self._toast_manager:
                exec_price = result.transaction.price if result.transaction else price
                toast_msg = f"{order_type} {quantity:,.8f}".rstrip('0').rstrip('.') + f" {symbol} @ ${exec_price:,.2f}"
                self._toast_manager.show_success(toast_msg)
            
            # Clear inputs
            self._quantity_input.clear()
        else:
            self._show_status(result.message, error=True)
            
            # Show error toast (Requirements 6.2)
            if self._toast_manager:
                self._toast_manager.show_error(result.message)
    
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
    
    def prefill_close_position(self, symbol: str, quantity: Decimal) -> None:
        """Pre-fill the order form for closing a position.
        
        Requirements 7.2: Pre-fill order form with SELL order for full position.
        
        Args:
            symbol: Trading pair symbol
            quantity: Position quantity to sell
        """
        # Set symbol
        self._symbol_input.setText(symbol)
        
        # Set quantity
        qty_str = f"{quantity:,.8f}".rstrip('0').rstrip('.')
        self._quantity_input.setText(qty_str)
        
        # Update slider to match
        self._quantity_slider.set_value(quantity)
        
        # Trigger validation and price update
        self._on_symbol_changed(symbol)


class PortfolioView(QWidget):
    """Widget displaying portfolio positions and value.
    
    Shows a table of positions with symbol, quantity, average cost,
    current value, unrealized PnL, and a Close button for quick actions.
    Also displays total portfolio value and total unrealized PnL.
    
    Signals:
        closePositionRequested: Emitted when user clicks Close button on a position.
            Args: symbol (str), quantity (Decimal)
    """
    
    closePositionRequested = Signal(str, object)  # symbol, quantity (Decimal)
    
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
        
        # Positions table with Close button column (Requirements 7.1, 7.4)
        self._positions_table = QTableWidget()
        self._positions_table.setColumnCount(6)
        self._positions_table.setHorizontalHeaderLabels([
            "Symbol", "Qty", "Avg Cost", "Value", "P&L", "Action"
        ])
        self._positions_table.verticalHeader().setVisible(False)
        self._positions_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._positions_table.setSelectionBehavior(QTableWidget.SelectRows)
        self._positions_table.setAlternatingRowColors(True)
        # Use ResizeToContents for most columns, stretch for P&L
        header = self._positions_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.Stretch)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        
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
            
            # Close button (Requirements 7.1, 7.4)
            close_button = self._create_close_button(symbol, position.quantity, unrealized_pnl)
            self._positions_table.setCellWidget(row, 5, close_button)
        
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
    
    def _create_close_button(self, symbol: str, quantity: Decimal, unrealized_pnl: Decimal) -> QPushButton:
        """Create a Close button for a position row.
        
        Requirements 7.1, 7.4: Show Close button with color based on P&L.
        
        Args:
            symbol: Trading pair symbol
            quantity: Position quantity
            unrealized_pnl: Unrealized profit/loss for the position
            
        Returns:
            Configured QPushButton widget
        """
        close_button = QPushButton("Close")
        button_color = self.get_close_button_color(unrealized_pnl)
        close_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {button_color};
                color: white;
                font-weight: bold;
                padding: 4px 8px;
                border-radius: 4px;
                border: none;
            }}
            QPushButton:hover {{
                opacity: 0.8;
            }}
        """)
        close_button.setToolTip(f"Close {symbol} position")
        
        # Connect button click to emit signal with position data
        close_button.clicked.connect(lambda: self._on_close_clicked(symbol, quantity))
        
        return close_button
    
    def _on_close_clicked(self, symbol: str, quantity: Decimal) -> None:
        """Handle Close button click.
        
        Requirements 7.2: Pre-fill order form with SELL order for full position.
        
        Args:
            symbol: Trading pair symbol
            quantity: Position quantity to close
        """
        self.closePositionRequested.emit(symbol, quantity)
    
    @staticmethod
    def get_close_button_color(unrealized_pnl: Decimal) -> str:
        """Get the Close button color based on unrealized P&L.
        
        Requirements 7.4: Green for profit, red for loss.
        
        Args:
            unrealized_pnl: Unrealized profit/loss value
            
        Returns:
            Hex color string ("#28A745" for profit, "#DC3545" for loss)
        """
        if unrealized_pnl > Decimal("0"):
            return "#28A745"  # Green for profit
        elif unrealized_pnl < Decimal("0"):
            return "#DC3545"  # Red for loss
        else:
            return "#6c757d"  # Gray for break-even


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
        # Connect close position signal to pre-fill order form (Requirements 7.2)
        self._portfolio_view.closePositionRequested.connect(self._on_close_position_requested)
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
    
    def _on_close_position_requested(self, symbol: str, quantity) -> None:
        """Handle close position request from portfolio view.
        
        Requirements 7.2: Pre-fill order form with SELL order for full position.
        
        Args:
            symbol: Trading pair symbol
            quantity: Position quantity to close
        """
        self._trading_panel.prefill_close_position(symbol, quantity)
    
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
