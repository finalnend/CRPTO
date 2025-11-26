"""Animation utilities for smooth UI transitions.

Provides animation helpers for:
- Price value fade transitions (Requirement 2.1)
- Expand/collapse animations (Requirement 2.2)
- Hover highlight animations (Requirement 2.3)
- Chart data smooth transitions (Requirement 2.4)
- Pulsing alert animations (Requirement 3.4)
"""

from __future__ import annotations

from typing import Optional, Callable

from PySide6.QtCore import (
    QObject,
    QPropertyAnimation,
    QEasingCurve,
    QTimer,
    Property,
    Signal,
    QParallelAnimationGroup,
    QSequentialAnimationGroup,
)
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QWidget, QGraphicsOpacityEffect, QTableWidgetItem


class FadeAnimator(QObject):
    """Handles fade in/out animations for widgets and values.
    
    Used for price update transitions (Requirement 2.1).
    """
    
    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._opacity = 1.0
    
    def get_opacity(self) -> float:
        return self._opacity
    
    def set_opacity(self, value: float) -> None:
        self._opacity = value
    
    opacity = Property(float, get_opacity, set_opacity)
    
    @staticmethod
    def fade_widget(
        widget: QWidget,
        start_opacity: float = 0.0,
        end_opacity: float = 1.0,
        duration_ms: int = 200,
        on_finished: Optional[Callable] = None,
    ) -> QPropertyAnimation:
        """Create a fade animation for a widget.
        
        Args:
            widget: Widget to animate
            start_opacity: Starting opacity (0.0-1.0)
            end_opacity: Ending opacity (0.0-1.0)
            duration_ms: Animation duration in milliseconds
            on_finished: Callback when animation completes
            
        Returns:
            The animation object (caller should keep reference)
        """
        effect = widget.graphicsEffect()
        if not isinstance(effect, QGraphicsOpacityEffect):
            effect = QGraphicsOpacityEffect(widget)
            widget.setGraphicsEffect(effect)
        
        effect.setOpacity(start_opacity)
        
        anim = QPropertyAnimation(effect, b"opacity")
        anim.setDuration(duration_ms)
        anim.setStartValue(start_opacity)
        anim.setEndValue(end_opacity)
        anim.setEasingCurve(QEasingCurve.InOutQuad)
        
        if on_finished:
            anim.finished.connect(on_finished)
        
        anim.start()
        return anim


class ValueTransitionAnimator(QObject):
    """Animates numeric value transitions with color flash.
    
    Used for price updates in table cells (Requirement 2.1).
    """
    
    valueChanged = Signal(float)
    colorChanged = Signal(QColor)
    
    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._value = 0.0
        self._color = QColor(255, 255, 255)
        self._animation: Optional[QPropertyAnimation] = None
        self._color_animation: Optional[QPropertyAnimation] = None
    
    def get_value(self) -> float:
        return self._value
    
    def set_value(self, value: float) -> None:
        self._value = value
        self.valueChanged.emit(value)
    
    def get_color(self) -> QColor:
        return self._color
    
    def set_color(self, color: QColor) -> None:
        self._color = color
        self.colorChanged.emit(color)
    
    value = Property(float, get_value, set_value)
    color = Property(QColor, get_color, set_color)
    
    def animate_to(
        self,
        target_value: float,
        duration_ms: int = 200,
        flash_color: Optional[QColor] = None,
    ) -> None:
        """Animate value change with optional color flash.
        
        Args:
            target_value: Target numeric value
            duration_ms: Animation duration
            flash_color: Color to flash during transition (green for up, red for down)
        """
        # Stop existing animations
        if self._animation and self._animation.state() == QPropertyAnimation.Running:
            self._animation.stop()
        
        self._animation = QPropertyAnimation(self, b"value")
        self._animation.setDuration(duration_ms)
        self._animation.setStartValue(self._value)
        self._animation.setEndValue(target_value)
        self._animation.setEasingCurve(QEasingCurve.OutQuad)
        self._animation.start()
        
        # Color flash effect
        if flash_color:
            self._animate_color_flash(flash_color, duration_ms)
    
    def _animate_color_flash(self, flash_color: QColor, duration_ms: int) -> None:
        """Flash color and return to normal."""
        if self._color_animation and self._color_animation.state() == QPropertyAnimation.Running:
            self._color_animation.stop()
        
        normal_color = QColor(255, 255, 255)
        
        # Flash to color then back
        self._color_animation = QPropertyAnimation(self, b"color")
        self._color_animation.setDuration(duration_ms)
        self._color_animation.setKeyValueAt(0.0, normal_color)
        self._color_animation.setKeyValueAt(0.3, flash_color)
        self._color_animation.setKeyValueAt(1.0, normal_color)
        self._color_animation.start()


