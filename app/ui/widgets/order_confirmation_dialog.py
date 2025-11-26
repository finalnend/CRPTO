"""Order confirmation dialog for large orders.

Displays order details and requires user confirmation before execution.
Requirements: 4.1, 4.2, 4.3, 4.4
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
)


@dataclass
class OrderPreview:
    """Preview data for order confirmation."""
    symbol: str
    order_type: str
    quantity: Decimal
    price: Decimal
    total_value: Decimal
    balance_percentage: float  # percentage of balance this order represents


class OrderConfirmationDialog(QDialog):
    """Confirmation dialog for large orders.
    
    Displays order details including symbol, type, quantity, price,
    and total value. Requires user to confirm or cancel before
    order execution.
    
    Requirements: 4.1, 4.2, 4.3, 4.4
    """
    
    # Threshold for showing confirmation (50% of balance)
    CONFIRMATION_THRESHOLD = 0.5
    
    def __init__(
        self,
        symbol: str,
        order_type: str,
        quantity: Decimal,
        price: Decimal,
        total_value: Decimal,
        parent: Optional[QDialog] = None,
    ) -> None:
        """Initialize the order confirmation dialog.
        
        Args:
            symbol: Trading symbol (e.g., "BTCUSDT")
            order_type: Type of order ("BUY" or "SELL")
            quantity: Order quantity
            price: Current price per unit
            total_value: Total order value (quantity * price)
            parent: Parent widget
        """
        super().__init__(parent)
        
        self._symbol = symbol
        self._order_type = order_type
        self._quantity = quantity
        self._price = price
        self._total_value = total_value
        
        self._setup_ui()
        self._apply_style()

    def _setup_ui(self) -> None:
        """Set up the dialog UI components."""
        self.setWindowTitle("Confirm Order")
        self.setModal(True)
        self.setFixedWidth(400)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)
        
        # Warning header
        header_label = QLabel("⚠️ Large Order Confirmation")
        header_label.setObjectName("header")
        header_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(header_label)
        
        # Description
        desc_label = QLabel(
            "You are about to place a large order. "
            "Please review the details below before confirming."
        )
        desc_label.setWordWrap(True)
        desc_label.setAlignment(Qt.AlignCenter)
        desc_label.setObjectName("description")
        layout.addWidget(desc_label)
        
        # Order details frame
        details_frame = QFrame()
        details_frame.setObjectName("detailsFrame")
        details_layout = QVBoxLayout(details_frame)
        details_layout.setSpacing(8)
        details_layout.setContentsMargins(16, 16, 16, 16)
        
        # Order type with color
        type_color = "#30D158" if self._order_type.upper() == "BUY" else "#FF453A"
        type_label = QLabel(f"<span style='color: {type_color}; font-weight: bold;'>{self._order_type.upper()}</span>")
        type_label.setAlignment(Qt.AlignCenter)
        type_label.setObjectName("orderType")
        details_layout.addWidget(type_label)
        
        # Symbol
        self._add_detail_row(details_layout, "Symbol", self._symbol)
        
        # Quantity
        self._add_detail_row(details_layout, "Quantity", f"{self._quantity:,.8f}".rstrip('0').rstrip('.'))
        
        # Price
        self._add_detail_row(details_layout, "Price", f"${self._price:,.2f}")
        
        # Total value (highlighted)
        total_row = QHBoxLayout()
        total_label = QLabel("Total Value")
        total_label.setObjectName("totalLabel")
        total_value_label = QLabel(f"${self._total_value:,.2f}")
        total_value_label.setObjectName("totalValue")
        total_value_label.setAlignment(Qt.AlignRight)
        total_row.addWidget(total_label)
        total_row.addWidget(total_value_label)
        details_layout.addLayout(total_row)
        
        layout.addWidget(details_frame)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(12)
        
        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.setObjectName("cancelBtn")
        self._cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self._cancel_btn)
        
        self._confirm_btn = QPushButton("Confirm Order")
        self._confirm_btn.setObjectName("confirmBtn")
        self._confirm_btn.clicked.connect(self.accept)
        button_layout.addWidget(self._confirm_btn)
        
        layout.addLayout(button_layout)
    
    def _add_detail_row(self, layout: QVBoxLayout, label: str, value: str) -> None:
        """Add a detail row to the layout.
        
        Args:
            layout: Parent layout
            label: Label text
            value: Value text
        """
        row = QHBoxLayout()
        label_widget = QLabel(label)
        label_widget.setObjectName("detailLabel")
        value_widget = QLabel(value)
        value_widget.setObjectName("detailValue")
        value_widget.setAlignment(Qt.AlignRight)
        row.addWidget(label_widget)
        row.addWidget(value_widget)
        layout.addLayout(row)

    def _apply_style(self) -> None:
        """Apply styling to the dialog."""
        self.setStyleSheet("""
            QDialog {
                background-color: #1e1e1e;
            }
            QLabel#header {
                font-size: 14pt;
                font-weight: bold;
                color: #FFD60A;
                padding: 8px;
            }
            QLabel#description {
                font-size: 10pt;
                color: #A0A0A0;
                padding: 4px;
            }
            QFrame#detailsFrame {
                background-color: #252525;
                border: 1px solid #3a3a3a;
                border-radius: 8px;
            }
            QLabel#orderType {
                font-size: 16pt;
                padding: 8px;
            }
            QLabel#detailLabel {
                font-size: 11pt;
                color: #A0A0A0;
            }
            QLabel#detailValue {
                font-size: 11pt;
                color: #E6E6E6;
                font-weight: 500;
            }
            QLabel#totalLabel {
                font-size: 12pt;
                font-weight: bold;
                color: #E6E6E6;
            }
            QLabel#totalValue {
                font-size: 12pt;
                font-weight: bold;
                color: #FFD60A;
            }
            QPushButton#cancelBtn {
                background-color: #3a3a3a;
                color: #E6E6E6;
                border: 1px solid #4a4a4a;
                border-radius: 6px;
                padding: 10px 24px;
                font-size: 11pt;
                min-width: 100px;
            }
            QPushButton#cancelBtn:hover {
                background-color: #4a4a4a;
                border-color: #5a5a5a;
            }
            QPushButton#confirmBtn {
                background-color: #0A84FF;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 24px;
                font-size: 11pt;
                font-weight: bold;
                min-width: 120px;
            }
            QPushButton#confirmBtn:hover {
                background-color: #0070E0;
            }
        """)
    
    def exec(self) -> bool:
        """Show dialog and return True if confirmed, False if cancelled.
        
        Returns:
            True if user clicked Confirm, False if cancelled
        """
        result = super().exec()
        return result == QDialog.Accepted
    
    @property
    def symbol(self) -> str:
        """Get the order symbol."""
        return self._symbol
    
    @property
    def order_type(self) -> str:
        """Get the order type."""
        return self._order_type
    
    @property
    def quantity(self) -> Decimal:
        """Get the order quantity."""
        return self._quantity
    
    @property
    def price(self) -> Decimal:
        """Get the order price."""
        return self._price
    
    @property
    def total_value(self) -> Decimal:
        """Get the total order value."""
        return self._total_value
    
    @staticmethod
    def requires_confirmation(total_value: Decimal, balance: Decimal) -> bool:
        """Check if an order requires confirmation based on threshold.
        
        An order requires confirmation if its total value exceeds 50%
        of the available balance.
        
        Args:
            total_value: Total order value (quantity * price)
            balance: Available balance
            
        Returns:
            True if confirmation is required, False otherwise
        """
        if balance <= Decimal("0"):
            return False
        
        percentage = total_value / balance
        return percentage > Decimal(str(OrderConfirmationDialog.CONFIRMATION_THRESHOLD))
