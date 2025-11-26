"""UI Widgets for Paper Trading convenience features.

This module provides reusable UI widgets:
- QuickPresetButtons: Quick quantity preset buttons (25%, 50%, 75%, 100%)
- QuantitySlider: Quantity slider with bidirectional sync
- SymbolDropdown: Dropdown for quick symbol selection
- ToastNotification: Toast notification widget
- ToastManager: Manager for toast notifications
- ToastData: Data class for toast notifications
- OrderConfirmationDialog: Confirmation dialog for large orders
- OrderPreview: Data class for order preview
"""

from app.ui.widgets.quick_preset_buttons import QuickPresetButtons
from app.ui.widgets.quantity_slider import QuantitySlider
from app.ui.widgets.symbol_dropdown import SymbolDropdown
from app.ui.widgets.toast_notification import ToastNotification, ToastManager, ToastData
from app.ui.widgets.order_confirmation_dialog import OrderConfirmationDialog, OrderPreview

__all__ = [
    "QuickPresetButtons",
    "QuantitySlider",
    "SymbolDropdown",
    "ToastNotification",
    "ToastManager",
    "ToastData",
    "OrderConfirmationDialog",
    "OrderPreview",
]
