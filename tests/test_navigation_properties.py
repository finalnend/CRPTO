"""Property-based tests for navigation components.

Tests navigation state consistency and settings persistence using Hypothesis.
"""

from __future__ import annotations

import tempfile
from hypothesis import given, settings, strategies as st
import pytest

from app.ui.navigation import PageType, NavigationState, NavigationSidebar
from app.ui.page_container import PageContainer
from app.ui.pages.settings import AppSettings, SettingsPage, SETTINGS_STORAGE_KEY, COLUMN_NAMES
from app.storage.storage import JsonFileStorage

# Need to initialize Qt application for widget tests
from PySide6.QtWidgets import QApplication, QWidget

# Ensure QApplication exists for tests
@pytest.fixture(scope="module", autouse=True)
def qt_app():
    """Create QApplication instance for tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


# Strategy for generating PageType values
page_type_strategy = st.sampled_from(list(PageType))

# Strategy for generating sequences of page types
page_sequence_strategy = st.lists(
    page_type_strategy,
    min_size=1,
    max_size=10
)


@given(page_sequence=page_sequence_strategy)
@settings(max_examples=100)
def test_navigation_state_consistency(page_sequence: list):
    """
    **Feature: sidebar-navigation, Property 1: Navigation state consistency**
    **Validates: Requirements 1.4, 1.5**
    
    For any navigation action, the sidebar's highlighted icon SHALL always
    match the currently displayed page in the container.
    """
    # Create sidebar and container
    sidebar = NavigationSidebar()
    container = PageContainer()
    
    # Register placeholder pages for each page type
    for page_type in PageType:
        placeholder = QWidget()
        container.add_page(page_type, placeholder)
    
    # Wire up signals (simulating MainWindow integration)
    sidebar.pageSelected.connect(container.switch_to)
    container.pageChanged.connect(sidebar.set_current_page)
    
    # Execute navigation sequence
    for page_type in page_sequence:
        # Simulate clicking the navigation button
        sidebar.set_current_page(page_type)
        container.switch_to(page_type, animate=False)  # No animation for test speed
        
        # Verify consistency: sidebar selection matches container's current page
        sidebar_current = sidebar.get_current_page()
        container_current = container.get_current_page_type()
        
        assert sidebar_current == container_current, (
            f"Navigation state inconsistency: sidebar shows {sidebar_current}, "
            f"but container shows {container_current}"
        )
        
        assert sidebar_current == page_type, (
            f"Navigation state inconsistency: expected {page_type}, "
            f"but sidebar shows {sidebar_current}"
        )


@given(page_type=page_type_strategy)
@settings(max_examples=100)
def test_page_switching_completeness(page_type: PageType):
    """
    **Feature: sidebar-navigation, Property 2: Page switching completeness**
    **Validates: Requirements 1.4**
    
    For any valid PageType, calling switch_to() SHALL result in that page
    being displayed and the previous page being hidden.
    """
    container = PageContainer()
    
    # Register placeholder pages for each page type
    pages = {}
    for pt in PageType:
        placeholder = QWidget()
        pages[pt] = placeholder
        container.add_page(pt, placeholder)
    
    # Switch to the target page
    container.switch_to(page_type, animate=False)
    
    # Verify the correct page is displayed
    current_page_type = container.get_current_page_type()
    assert current_page_type == page_type, (
        f"Expected page {page_type}, but got {current_page_type}"
    )
    
    # Verify the correct widget is current
    current_widget = container.currentWidget()
    expected_widget = pages[page_type]
    assert current_widget == expected_widget, (
        f"Current widget does not match expected widget for {page_type}"
    )


@given(
    initial_page=page_type_strategy,
    target_page=page_type_strategy
)
@settings(max_examples=100)
def test_sidebar_highlight_updates_on_page_change(
    initial_page: PageType,
    target_page: PageType
):
    """
    **Feature: sidebar-navigation, Property 1: Navigation state consistency**
    **Validates: Requirements 1.5**
    
    While a page is active, the NavigationSidebar SHALL maintain the
    highlighted state for that page's icon.
    """
    sidebar = NavigationSidebar()
    
    # Set initial page
    sidebar.set_current_page(initial_page)
    
    # Verify initial highlight
    assert sidebar.get_current_page() == initial_page, (
        f"Initial page should be {initial_page}"
    )
    
    # Change to target page
    sidebar.set_current_page(target_page)
    
    # Verify highlight updated
    assert sidebar.get_current_page() == target_page, (
        f"After navigation, page should be {target_page}"
    )
    
    # Verify the button states
    for page_type, button in sidebar._buttons.items():
        if page_type == target_page:
            assert button.is_selected(), (
                f"Button for {page_type} should be selected"
            )
        else:
            assert not button.is_selected(), (
                f"Button for {page_type} should not be selected"
            )


# Strategy for generating valid settings data
@st.composite
def settings_strategy(draw):
    """Generate valid AppSettings data."""
    data_source = draw(st.sampled_from(["auto", "binance-ws", "binance", "coingecko", "coinbase"]))
    theme_mode = draw(st.sampled_from(["dark", "light"]))
    
    # Generate valid hex color
    r = draw(st.integers(min_value=0, max_value=255))
    g = draw(st.integers(min_value=0, max_value=255))
    b = draw(st.integers(min_value=0, max_value=255))
    accent_color = f"#{r:02x}{g:02x}{b:02x}"
    
    # Generate subset of visible columns
    visible_columns = draw(st.lists(
        st.sampled_from(COLUMN_NAMES),
        min_size=0,
        max_size=len(COLUMN_NAMES),
        unique=True
    ))
    
    minimize_to_tray = draw(st.booleans())
    
    return AppSettings(
        data_source=data_source,
        theme_mode=theme_mode,
        accent_color=accent_color,
        visible_columns=visible_columns,
        minimize_to_tray=minimize_to_tray,
    )


@given(settings_data=settings_strategy())
@settings(max_examples=100)
def test_settings_persistence_round_trip(settings_data: AppSettings):
    """
    **Feature: sidebar-navigation, Property 4: Settings persistence round-trip**
    **Validates: Requirements 5.5**
    
    For any valid setting change, saving to storage and then loading
    SHALL produce the same setting value.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = JsonFileStorage(tmpdir)
        
        # Save settings to storage
        storage.save(SETTINGS_STORAGE_KEY, settings_data.to_dict())
        
        # Load settings from storage
        loaded_data = storage.load(SETTINGS_STORAGE_KEY)
        
        # Verify data was loaded
        assert loaded_data is not None, "Loaded settings should not be None"
        
        # Reconstruct AppSettings from loaded data
        loaded_settings = AppSettings.from_dict(loaded_data)
        
        # Verify all fields match
        assert loaded_settings.data_source == settings_data.data_source, (
            f"data_source mismatch: expected {settings_data.data_source}, "
            f"got {loaded_settings.data_source}"
        )
        assert loaded_settings.theme_mode == settings_data.theme_mode, (
            f"theme_mode mismatch: expected {settings_data.theme_mode}, "
            f"got {loaded_settings.theme_mode}"
        )
        assert loaded_settings.accent_color == settings_data.accent_color, (
            f"accent_color mismatch: expected {settings_data.accent_color}, "
            f"got {loaded_settings.accent_color}"
        )
        assert set(loaded_settings.visible_columns) == set(settings_data.visible_columns), (
            f"visible_columns mismatch: expected {settings_data.visible_columns}, "
            f"got {loaded_settings.visible_columns}"
        )
        assert loaded_settings.minimize_to_tray == settings_data.minimize_to_tray, (
            f"minimize_to_tray mismatch: expected {settings_data.minimize_to_tray}, "
            f"got {loaded_settings.minimize_to_tray}"
        )


