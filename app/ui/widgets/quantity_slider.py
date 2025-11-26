"""Quantity Slider Widget.

Provides a slider widget for visual quantity adjustment with
bidirectional sync to input fields.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Optional

from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import QWidget, QHBoxLayout, QSlider, QLabel


class QuantitySlider(QWidget):
    """Quantity slider with bidirectional sync to input field.
    
    Provides a slider for visual quantity adjustment with support for
    Decimal precision for crypto quantities.
    
    Signals:
        valueChanged: Emitted with quantity value as Decimal when slider moves
    """
    
    valueChanged = Signal(object)  # Decimal value
    
    # Internal slider uses integer steps, we scale to support decimals
    SLIDER_STEPS = 1000
    
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """Initialize the quantity slider widget.
        
        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        
        self._min_value = Decimal("0")
        self._max_value = Decimal("1")
        self._current_value = Decimal("0")
        self._updating = False  # Prevent recursive updates
        
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        """Set up the UI components."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        # Slider
        self._slider = QSlider(Qt.Horizontal)
        self._slider.setMinimum(0)
        self._slider.setMaximum(self.SLIDER_STEPS)
        self._slider.setValue(0)
        self._slider.setStyleSheet(self._get_slider_style())
        self._slider.valueChanged.connect(self._on_slider_changed)
        layout.addWidget(self._slider, stretch=1)
        
        # Value display label
        self._value_label = QLabel("0%")
        self._value_label.setMinimumWidth(40)
        self._value_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self._value_label.setStyleSheet("color: #E6E6E6; font-size: 10pt;")
        layout.addWidget(self._value_label)
    
    def _get_slider_style(self) -> str:
        """Get the stylesheet for the slider."""
        return """
            QSlider::groove:horizontal {
                border: 1px solid #3a3a3a;
                height: 6px;
                background: #2a2a2a;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #4a9eff;
                border: 1px solid #3a8eef;
                width: 14px;
                height: 14px;
                margin: -5px 0;
                border-radius: 7px;
            }
            QSlider::handle:horizontal:hover {
                background: #5aafff;
            }
            QSlider::handle:horizontal:disabled {
                background: #666666;
                border-color: #555555;
            }
            QSlider::sub-page:horizontal {
                background: #4a9eff;
                border-radius: 3px;
            }
            QSlider::add-page:horizontal {
                background: #2a2a2a;
                border-radius: 3px;
            }
            QSlider::groove:horizontal:disabled {
                background: #1a1a1a;
            }
        """
    
    def _on_slider_changed(self, slider_value: int) -> None:
        """Handle slider value change.
        
        Args:
            slider_value: The slider position (0 to SLIDER_STEPS)
        """
        if self._updating:
            return
        
        self._updating = True
        try:
            # Calculate the actual value from slider position
            if self._max_value > self._min_value:
                ratio = Decimal(str(slider_value)) / Decimal(str(self.SLIDER_STEPS))
                self._current_value = self._min_value + (self._max_value - self._min_value) * ratio
            else:
                self._current_value = self._min_value
            
            # Update percentage display
            percentage = (slider_value / self.SLIDER_STEPS) * 100
            self._value_label.setText(f"{percentage:.0f}%")
            
            # Emit the value changed signal
            self.valueChanged.emit(self._current_value)
        finally:
            self._updating = False
    
    def set_range(self, min_val: Decimal, max_val: Decimal) -> None:
        """Set the slider range.
        
        Args:
            min_val: Minimum value
            max_val: Maximum value
        """
        self._min_value = min_val
        self._max_value = max_val
        
        # Update current value if out of range
        if self._current_value < min_val:
            self.set_value(min_val)
        elif self._current_value > max_val:
            self.set_value(max_val)
    
    def set_value(self, value: Decimal) -> None:
        """Set the slider value.
        
        Args:
            value: The quantity value to set
        """
        if self._updating:
            return
        
        self._updating = True
        try:
            # Clamp value to range
            self._current_value = max(self._min_value, min(self._max_value, value))
            
            # Calculate slider position
            if self._max_value > self._min_value:
                ratio = (self._current_value - self._min_value) / (self._max_value - self._min_value)
                slider_pos = int(float(ratio) * self.SLIDER_STEPS)
            else:
                slider_pos = 0
            
            self._slider.setValue(slider_pos)
            
            # Update percentage display
            percentage = (slider_pos / self.SLIDER_STEPS) * 100
            self._value_label.setText(f"{percentage:.0f}%")
        finally:
            self._updating = False
    
    def get_value(self) -> Decimal:
        """Get the current slider value.
        
        Returns:
            Current quantity value as Decimal
        """
        return self._current_value
    
    def setEnabled(self, enabled: bool) -> None:
        """Enable or disable the slider.
        
        Args:
            enabled: True to enable, False to disable
        """
        super().setEnabled(enabled)
        self._slider.setEnabled(enabled)