class ExpandCollapseAnimator(QObject):
    """Handles smooth expand/collapse animations for widgets.
    
    Used for sidebar section animations (Requirement 2.2).
    """
    
    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._height = 0
    
    def get_height(self) -> int:
        return self._height
    
    def set_height(self, value: int) -> None:
        self._height = value
    
    height = Property(int, get_height, set_height)
    
    @staticmethod
    def animate_height(
        widget: QWidget,
        start_height: int,
        end_height: int,
        duration_ms: int = 250,
        on_finished: Optional[Callable] = None,
    ) -> QPropertyAnimation:
        """Animate widget height change.
        
        Args:
            widget: Widget to animate
            start_height: Starting height in pixels
            end_height: Ending height in pixels
            duration_ms: Animation duration
            on_finished: Callback when complete
            
        Returns:
            The animation object
        """
        anim = QPropertyAnimation(widget, b"maximumHeight")
        anim.setDuration(duration_ms)
        anim.setStartValue(start_height)
        anim.setEndValue(end_height)
        anim.setEasingCurve(QEasingCurve.InOutCubic)
        
        if on_finished:
            anim.finished.connect(on_finished)
        
        anim.start()
        return anim


class HoverAnimator(QObject):
    """Provides hover highlight animations for interactive elements.
    
    Used for button and row hover effects (Requirement 2.3).
    """
    
    def __init__(self, widget: QWidget, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._widget = widget
        self._scale = 1.0
        self._brightness = 1.0
        self._animation: Optional[QPropertyAnimation] = None
    
    def get_brightness(self) -> float:
        return self._brightness
    
    def set_brightness(self, value: float) -> None:
        self._brightness = value
        self._apply_brightness()
    
    brightness = Property(float, get_brightness, set_brightness)
    
    def _apply_brightness(self) -> None:
        """Apply brightness effect via stylesheet."""
        # Use opacity effect for brightness simulation
        effect = self._widget.graphicsEffect()
        if isinstance(effect, QGraphicsOpacityEffect):
            effect.setOpacity(min(1.0, self._brightness))
    
    def animate_hover_enter(self, duration_ms: int = 100) -> None:
        """Animate hover enter effect."""
        self._animate_brightness(1.0, 1.15, duration_ms)
    
    def animate_hover_leave(self, duration_ms: int = 100) -> None:
        """Animate hover leave effect."""
        self._animate_brightness(self._brightness, 1.0, duration_ms)
    
    def _animate_brightness(self, start: float, end: float, duration_ms: int) -> None:
        """Animate brightness change."""
        if self._animation and self._animation.state() == QPropertyAnimation.Running:
            self._animation.stop()
        
        self._animation = QPropertyAnimation(self, b"brightness")
        self._animation.setDuration(duration_ms)
        self._animation.setStartValue(start)
        self._animation.setEndValue(end)
        self._animation.setEasingCurve(QEasingCurve.OutQuad)
        self._animation.start()


class PulseAnimator(QObject):
    """Creates pulsing animation for alerts and notifications.
    
    Used for critical alert animations (Requirement 3.4).
    """
    
    pulseValue = Signal(float)
    
    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._pulse = 1.0
        self._animation: Optional[QPropertyAnimation] = None
        self._is_pulsing = False
    
    def get_pulse(self) -> float:
        return self._pulse
    
    def set_pulse(self, value: float) -> None:
        self._pulse = value
        self.pulseValue.emit(value)
    
    pulse = Property(float, get_pulse, set_pulse)
    
    def start_pulsing(
        self,
        min_value: float = 0.5,
        max_value: float = 1.0,
        duration_ms: int = 800,
    ) -> None:
        """Start continuous pulsing animation.
        
        Args:
            min_value: Minimum pulse value (opacity/scale)
            max_value: Maximum pulse value
            duration_ms: Duration of one pulse cycle
        """
        if self._is_pulsing:
            return
        
        self._is_pulsing = True
        self._animation = QPropertyAnimation(self, b"pulse")
        self._animation.setDuration(duration_ms)
        self._animation.setStartValue(max_value)
        self._animation.setKeyValueAt(0.5, min_value)
        self._animation.setEndValue(max_value)
        self._animation.setEasingCurve(QEasingCurve.InOutSine)
        self._animation.setLoopCount(-1)  # Infinite loop
        self._animation.start()
    
    def stop_pulsing(self) -> None:
        """Stop the pulsing animation."""
        self._is_pulsing = False
        if self._animation:
            self._animation.stop()
            self._pulse = 1.0
            self.pulseValue.emit(1.0)


class AnimatedTableItem(QTableWidgetItem):
    """Table item with built-in value transition animation.
    
    Provides smooth price update animations for table cells.
    """
    
    def __init__(self, text: str = "", value: float = 0.0) -> None:
        super().__init__(text)
        self._value = value
        self._animator: Optional[ValueTransitionAnimator] = None
        self._flash_timer: Optional[QTimer] = None
        self._original_background = None
    
    @property
    def value(self) -> float:
        return self._value
    
    def set_value_animated(
        self,
        new_value: float,
        format_func: Callable[[float], str],
        flash_up_color: QColor = QColor(0, 200, 0, 100),
        flash_down_color: QColor = QColor(200, 0, 0, 100),
    ) -> None:
        """Set value with animation and color flash.
        
        Args:
            new_value: New numeric value
            format_func: Function to format value as string
            flash_up_color: Color for value increase
            flash_down_color: Color for value decrease
        """
        if new_value == self._value:
            return
        
        # Determine flash color based on direction
        if new_value > self._value:
            flash_color = flash_up_color
        elif new_value < self._value:
            flash_color = flash_down_color
        else:
            flash_color = None
        
        self._value = new_value
        self.setText(format_func(new_value))
        
        # Apply flash effect
        if flash_color:
            self._flash_background(flash_color)
    
    def _flash_background(self, color: QColor, duration_ms: int = 200) -> None:
        """Flash background color briefly."""
        self._original_background = self.background()
        self.setBackground(color)
        
        # Reset after duration
        if self._flash_timer:
            self._flash_timer.stop()
        
        self._flash_timer = QTimer()
        self._flash_timer.setSingleShot(True)
        self._flash_timer.timeout.connect(self._reset_background)
        self._flash_timer.start(duration_ms)
    
    def _reset_background(self) -> None:
        """Reset background to original."""
        if self._original_background:
            self.setBackground(self._original_background)


def create_chart_transition_animation(
    series,
    old_points: list,
    new_points: list,
    duration_ms: int = 300,
) -> QPropertyAnimation:
    """Create smooth transition animation for chart data.
    
    Note: This is a helper that should be called from the chart update logic.
    The actual implementation depends on the chart library being used.
    
    Args:
        series: The chart series to animate
        old_points: Previous data points
        new_points: New data points
        duration_ms: Animation duration
        
    Returns:
        Animation object (for reference keeping)
    """
    # For QLineSeries, we interpolate between old and new points
    # This is a simplified version - full implementation would need
    # a custom animator class
    
    class ChartAnimator(QObject):
        def __init__(self, series, old_pts, new_pts):
            super().__init__()
            self._series = series
            self._old = old_pts
            self._new = new_pts
            self._progress = 0.0
        
        def get_progress(self) -> float:
            return self._progress
        
        def set_progress(self, value: float) -> None:
            self._progress = value
            self._interpolate()
        
        progress = Property(float, get_progress, set_progress)
        
        def _interpolate(self) -> None:
            """Interpolate between old and new points."""
            if not self._old or not self._new:
                return
            
            # Simple linear interpolation
            from PySide6.QtCore import QPointF
            interpolated = []
            min_len = min(len(self._old), len(self._new))
            
            for i in range(min_len):
                old_pt = self._old[i]
                new_pt = self._new[i]
                x = old_pt.x() + (new_pt.x() - old_pt.x()) * self._progress
                y = old_pt.y() + (new_pt.y() - old_pt.y()) * self._progress
                interpolated.append(QPointF(x, y))
            
            # Add remaining new points if any
            if len(self._new) > min_len:
                for i in range(min_len, len(self._new)):
                    interpolated.append(self._new[i])
            
            self._series.replace(interpolated)
    
    animator = ChartAnimator(series, old_points, new_points)
    anim = QPropertyAnimation(animator, b"progress")
    anim.setDuration(duration_ms)
    anim.setStartValue(0.0)
    anim.setEndValue(1.0)
    anim.setEasingCurve(QEasingCurve.OutQuad)
    
    # Keep animator alive
    anim.animator = animator
    anim.start()
    
    return anim
