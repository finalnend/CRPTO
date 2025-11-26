"""Page container widget with transition animations.

Provides a QStackedWidget-based container for managing page widgets
with smooth fade transition animations between pages.
"""

from __future__ import annotations

from typing import Optional, Dict

from PySide6.QtCore import Signal, QPropertyAnimation, QEasingCurve
from PySide6.QtWidgets import (
    QStackedWidget,
    QWidget,
    QGraphicsOpacityEffect,
)

from app.ui.navigation import PageType


class PageContainer(QStackedWidget):
    """Container for page widgets with transition animations.
    
    Manages multiple page widgets and provides smooth fade transitions
    when switching between pages.
    
    Signals:
        pageChanged: Emitted when the current page changes
    """
    
    pageChanged = Signal(PageType)
    
    # Animation duration in milliseconds (Requirements 6.1, 6.2: 150ms)
    FADE_DURATION_MS = 150
    
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        
        self._pages: Dict[PageType, QWidget] = {}
        self._current_page_type: Optional[PageType] = None
        self._fade_out_anim: Optional[QPropertyAnimation] = None
        self._fade_in_anim: Optional[QPropertyAnimation] = None
        self._is_transitioning: bool = False
        self._pending_page: Optional[PageType] = None
    
    def add_page(self, page_type: PageType, widget: QWidget) -> None:
        """Register a page widget.
        
        Args:
            page_type: The type of page being registered
            widget: The widget to display for this page
        """
        if page_type in self._pages:
            # Remove existing page
            old_widget = self._pages[page_type]
            self.removeWidget(old_widget)
        
        self._pages[page_type] = widget
        self.addWidget(widget)
        
        # Don't apply graphics effect during add - apply only during animation
        # This prevents QPainter errors when widgets are not visible
        
        # Set first added page as current
        if self._current_page_type is None:
            self._current_page_type = page_type
            self.setCurrentWidget(widget)
    
    def switch_to(self, page_type: PageType, animate: bool = True) -> None:
        """Switch to the specified page with optional animation.
        
        Args:
            page_type: The page to switch to
            animate: Whether to animate the transition (default: True)
        """
        if page_type not in self._pages:
            return
        
        if page_type == self._current_page_type:
            return
        
        # Handle animation interruption (Requirements 6.4)
        if self._is_transitioning:
            self._cancel_animations()
            self._pending_page = page_type
            self._complete_transition_immediately()
            return
        
        target_widget = self._pages[page_type]
        
        if animate and self._current_page_type is not None:
            self._animate_transition(page_type, target_widget)
        else:
            self._switch_immediately(page_type, target_widget)
    
    def _switch_immediately(self, page_type: PageType, widget: QWidget) -> None:
        """Switch to a page without animation.
        
        Args:
            page_type: The page type to switch to
            widget: The widget to display
        """
        self._current_page_type = page_type
        
        # Remove any graphics effect to prevent QPainter errors
        widget.setGraphicsEffect(None)
        
        self.setCurrentWidget(widget)
        self.pageChanged.emit(page_type)
    
    def _animate_transition(self, page_type: PageType, target_widget: QWidget) -> None:
        """Animate the transition between pages.
        
        Args:
            page_type: The target page type
            target_widget: The widget to transition to
        """
        self._is_transitioning = True
        self._pending_page = page_type
        
        current_widget = self._pages.get(self._current_page_type)
        
        if current_widget:
            # Fade out current page
            self._fade_out_anim = self._create_fade_animation(
                current_widget, 1.0, 0.0
            )
            self._fade_out_anim.finished.connect(
                lambda: self._on_fade_out_complete(page_type, target_widget)
            )
            self._fade_out_anim.start()
        else:
            # No current page, just fade in
            self._start_fade_in(page_type, target_widget)
    
    def _on_fade_out_complete(self, page_type: PageType, target_widget: QWidget) -> None:
        """Handle fade out animation completion.
        
        Args:
            page_type: The target page type
            target_widget: The widget to transition to
        """
        # Remove graphics effect from the old widget
        if self._current_page_type is not None:
            old_widget = self._pages.get(self._current_page_type)
            if old_widget:
                old_widget.setGraphicsEffect(None)
        
        # Check if a different page was requested during animation
        if self._pending_page != page_type:
            page_type = self._pending_page
            target_widget = self._pages.get(page_type)
            if target_widget is None:
                self._is_transitioning = False
                return
        
        self._start_fade_in(page_type, target_widget)
    
    def _start_fade_in(self, page_type: PageType, target_widget: QWidget) -> None:
        """Start the fade in animation for the target page.
        
        Args:
            page_type: The target page type
            target_widget: The widget to fade in
        """
        # Set target widget opacity to 0 before showing
        effect = target_widget.graphicsEffect()
        if isinstance(effect, QGraphicsOpacityEffect):
            effect.setOpacity(0.0)
        
        # Switch to target widget
        self._current_page_type = page_type
        self.setCurrentWidget(target_widget)
        
        # Fade in target page
        self._fade_in_anim = self._create_fade_animation(
            target_widget, 0.0, 1.0
        )
        self._fade_in_anim.finished.connect(self._on_fade_in_complete)
        self._fade_in_anim.start()
        
        self.pageChanged.emit(page_type)
    
    def _on_fade_in_complete(self) -> None:
        """Handle fade in animation completion."""
        self._is_transitioning = False
        self._pending_page = None
        
        # Remove graphics effect after animation to prevent QPainter errors
        if self._current_page_type is not None:
            current_widget = self._pages.get(self._current_page_type)
            if current_widget:
                current_widget.setGraphicsEffect(None)
    
    def _create_fade_animation(
        self,
        widget: QWidget,
        start_opacity: float,
        end_opacity: float,
    ) -> QPropertyAnimation:
        """Create a fade animation for a widget.
        
        Args:
            widget: The widget to animate
            start_opacity: Starting opacity (0.0-1.0)
            end_opacity: Ending opacity (0.0-1.0)
            
        Returns:
            The configured animation object
        """
        effect = widget.graphicsEffect()
        if not isinstance(effect, QGraphicsOpacityEffect):
            effect = QGraphicsOpacityEffect(widget)
            widget.setGraphicsEffect(effect)
        
        anim = QPropertyAnimation(effect, b"opacity")
        anim.setDuration(self.FADE_DURATION_MS)
        anim.setStartValue(start_opacity)
        anim.setEndValue(end_opacity)
        anim.setEasingCurve(QEasingCurve.InOutQuad)
        
        return anim
    
    def _cancel_animations(self) -> None:
        """Cancel any running animations."""
        if self._fade_out_anim and self._fade_out_anim.state() == QPropertyAnimation.Running:
            self._fade_out_anim.stop()
            self._fade_out_anim = None
        
        if self._fade_in_anim and self._fade_in_anim.state() == QPropertyAnimation.Running:
            self._fade_in_anim.stop()
            self._fade_in_anim = None
    
    def _complete_transition_immediately(self) -> None:
        """Complete the transition to the pending page immediately."""
        if self._pending_page is None:
            self._is_transitioning = False
            return
        
        target_widget = self._pages.get(self._pending_page)
        if target_widget:
            # Remove all graphics effects to prevent QPainter errors
            for widget in self._pages.values():
                widget.setGraphicsEffect(None)
            
            self._switch_immediately(self._pending_page, target_widget)
        
        self._is_transitioning = False
        self._pending_page = None
    
    def get_current_page_type(self) -> Optional[PageType]:
        """Get the current page type.
        
        Returns:
            The currently displayed PageType, or None if no page is set
        """
        return self._current_page_type
    
    def get_page(self, page_type: PageType) -> Optional[QWidget]:
        """Get the widget for a specific page type.
        
        Args:
            page_type: The page type to get
            
        Returns:
            The widget for the page, or None if not registered
        """
        return self._pages.get(page_type)
    
    def is_transitioning(self) -> bool:
        """Check if a page transition is in progress.
        
        Returns:
            True if a transition animation is running
        """
        return self._is_transitioning
    
    def notify_width_changed(self, width: int) -> None:
        """Notify all pages of a width change for responsive adjustments.
        
        Implements Requirements 7.3, 7.4: Adjust page layouts based on
        available width.
        
        Args:
            width: The new available width in pixels
        """
        for page in self._pages.values():
            if hasattr(page, 'on_container_width_changed'):
                page.on_container_width_changed(width)
