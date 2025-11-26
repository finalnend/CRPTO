"""Acrylic/Frosted Glass Effect Widget Module.

Provides modern frosted glass visual effects for UI components.
Implements fallback to solid backgrounds when effects are not supported.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QPaintEvent, QBrush
from PySide6.QtWidgets import QWidget, QGraphicsBlurEffect, QVBoxLayout


class IAcrylicEffect(ABC):
    """Interface for acrylic effect implementations."""

    @abstractmethod
    def set_blur_radius(self, radius: int) -> None:
        """Set the blur radius for the effect."""
        ...

    @abstractmethod
    def set_tint_color(self, color: QColor, opacity: float) -> None:
        """Set the tint color and opacity for the effect."""
        ...

    @abstractmethod
    def is_supported(self) -> bool:
        """Check if acrylic effects are supported on this system."""
        ...


class AcrylicWidget(QWidget):
    """Widget with frosted glass background effect.
    
    Provides a semi-transparent blurred background effect that creates
    a modern "acrylic" or "frosted glass" appearance. Falls back to
    solid semi-transparent backgrounds when effects are not supported.
    
    Implements IAcrylicEffect interface methods.
    
    Args:
        parent: Parent widget
        blur_radius: Blur intensity (default: 20)
        tint_opacity: Background opacity 0.0-1.0 (default: 0.7)
    """

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        blur_radius: int = 20,
        tint_opacity: float = 0.7,
    ) -> None:
        super().__init__(parent)
        
        self._blur_radius = blur_radius
        self._tint_opacity = max(0.0, min(1.0, tint_opacity))
        self._tint_color = QColor(30, 30, 30)  # Default dark tint
        self._effects_supported = True
        self._blur_effect: Optional[QGraphicsBlurEffect] = None
        
        # Set up widget properties
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAutoFillBackground(False)
        
        # Create internal layout for child widgets
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        
        # Try to apply blur effect
        self._setup_blur_effect()

    def _setup_blur_effect(self) -> None:
        """Set up the blur effect if supported."""
        try:
            self._blur_effect = QGraphicsBlurEffect(self)
            self._blur_effect.setBlurRadius(self._blur_radius)
            self._blur_effect.setBlurHints(QGraphicsBlurEffect.QualityHint)
            # Note: We don't apply the effect to self directly as it would blur content
            # Instead, we use custom painting for the background
            self._effects_supported = True
        except Exception:
            self._effects_supported = False
            self._blur_effect = None

    def set_blur_radius(self, radius: int) -> None:
        """Set the blur radius for the effect.
        
        Args:
            radius: Blur radius in pixels (clamped to 0-100)
        """
        self._blur_radius = max(0, min(100, radius))
        if self._blur_effect:
            self._blur_effect.setBlurRadius(self._blur_radius)
        self.update()

    def set_tint_color(self, color: QColor, opacity: float) -> None:
        """Set the tint color and opacity for the effect.
        
        Args:
            color: The tint color
            opacity: Opacity value 0.0-1.0
        """
        self._tint_color = color
        self._tint_opacity = max(0.0, min(1.0, opacity))
        self.update()

    def is_supported(self) -> bool:
        """Check if acrylic effects are supported on this system.
        
        Returns:
            True if blur effects are supported, False otherwise
        """
        return self._effects_supported

    def get_blur_radius(self) -> int:
        """Get the current blur radius."""
        return self._blur_radius

    def get_tint_opacity(self) -> float:
        """Get the current tint opacity."""
        return self._tint_opacity

    def get_tint_color(self) -> QColor:
        """Get the current tint color."""
        return self._tint_color

    def apply_theme(self, mode: str, accent: QColor) -> None:
        """Apply theme-aware styling to the acrylic effect.
        
        Adjusts opacity and blur for dark/light modes to maintain readability.
        Uses theme module for contrast-compliant colors.
        
        Args:
            mode: Theme mode ("dark" or "light")
            accent: Accent color for the theme
        """
        # Import here to avoid circular imports
        from app.theme import get_acrylic_colors
        
        tint_color, opacity, blur_radius = get_acrylic_colors(mode)
        self._tint_color = tint_color
        self._tint_opacity = opacity
        self._blur_radius = blur_radius
        
        if self._blur_effect:
            self._blur_effect.setBlurRadius(self._blur_radius)
        
        self.update()
    
    def get_text_color(self, mode: str) -> QColor:
        """Get a contrast-compliant text color for the current acrylic background.
        
        Args:
            mode: Theme mode ("dark" or "light")
            
        Returns:
            Text color that meets WCAG AA contrast requirements
        """
        from app.theme import ensure_contrast_ratio
        
        # Get effective background color (tint with opacity applied)
        effective_bg = QColor(self._tint_color)
        
        # Default text color based on mode
        if mode == "dark":
            text = QColor("#E6E6E6")
        else:
            text = QColor("#111111")
        
        return ensure_contrast_ratio(text, effective_bg)

    def paintEvent(self, event: QPaintEvent) -> None:
        """Paint the acrylic background effect."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Create the background color with opacity
        bg_color = QColor(self._tint_color)
        bg_color.setAlphaF(self._tint_opacity)
        
        if self._effects_supported:
            # Draw semi-transparent background (simulated acrylic)
            # The actual blur effect would require compositing with content behind
            # For now, we use a semi-transparent solid with noise texture simulation
            painter.fillRect(self.rect(), QBrush(bg_color))
            
            # Add subtle noise/grain effect for acrylic appearance
            noise_color = QColor(255, 255, 255, 5) if self._tint_opacity > 0.5 else QColor(0, 0, 0, 5)
            painter.fillRect(self.rect(), QBrush(noise_color))
        else:
            # Fallback: solid semi-transparent background
            painter.fillRect(self.rect(), QBrush(bg_color))
        
        painter.end()
        super().paintEvent(event)

    def layout(self) -> QVBoxLayout:
        """Get the internal layout for adding child widgets."""
        return self._layout


class AcrylicPanel(AcrylicWidget):
    """Convenience class for acrylic panels with common styling.
    
    Pre-configured with rounded corners and padding suitable for
    sidebar panels and dialog boxes.
    """

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        blur_radius: int = 20,
        tint_opacity: float = 0.7,
    ) -> None:
        super().__init__(parent, blur_radius, tint_opacity)
        
        # Add padding for panel content
        self._layout.setContentsMargins(10, 10, 10, 10)
        self._layout.setSpacing(8)

    def paintEvent(self, event: QPaintEvent) -> None:
        """Paint the acrylic panel with rounded corners."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Create the background color with opacity
        bg_color = QColor(self._tint_color)
        bg_color.setAlphaF(self._tint_opacity)
        
        # Draw rounded rectangle
        painter.setBrush(QBrush(bg_color))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(self.rect(), 8, 8)
        
        painter.end()
        # Skip AcrylicWidget.paintEvent to avoid double painting
        QWidget.paintEvent(self, event)