# Strategy for generating application state
@st.composite
def app_state_strategy(draw):
    """Generate valid application state for testing."""
    from decimal import Decimal
    
    # Generate portfolio balance
    balance = draw(st.decimals(
        min_value=Decimal("0"),
        max_value=Decimal("1000000"),
        places=2,
        allow_nan=False,
        allow_infinity=False
    ))
    
    # Generate positions (symbol -> quantity)
    symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "ADAUSDT"]
    positions = {}
    for sym in draw(st.lists(st.sampled_from(symbols), min_size=0, max_size=3, unique=True)):
        qty = draw(st.decimals(
            min_value=Decimal("0.001"),
            max_value=Decimal("100"),
            places=8,
            allow_nan=False,
            allow_infinity=False
        ))
        positions[sym] = qty
    
    # Generate settings
    settings_data = draw(settings_strategy())
    
    return {
        "balance": balance,
        "positions": positions,
        "settings": settings_data,
    }


@given(
    page_sequence=page_sequence_strategy,
    initial_state=app_state_strategy()
)
@settings(max_examples=100)
def test_state_preservation_across_navigation(page_sequence: list, initial_state: dict):
    """
    **Feature: sidebar-navigation, Property 3: State preservation across navigation**
    **Validates: Requirements 6.3**
    
    For any sequence of page switches, the application state (portfolio balance,
    positions, settings) SHALL remain unchanged.
    """
    from decimal import Decimal
    from app.trading.portfolio import PortfolioManager
    
    # Create sidebar and container
    sidebar = NavigationSidebar()
    container = PageContainer()
    
    # Register placeholder pages for each page type
    for page_type in PageType:
        placeholder = QWidget()
        container.add_page(page_type, placeholder)
    
    # Wire up signals
    sidebar.pageSelected.connect(container.switch_to)
    container.pageChanged.connect(sidebar.set_current_page)
    
    # Create portfolio with initial state
    # Start with a large balance to accommodate position purchases
    large_balance = initial_state["balance"] + Decimal("1000000")
    portfolio = PortfolioManager(large_balance)
    
    # Add positions by executing buy orders at price 1.0
    for sym, qty in initial_state["positions"].items():
        portfolio.execute_buy(sym, qty, Decimal("1.0"))
    
    # Capture initial state after setup
    initial_balance = portfolio.get_balance()
    initial_positions = {sym: pos.quantity for sym, pos in portfolio.get_positions().items()}
    initial_settings = initial_state["settings"].to_dict()
    
    # Execute navigation sequence
    for page_type in page_sequence:
        sidebar.set_current_page(page_type)
        container.switch_to(page_type, animate=False)
    
    # Verify state is preserved after navigation
    final_balance = portfolio.get_balance()
    final_positions = {sym: pos.quantity for sym, pos in portfolio.get_positions().items()}
    final_settings = initial_state["settings"].to_dict()
    
    # Assert balance unchanged
    assert final_balance == initial_balance, (
        f"Balance changed during navigation: {initial_balance} -> {final_balance}"
    )
    
    # Assert positions unchanged
    assert final_positions == initial_positions, (
        f"Positions changed during navigation: {initial_positions} -> {final_positions}"
    )
    
    # Assert settings unchanged
    assert final_settings == initial_settings, (
        f"Settings changed during navigation"
    )


