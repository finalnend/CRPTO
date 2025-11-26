"""Quick Preset Buttons Widget.

Provides a widget with 4 QPushButtons (25%, 50%, 75%, 100%) for quick
quantity selection in the order panel.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget, QHBoxLayout, QPushButton


class QuickPresetButtons(QWidget):
    """Quick quantity preset buttons (25%, 50%, 75%, 100%).
    
    Emits presetClicked signal with percentage value when a button is clicked.
    
    Signals:
        presetClicked: Emitted with percentage as decimal (0.25, 0.5, 0.75, 1.0)
    """
    
    presetClicked = Signal(float)
    
    # Preset percentages
    PRESETS = [
        (0.25, "25%"),
        (0.50, "50%"),
        (0.75, "75%"),
        (1.00, "100%"),
    ]
    
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """Initialize the quick preset buttons widget.
        
        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self._buttons: list[QPushButton] = []
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        """Set up the UI components."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        
        for percentage, label in self.PRESETS:
            button = QPushButton(label)
            button.setMinimumWidth(45)
            button.setStyleSheet(self._get_button_style())
            button.setToolTip(f"Set quantity to {label} of available amount")
            button.clicked.connect(lambda checked, p=percentage: self._on_preset_clicked(p))
            layout.addWidget(button)
            self._buttons.append(button)
    
    def _get_button_style(self) -> str:
        """Get the stylesheet for preset buttons."""
        return """
            QPushButton {
                background-color: #2a2a2a;
                color: #E6E6E6;
                border: 1px solid #3a3a3a;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 10pt;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #3a3a3a;
                border-color: #4a9eff;
            }
            QPushButton:pressed {
                background-color: #4a9eff;
                color: white;
            }
            QPushButton:disabled {
                background-color: #1a1a1a;
                color: #666666;
                border-color: #2a2a2a;
            }
        """
    
    def _on_preset_clicked(self, percentage: float) -> None:
        """Handle preset button click.
        
        Args:
            percentage: The percentage value (0.25, 0.5, 0.75, 1.0)
        """
        self.presetClicked.emit(percentage)
    
    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable all preset buttons.
        
        Args:
            enabled: True to enable, False to disable
        """
        for button in self._buttons:
            button.setEnabled(enabled)
        
        # Update tooltip when disabled
        if not enabled:
            for button in self._buttons:
                button.setToolTip("Price data required to use presets")
        else:
            for button, (percentage, label) in zip(self._buttons, self.PRESETS):
                button.setToolTip(f"Set quantity to {label} of available amount")
