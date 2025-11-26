"""Symbol Dropdown Widget.

Provides a dropdown widget for quick symbol selection with filtering
and current price display.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Dict, List, Optional

from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QListWidget,
    QListWidgetItem,
    QFrame,
)


class SymbolDropdown(QWidget):
    """Dropdown for quick symbol selection with filtering.
    
    Displays a list of available trading symbols with their current prices.
    Supports filtering based on text input.
    
    Signals:
        symbolSelected: Emitted with selected symbol string
    """
    
    symbolSelected = Signal(str)
    
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """Initialize the symbol dropdown widget.
        
        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        
        self._symbols: List[str] = []
        self._prices: Dict[str, Decimal] = {}
        self._filtered_symbols: List[str] = []
        
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        """Set up the UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Dropdown button
        self._dropdown_button = QPushButton("▼")
        self._dropdown_button.setFixedWidth(30)
        self._dropdown_button.setStyleSheet(self._get_button_style())
        self._dropdown_button.setToolTip("Select symbol from list")
        self._dropdown_button.clicked.connect(self._toggle_dropdown)
        layout.addWidget(self._dropdown_button)
        
        # Dropdown panel (hidden by default)
        self._dropdown_panel = QFrame()
        self._dropdown_panel.setStyleSheet(self._get_panel_style())
        self._dropdown_panel.hide()
        
        panel_layout = QVBoxLayout(self._dropdown_panel)
        panel_layout.setContentsMargins(4, 4, 4, 4)
        panel_layout.setSpacing(4)
        
        # Filter input
        self._filter_input = QLineEdit()
        self._filter_input.setPlaceholderText("Filter symbols...")
        self._filter_input.setStyleSheet(self._get_input_style())
        self._filter_input.textChanged.connect(self._on_filter_changed)
        panel_layout.addWidget(self._filter_input)
        
        # Symbol list
        self._symbol_list = QListWidget()
        self._symbol_list.setStyleSheet(self._get_list_style())
        self._symbol_list.setMinimumHeight(150)
        self._symbol_list.setMaximumHeight(250)
        self._symbol_list.itemClicked.connect(self._on_item_clicked)
        panel_layout.addWidget(self._symbol_list)
        
        layout.addWidget(self._dropdown_panel)
    
    def _get_button_style(self) -> str:
        """Get the stylesheet for the dropdown button."""
        return """
            QPushButton {
                background-color: #2a2a2a;
                color: #E6E6E6;
                border: 1px solid #3a3a3a;
                border-radius: 4px;
                padding: 4px;
                font-size: 10pt;
            }
            QPushButton:hover {
                background-color: #3a3a3a;
                border-color: #4a9eff;
            }
            QPushButton:pressed {
                background-color: #4a9eff;
            }
        """
    
    def _get_panel_style(self) -> str:
        """Get the stylesheet for the dropdown panel."""
        return """
            QFrame {
                background-color: #1e1e1e;
                border: 1px solid #3a3a3a;
                border-radius: 4px;
            }
        """
    
    def _get_input_style(self) -> str:
        """Get the stylesheet for the filter input."""
        return """
            QLineEdit {
                background-color: #2a2a2a;
                color: #E6E6E6;
                border: 1px solid #3a3a3a;
                border-radius: 4px;
                padding: 4px 8px;
            }
            QLineEdit:focus {
                border-color: #4a9eff;
            }
        """
    
    def _get_list_style(self) -> str:
        """Get the stylesheet for the symbol list."""
        return """
            QListWidget {
                background-color: #2a2a2a;
                color: #E6E6E6;
                border: 1px solid #3a3a3a;
                border-radius: 4px;
                outline: none;
            }
            QListWidget::item {
                padding: 6px 8px;
                border-bottom: 1px solid #3a3a3a;
            }
            QListWidget::item:hover {
                background-color: #3a3a3a;
            }
            QListWidget::item:selected {
                background-color: #4a9eff;
                color: white;
            }
        """
    
    def _toggle_dropdown(self) -> None:
        """Toggle the dropdown panel visibility."""
        if self._dropdown_panel.isVisible():
            self.hide_dropdown()
        else:
            self.show_dropdown()
    
    def _on_filter_changed(self, text: str) -> None:
        """Handle filter input change.
        
        Args:
            text: The filter text
        """
        self.filter_symbols(text)
    
    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        """Handle symbol list item click.
        
        Args:
            item: The clicked list item
        """
        # Extract symbol from item text (format: "SYMBOL - $price")
        text = item.text()
        symbol = text.split(" - ")[0] if " - " in text else text
        
        self.symbolSelected.emit(symbol)
        self.hide_dropdown()
    
    def _update_list(self) -> None:
        """Update the symbol list display."""
        self._symbol_list.clear()
        
        for symbol in self._filtered_symbols:
            price = self._prices.get(symbol)
            if price is not None:
                # Format price, removing trailing zeros
                price_str = f"${price:,.8f}".rstrip('0').rstrip('.')
                item_text = f"{symbol} - {price_str}"
            else:
                item_text = symbol
            
            item = QListWidgetItem(item_text)
            self._symbol_list.addItem(item)
    
    def set_symbols(self, symbols: List[str], prices: Dict[str, Decimal]) -> None:
        """Set the available symbols and their prices.
        
        Args:
            symbols: List of symbol strings
            prices: Dictionary mapping symbols to prices
        """
        self._symbols = sorted(symbols)
        self._prices = prices
        self._filtered_symbols = self._symbols.copy()
        self._update_list()
    
    def filter_symbols(self, text: str) -> None:
        """Filter the symbol list based on text.
        
        Args:
            text: Filter text (case-insensitive)
        """
        if not text:
            self._filtered_symbols = self._symbols.copy()
        else:
            filter_lower = text.lower()
            self._filtered_symbols = [
                s for s in self._symbols
                if filter_lower in s.lower()
            ]
        self._update_list()
    
    def show_dropdown(self) -> None:
        """Show the dropdown panel."""
        self._dropdown_panel.show()
        self._filter_input.setFocus()
        self._filter_input.clear()
        self._filtered_symbols = self._symbols.copy()
        self._update_list()
    
    def hide_dropdown(self) -> None:
        """Hide the dropdown panel."""
        self._dropdown_panel.hide()
    
    def get_filtered_symbols(self) -> List[str]:
        """Get the currently filtered symbols.
        
        Returns:
            List of filtered symbol strings
        """
        return self._filtered_symbols.copy()