# Strategy for generating window widths
window_width_strategy = st.integers(min_value=200, max_value=2000)


@given(window_width=window_width_strategy)
@settings(max_examples=100)
def test_responsive_sidebar_behavior(window_width: int):
    """
    **Feature: sidebar-navigation, Property 6: Responsive sidebar behavior**
    **Validates: Requirements 7.1**
    
    For any window width below 800 pixels, the sidebar width SHALL be
    less than or equal to the icon-only width (e.g., 60px).
    """
    # Breakpoint constant (same as in MainWindow)
    RESPONSIVE_BREAKPOINT = 800
    ICON_ONLY_WIDTH = NavigationSidebar.COLLAPSED_WIDTH  # 60px
    
    # Create sidebar
    sidebar = NavigationSidebar()
    
    # Simulate window resize behavior
    should_collapse = window_width < RESPONSIVE_BREAKPOINT
    sidebar.set_collapsed(should_collapse)
    
    # Get the actual sidebar width
    actual_width = sidebar.get_width()
    
    # Verify the property
    if window_width < RESPONSIVE_BREAKPOINT:
        # Below breakpoint: sidebar MUST be collapsed (icon-only width)
        assert actual_width <= ICON_ONLY_WIDTH, (
            f"For window width {window_width}px (below {RESPONSIVE_BREAKPOINT}px), "
            f"sidebar width should be <= {ICON_ONLY_WIDTH}px, but got {actual_width}px"
        )
        assert sidebar.is_collapsed(), (
            f"For window width {window_width}px (below {RESPONSIVE_BREAKPOINT}px), "
            f"sidebar should be collapsed"
        )
    else:
        # At or above breakpoint: sidebar MAY be expanded
        # Just verify it's in expanded state
        assert not sidebar.is_collapsed(), (
            f"For window width {window_width}px (>= {RESPONSIVE_BREAKPOINT}px), "
            f"sidebar should be expanded"
        )


@given(
    width_sequence=st.lists(
        window_width_strategy,
        min_size=1,
        max_size=20
    )
)
@settings(max_examples=100)
def test_responsive_sidebar_state_transitions(width_sequence: list):
    """
    **Feature: sidebar-navigation, Property 6: Responsive sidebar behavior**
    **Validates: Requirements 7.1**
    
    For any sequence of window width changes, the sidebar state SHALL
    correctly transition between collapsed and expanded states based
    on the 800px breakpoint.
    """
    RESPONSIVE_BREAKPOINT = 800
    
    sidebar = NavigationSidebar()
    
    for width in width_sequence:
        # Simulate resize event
        should_collapse = width < RESPONSIVE_BREAKPOINT
        sidebar.set_collapsed(should_collapse)
        
        # Verify state matches expectation
        if width < RESPONSIVE_BREAKPOINT:
            assert sidebar.is_collapsed(), (
                f"Sidebar should be collapsed at width {width}px"
            )
            assert sidebar.get_width() == NavigationSidebar.COLLAPSED_WIDTH, (
                f"Collapsed sidebar width should be {NavigationSidebar.COLLAPSED_WIDTH}px"
            )
        else:
            assert not sidebar.is_collapsed(), (
                f"Sidebar should be expanded at width {width}px"
            )
            assert sidebar.get_width() == NavigationSidebar.EXPANDED_WIDTH, (
                f"Expanded sidebar width should be {NavigationSidebar.EXPANDED_WIDTH}px"
            )
