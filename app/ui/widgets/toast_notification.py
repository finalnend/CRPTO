"""Toast notification widget for displaying temporary messages.

Provides visual feedback for order results and other user actions.
Requirements: 6.1, 6.2, 6.3, 6.4
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from PySide6.QtCore import (
    Qt,
    Signal,
    QTimer,
    QPropertyAnimation,
    QEasingCurve,
)
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QGraphicsOpacityEffect,
)


@dataclass
class ToastData:
    """Data for a toast notification."""
    message: str
    toast_type: str  # "success", "error", "info"
    timestamp: datetime
    duration_ms: int = 4000


class ToastNotification(QFrame):
    """Single toast notification widget.
    
    A QFrame-based notification with message and icon that supports:
    - Success (green), error (red), info (blue) types
    - Auto-dismiss with QTimer
    - Click-to-dismiss functionality
    - Fade-in/fade-out animations
    
    Requirements: 6.1, 6.2, 6.3, 6.4
    """
    
    dismissed = Signal()
    
    # Toast type colors
    COLORS = {
        "success": {"bg": "#1a472a", "border": "#30D158", "icon": "✓"},
        "error": {"bg": "#4a1a1a", "border": "#FF453A", "icon": "✕"},
        "info": {"bg": "#1a2a4a", "border": "#0A84FF", "icon": "ℹ"},
    }
    
    def __init__(
        self,
        message: str,
        toast_type: str = "info",
        duration_ms: int = 4000,
        parent: Optional[QFrame] = None,
    ) -> None:
        """Initialize toast notification.
        
        Args:
            message: The message to display
            toast_type: Type of toast ("success", "error", "info")
            duration_ms: Auto-dismiss duration in milliseconds
            parent: Parent widget
        """
        super().__init__(parent)
        
        self._message = message
        self._toast_type = toast_type if toast_type in self.COLORS else "info"
        self._duration_ms = duration_ms
        self._dismiss_timer: Optional[QTimer] = None
        self._fade_animation: Optional[QPropertyAnimation] = None
        self._opacity_effect: Optional[QGraphicsOpacityEffect] = None
        
        self._setup_ui()
        self._apply_style()
    
    def _setup_ui(self) -> None:
        """Set up the toast UI components."""
        self.setFixedWidth(320)
        self.setMinimumHeight(50)
        self.setCursor(Qt.PointingHandCursor)
        
        # Set up opacity effect for animations
        self._opacity_effect = QGraphicsOpacityEffect(self)
        self._opacity_effect.setOpacity(0.0)
        self.setGraphicsEffect(self._opacity_effect)
        
        # Layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(10)
        
        # Icon label
        colors = self.COLORS[self._toast_type]
        self._icon_label = QLabel(colors["icon"])
        self._icon_label.setStyleSheet(f"color: {colors['border']}; font-size: 16px;")
        self._icon_label.setFixedWidth(20)
        layout.addWidget(self._icon_label)
        
        # Message label
        self._message_label = QLabel(self._message)
        self._message_label.setWordWrap(True)
        self._message_label.setStyleSheet("color: #E6E6E6; font-size: 11pt;")
        layout.addWidget(self._message_label, 1)
    
    def _apply_style(self) -> None:
        """Apply styling based on toast type."""
        colors = self.COLORS[self._toast_type]
        self.setStyleSheet(f"""
            ToastNotification {{
                background-color: {colors['bg']};
                border: 1px solid {colors['border']};
                border-radius: 8px;
            }}
        """)

    def show_toast(self) -> None:
        """Show the toast with fade-in animation and start auto-dismiss timer."""
        self.show()
        self._fade_in()
        self._start_dismiss_timer()
    
    def dismiss(self) -> None:
        """Dismiss the toast with fade-out animation."""
        # Stop dismiss timer if running
        if self._dismiss_timer:
            self._dismiss_timer.stop()
            self._dismiss_timer = None
        
        self._fade_out()
    
    def _fade_in(self, duration_ms: int = 200) -> None:
        """Fade in the toast notification."""
        if self._fade_animation:
            self._fade_animation.stop()
        
        self._fade_animation = QPropertyAnimation(self._opacity_effect, b"opacity")
        self._fade_animation.setDuration(duration_ms)
        self._fade_animation.setStartValue(0.0)
        self._fade_animation.setEndValue(1.0)
        self._fade_animation.setEasingCurve(QEasingCurve.OutQuad)
        self._fade_animation.start()
    
    def _fade_out(self, duration_ms: int = 200) -> None:
        """Fade out the toast notification and emit dismissed signal."""
        if self._fade_animation:
            self._fade_animation.stop()
        
        self._fade_animation = QPropertyAnimation(self._opacity_effect, b"opacity")
        self._fade_animation.setDuration(duration_ms)
        self._fade_animation.setStartValue(self._opacity_effect.opacity())
        self._fade_animation.setEndValue(0.0)
        self._fade_animation.setEasingCurve(QEasingCurve.InQuad)
        self._fade_animation.finished.connect(self._on_fade_out_finished)
        self._fade_animation.start()
    
    def _on_fade_out_finished(self) -> None:
        """Handle fade out completion."""
        self.hide()
        # Remove graphics effect to prevent QPainter errors
        self.setGraphicsEffect(None)
        self._opacity_effect = None
        self.dismissed.emit()
    
    def _start_dismiss_timer(self) -> None:
        """Start the auto-dismiss timer."""
        if self._dismiss_timer:
            self._dismiss_timer.stop()
        
        self._dismiss_timer = QTimer(self)
        self._dismiss_timer.setSingleShot(True)
        self._dismiss_timer.timeout.connect(self.dismiss)
        self._dismiss_timer.start(self._duration_ms)
    
    def mousePressEvent(self, event) -> None:
        """Handle click to dismiss."""
        self.dismiss()
        event.accept()
    
    @property
    def toast_type(self) -> str:
        """Get the toast type."""
        return self._toast_type
    
    @property
    def message(self) -> str:
        """Get the toast message."""
        return self._message


class ToastManager:
    """Manages toast notification display and stacking.
    
    Provides methods to show success, error, and info toasts,
    handles vertical stacking of multiple notifications,
    and cleans up dismissed notifications.
    
    Requirements: 6.1, 6.2, 6.3, 6.4
    """
    
    # Spacing between stacked toasts
    TOAST_SPACING = 10
    # Margin from screen edge
    MARGIN_RIGHT = 20
    MARGIN_TOP = 20
    
    def __init__(self, parent_widget: QFrame) -> None:
        """Initialize the toast manager.
        
        Args:
            parent_widget: The parent widget where toasts will be displayed
        """
        self._parent = parent_widget
        self._active_toasts: list[ToastNotification] = []
    
    def show_success(self, message: str, duration_ms: int = 4000) -> None:
        """Show a success toast notification.
        
        Args:
            message: The success message to display
            duration_ms: Auto-dismiss duration in milliseconds
        """
        self._show_toast(message, "success", duration_ms)
    
    def show_error(self, message: str, duration_ms: int = 4000) -> None:
        """Show an error toast notification.
        
        Args:
            message: The error message to display
            duration_ms: Auto-dismiss duration in milliseconds
        """
        self._show_toast(message, "error", duration_ms)
    
    def show_info(self, message: str, duration_ms: int = 4000) -> None:
        """Show an info toast notification.
        
        Args:
            message: The info message to display
            duration_ms: Auto-dismiss duration in milliseconds
        """
        self._show_toast(message, "info", duration_ms)
    
    def _show_toast(self, message: str, toast_type: str, duration_ms: int) -> None:
        """Create and show a toast notification.
        
        Args:
            message: The message to display
            toast_type: Type of toast ("success", "error", "info")
            duration_ms: Auto-dismiss duration in milliseconds
        """
        toast = ToastNotification(
            message=message,
            toast_type=toast_type,
            duration_ms=duration_ms,
            parent=self._parent,
        )
        
        # Connect dismissed signal to cleanup
        toast.dismissed.connect(lambda: self._on_toast_dismissed(toast))
        
        # Add to active toasts
        self._active_toasts.append(toast)
        
        # Position the toast
        self._position_toast(toast)
        
        # Show with animation
        toast.show_toast()
    
    def _position_toast(self, toast: ToastNotification) -> None:
        """Position a toast notification in the stack.
        
        Args:
            toast: The toast to position
        """
        parent_rect = self._parent.rect()
        
        # Calculate x position (right-aligned)
        x = parent_rect.width() - toast.width() - self.MARGIN_RIGHT
        
        # Calculate y position (stacked from top)
        y = self.MARGIN_TOP
        for active_toast in self._active_toasts:
            if active_toast is not toast and active_toast.isVisible():
                y += active_toast.height() + self.TOAST_SPACING
        
        toast.move(x, y)
    
    def _on_toast_dismissed(self, toast: ToastNotification) -> None:
        """Handle toast dismissal and cleanup.
        
        Args:
            toast: The dismissed toast
        """
        if toast in self._active_toasts:
            self._active_toasts.remove(toast)
        
        # Reposition remaining toasts
        self._reposition_all_toasts()
        
        # Schedule deletion
        toast.deleteLater()
    
    def _reposition_all_toasts(self) -> None:
        """Reposition all active toasts after one is dismissed."""
        parent_rect = self._parent.rect()
        x = parent_rect.width() - 320 - self.MARGIN_RIGHT  # Toast width is 320
        y = self.MARGIN_TOP
        
        for toast in self._active_toasts:
            if toast.isVisible():
                toast.move(x, y)
                y += toast.height() + self.TOAST_SPACING
    
    def dismiss_all(self) -> None:
        """Dismiss all active toast notifications."""
        for toast in list(self._active_toasts):
            toast.dismiss()
    
    @property
    def active_count(self) -> int:
        """Get the number of active toast notifications."""
        return len(self._active_toasts)
