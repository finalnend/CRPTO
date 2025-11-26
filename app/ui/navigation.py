"""Navigation components for sidebar-based page navigation.

Provides:
- PageType enum for identifying different pages
- NavigationState dataclass for tracking navigation state
- NavigationSidebar widget for icon-based page selection
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict

from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QIcon, QColor
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QPushButton,
    QSizePolicy,
)


class PageType(Enum):
    """Enumeration of available pages in the application.
    
    Each page type corresponds to a distinct functional area.
    """
    MARKET_OVERVIEW = "market"
    PAPER_TRADING = "trading"
    CHART_ANALYSIS = "chart"
    SETTINGS = "settings"


@dataclass
class NavigationState:
    """Tracks the current navigation state.
    
    Attributes:
        current_page: The currently displayed page
        previous_page: The previously displayed page (for back navigation)
        is_transitioning: Whether a page transition animation is in progress
    """
    current_page: PageType
    previous_page: Optional[PageType] = None
    is_transitioning: bool = False


# Page metadata for UI display
PAGE_METADATA: Dict[PageType, Dict[str, str]] = {
    PageType.MARKET_OVERVIEW: {
        "icon": "📊",
        "label": "Market Overview",
        "tooltip": "View cryptocurrency prices and charts",
    },
    PageType.PAPER_TRADING: {
        "icon": "💹",
        "label": "Paper Trading",
        "tooltip": "Practice trading with virtual funds",
    },
    PageType.CHART_ANALYSIS: {
        "icon": "📈",
        "label": "Chart Analysis",
        "tooltip": "Detailed technical analysis charts",
    },
    PageType.SETTINGS: {
        "icon": "⚙️",
        "label": "Settings",
        "tooltip": "Configure application preferences",
    },
}


class NavigationButton(QPushButton):
    """A navigation button with icon and optional label."""
    
    # Size constants
    COLLAPSED_SIZE = (48, 48)
    EXPANDED_SIZE = (148, 48)
    
    def __init__(
        self,
        page_type: PageType,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._page_type = page_type
        self._is_selected = False
        self._collapsed = True  # Start collapsed (icon-only)
        
        metadata = PAGE_METADATA[page_type]
        self._icon_text = metadata["icon"]
        self._label_text = metadata["label"]
        self.setText(self._icon_text)
        self.setToolTip(metadata["tooltip"])
        
        self.setFixedSize(*self.COLLAPSED_SIZE)
        self.setCursor(Qt.PointingHandCursor)
        self._update_style()
    
    @property
    def page_type(self) -> PageType:
        """Get the page type this button represents."""
        return self._page_type
    
    def set_selected(self, selected: bool) -> None:
        """Set the selected state of the button.
        
        Args:
            selected: Whether this button should appear selected
        """
        self._is_selected = selected
        self._update_style()
    
    def is_selected(self) -> bool:
        """Check if this button is currently selected."""
        return self._is_selected
    
    def set_collapsed(self, collapsed: bool) -> None:
        """Set the collapsed state of the button.
        
        When collapsed, shows only the icon.
        When expanded, shows icon with label.
        
        Args:
            collapsed: True for icon-only, False for icon with label
        """
        if self._collapsed == collapsed:
            return
        
        self._collapsed = collapsed
        
        if collapsed:
            self.setText(self._icon_text)
            self.setFixedSize(*self.COLLAPSED_SIZE)
        else:
            self.setText(f"{self._icon_text}  {self._label_text}")
            self.setFixedSize(*self.EXPANDED_SIZE)
        
        self._update_style()
    
    def _update_style(self) -> None:
        """Update button styling based on selection and collapsed state."""
        # Text alignment based on collapsed state
        text_align = "center" if self._collapsed else "left"
        padding = "0px" if self._collapsed else "0px 12px"
        
        if self._is_selected:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: #0A84FF;
                    border: none;
                    border-radius: 8px;
                    font-size: 16px;
                    color: white;
                    text-align: {text_align};
                    padding: {padding};
                }}
                QPushButton:hover {{
                    background-color: #0A84FF;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    border: none;
                    border-radius: 8px;
                    font-size: 16px;
                    color: #cccccc;
                    text-align: {text_align};
                    padding: {padding};
                }}
                QPushButton:hover {{
                    background-color: rgba(255, 255, 255, 0.1);
                }}
            """)


class NavigationSidebar(QWidget):
    """Vertical icon-based navigation sidebar.
    
    Displays navigation buttons for each page type and emits signals
    when a page is selected. Supports collapsed mode for responsive layouts.
    
    Signals:
        pageSelected: Emitted when a navigation button is clicked
    """
    
    # Width constants for responsive behavior
    EXPANDED_WIDTH = 160
    COLLAPSED_WIDTH = 60
    
    pageSelected = Signal(PageType)
    
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        
        self._buttons: Dict[PageType, NavigationButton] = {}
        self._current_page: PageType = PageType.MARKET_OVERVIEW
        self._collapsed: bool = False
        
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        """Set up the sidebar UI."""
        self.setFixedWidth(self.COLLAPSED_WIDTH)
        self.setStyleSheet("""
            NavigationSidebar {
                background-color: #1a1a1a;
                border-right: 1px solid #2a2a2a;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 12, 6, 12)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignTop)
        
        # Create buttons for each page type
        for page_type in PageType:
            button = NavigationButton(page_type, self)
            button.clicked.connect(lambda checked, pt=page_type: self._on_button_clicked(pt))
            self._buttons[page_type] = button
            layout.addWidget(button)
        
        # Add stretch to push buttons to top
        layout.addStretch()
        
        # Set initial selection
        self._buttons[self._current_page].set_selected(True)
    
    def _on_button_clicked(self, page_type: PageType) -> None:
        """Handle navigation button click.
        
        Args:
            page_type: The page type that was clicked
        """
        if page_type != self._current_page:
            self.set_current_page(page_type)
            self.pageSelected.emit(page_type)
    
    def set_current_page(self, page: PageType) -> None:
        """Set the currently active page (updates highlight).
        
        Args:
            page: The page to set as current
        """
        # Deselect previous button
        if self._current_page in self._buttons:
            self._buttons[self._current_page].set_selected(False)
        
        # Select new button
        self._current_page = page
        if page in self._buttons:
            self._buttons[page].set_selected(True)
    
    def get_current_page(self) -> PageType:
        """Get the currently selected page.
        
        Returns:
            The currently selected PageType
        """
        return self._current_page
    
    def set_collapsed(self, collapsed: bool) -> None:
        """Set the collapsed state of the sidebar.
        
        When collapsed, the sidebar shows only icons (no labels).
        When expanded, the sidebar shows icons with labels.
        
        Args:
            collapsed: True to collapse, False to expand
        """
        if self._collapsed == collapsed:
            return
        
        self._collapsed = collapsed
        
        # Update sidebar width
        if collapsed:
            self.setFixedWidth(self.COLLAPSED_WIDTH)
        else:
            self.setFixedWidth(self.EXPANDED_WIDTH)
        
        # Update button display mode
        for button in self._buttons.values():
            button.set_collapsed(collapsed)
    
    def is_collapsed(self) -> bool:
        """Check if the sidebar is currently collapsed.
        
        Returns:
            True if collapsed, False if expanded
        """
        return self._collapsed
    
    def get_width(self) -> int:
        """Get the current sidebar width.
        
        Returns:
            Current width in pixels
        """
        return self.COLLAPSED_WIDTH if self._collapsed else self.EXPANDED_WIDTH
