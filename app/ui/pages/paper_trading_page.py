"""Paper Trading Full Page.

Full-page paper trading interface with three-column layout.
Implements Requirements 3.1, 3.2, 3.3, 3.4.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QSplitter,
    QGroupBox,
    QLabel,
    QFrame,
)

from app.trading.portfolio import IPortfolioManager
from app.trading.orders import IOrderService, IDataProvider
from app.ui.paper_trading import (
    PaperTradingPanel,
    PortfolioView,
    TradeHistoryView,
)


class PaperTradingFullPage(QWidget):
    """Full-page paper trading interface.
    
    Displays a three-column layout with order entry, portfolio positions,
    and trade history with performance metrics.
    
    Signals:
        orderSubmitted: Emitted when an order is successfully submitted
    """
    
    orderSubmitted = Signal(str, str, object, object)  # symbol, order_type, quantity, price
    
    def __init__(
        self,
        portfolio: IPortfolioManager,
        order_service: IOrderService,
        data_provider: IDataProvider,
        parent: Optional[QWidget] = None,
    ) -> None:
        """Initialize the paper trading page.
        
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
    
    def _setup_ui(self) -> None:
        """Set up the page UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)
        
        # Header with real-time price display
        header = self._create_header()
        layout.addWidget(header)
        
        # Three-column splitter layout
        splitter = QSplitter(Qt.Horizontal)
        
        # Column 1: Order Entry Panel
        order_group = QGroupBox("Place Order")
        order_layout = QVBoxLayout(order_group)
        order_layout.setContentsMargins(0, 8, 0, 0)
        
        self._trading_panel = PaperTradingPanel(
            self._portfolio,
            self._order_service,
            self._data_provider,
        )
        self._trading_panel.orderSubmitted.connect(self._on_order_submitted)
        order_layout.addWidget(self._trading_panel)
        
        splitter.addWidget(order_group)
        
        # Column 2: Portfolio Positions
        portfolio_group = QGroupBox("Portfolio Positions")
        portfolio_layout = QVBoxLayout(portfolio_group)
        portfolio_layout.setContentsMargins(0, 8, 0, 0)
        
        self._portfolio_view = PortfolioView(
            self._portfolio,
            self._data_provider,
        )
        portfolio_layout.addWidget(self._portfolio_view)
        
        splitter.addWidget(portfolio_group)
        
        # Column 3: Trade History
        history_group = QGroupBox("Trade History")
        history_layout = QVBoxLayout(history_group)
        history_layout.setContentsMargins(0, 8, 0, 0)
        
        self._history_view = TradeHistoryView(self._portfolio)
        history_layout.addWidget(self._history_view)
        
        splitter.addWidget(history_group)
        
        # Set initial column sizes (equal distribution)
        splitter.setSizes([300, 400, 400])
        
        layout.addWidget(splitter, 1)
    
    def _create_header(self) -> QFrame:
        """Create the header with real-time price display."""
        header = QFrame()
        header.setStyleSheet("""
            QFrame {
                background-color: rgba(30, 30, 30, 0.8);
                border-radius: 8px;
                padding: 8px;
            }
        """)
        
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(16, 8, 16, 8)
        
        # Title
        title = QLabel("Paper Trading")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        # Real-time price display
        self._price_label = QLabel("--")
        self._price_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        header_layout.addWidget(QLabel("Current Price:"))
        header_layout.addWidget(self._price_label)
        
        header_layout.addSpacing(24)
        
        # Balance display
        self._balance_label = QLabel("$0.00")
        self._balance_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #0A84FF;")
        header_layout.addWidget(QLabel("Balance:"))
        header_layout.addWidget(self._balance_label)
        
        return header
    
    def _on_order_submitted(self, symbol: str, order_type: str, quantity, price) -> None:
        """Handle order submission from trading panel."""
        # Refresh views
        self._portfolio_view.refresh()
        self._history_view.refresh()
        self._update_balance_display()
        
        # Forward signal
        self.orderSubmitted.emit(symbol, order_type, quantity, price)
    
    def _update_balance_display(self) -> None:
        """Update the balance display in the header."""
        balance = self._portfolio.get_balance()
        self._balance_label.setText(f"${balance:,.2f}")
    
    def refresh(self) -> None:
        """Refresh all sections."""
        self._trading_panel.refresh()
        self._portfolio_view.refresh()
        self._history_view.refresh()
        self._update_balance_display()
    
    def set_symbol(self, symbol: str) -> None:
        """Set the trading symbol.
        
        Args:
            symbol: Trading pair symbol
        """
        self._trading_panel.set_symbol(symbol)
        self._update_price_display(symbol)
    
    def _update_price_display(self, symbol: str) -> None:
        """Update the real-time price display for a symbol."""
        if not symbol:
            self._price_label.setText("--")
            return
        
        price = self._data_provider.get_current_price(symbol)
        if price is not None:
            self._price_label.setText(f"${price:,.8f}".rstrip('0').rstrip('.'))
        else:
            self._price_label.setText("--")
    
    def update_price(self, symbol: str, price: Decimal) -> None:
        """Update the displayed price for a symbol.
        
        Args:
            symbol: Trading pair symbol
            price: Current price
        """
        # Update price label if this is the current symbol
        current_symbol = self._trading_panel._symbol_input.text().strip().upper()
        if symbol.upper() == current_symbol:
            self._price_label.setText(f"${price:,.8f}".rstrip('0').rstrip('.'))
        
        # Refresh portfolio view to update unrealized P&L
        self._portfolio_view.refresh()
    
    def on_container_width_changed(self, width: int) -> None:
        """Handle container width changes for responsive layout.
        
        Implements Requirements 7.3, 7.4: Adjust layout based on available width.
        
        Args:
            width: The new available width in pixels
        """
        # Find the splitter in the layout
        splitter = self.findChild(QSplitter)
        if splitter is None:
            return
        
        # Below 800px: Stack columns vertically
        # 800px and above: Three-column horizontal layout
        if width < 800:
            splitter.setOrientation(Qt.Vertical)
            # Equal distribution in vertical mode
            splitter.setSizes([300, 300, 300])
        else:
            splitter.setOrientation(Qt.Horizontal)
            # Standard three-column distribution
            splitter.setSizes([300, 400, 400])
