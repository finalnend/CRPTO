"""Property-based tests for position quick actions.

Tests the position quick actions correctness properties using Hypothesis.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from hypothesis import given, settings, strategies as st, assume

from app.ui.paper_trading import PortfolioView


# Strategies for generating valid test data
positive_quantity_strategy = st.decimals(
    min_value=Decimal("0.001"),
    max_value=Decimal("1000"),
    places=8,
    allow_nan=False,
    allow_infinity=False
)

pnl_strategy = st.decimals(
    min_value=Decimal("-100000"),
    max_value=Decimal("100000"),
    places=2,
    allow_nan=False,
    allow_infinity=False
)

symbol_strategy = st.sampled_from(["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "ADAUSDT"])


@given(unrealized_pnl=pnl_strategy)
@settings(max_examples=100)
def test_close_button_color_by_pnl(unrealized_pnl: Decimal):
    """
    **Feature: ui-ux-convenience, Property 10: Close Button Color by P&L**
    **Validates: Requirements 7.4**
    
    For any position with unrealized P&L > 0, the Close button SHALL be green;
    for any position with unrealized P&L < 0, the Close button SHALL be red.
    """
    color = PortfolioView.get_close_button_color(unrealized_pnl)
    
    if unrealized_pnl > Decimal("0"):
        assert color == "#28A745", f"Expected green (#28A745) for profit, got {color}"
    elif unrealized_pnl < Decimal("0"):
        assert color == "#DC3545", f"Expected red (#DC3545) for loss, got {color}"
    else:
        # Break-even case - should be gray
        assert color == "#6c757d", f"Expected gray (#6c757d) for break-even, got {color}"


class MockDataProvider:
    """Mock data provider for testing."""
    
    def __init__(self, prices: dict = None):
        self._prices = prices or {}
        self._connected = True
    
    def get_current_price(self, symbol: str) -> Decimal | None:
        return self._prices.get(symbol)
    
    def is_connected(self) -> bool:
        return self._connected


class MockPortfolioManager:
    """Mock portfolio manager for testing."""
    
    def __init__(self, balance: Decimal = Decimal("10000"), positions: dict = None):
        self._balance = balance
        self._positions = positions or {}
    
    def get_balance(self) -> Decimal:
        return self._balance
    
    def get_positions(self) -> dict:
        return self._positions.copy()
    
    def get_position(self, symbol: str):
        return self._positions.get(symbol)
    
    def get_unrealized_pnl(self, symbol: str, current_price: Decimal) -> Decimal:
        position = self._positions.get(symbol)
        if position is None:
            return Decimal("0")
        current_value = position.quantity * current_price
        cost_basis = position.total_cost
        return current_value - cost_basis


class MockPosition:
    """Mock position for testing."""
    
    def __init__(self, symbol: str, quantity: Decimal, average_cost: Decimal):
        self.symbol = symbol
        self.quantity = quantity
        self.average_cost = average_cost
    
    @property
    def total_cost(self) -> Decimal:
        return self.quantity * self.average_cost


@given(
    symbol=symbol_strategy,
    quantity=positive_quantity_strategy
)
@settings(max_examples=100)
def test_close_position_prefill(symbol: str, quantity: Decimal):
    """
    **Feature: ui-ux-convenience, Property 9: Close Position Pre-fill**
    **Validates: Requirements 7.2**
    
    For any position with symbol S and quantity Q, clicking the Close button
    SHALL pre-fill the order form with symbol=S, order_type=SELL, and quantity=Q.
    """
    # This test verifies the signal emission and data passing
    # We test that the closePositionRequested signal carries the correct data
    
    average_cost = Decimal("100")
    position = MockPosition(symbol, quantity, average_cost)
    current_price = average_cost  # Break-even for simplicity
    
    # Create mock portfolio with the position
    mock_portfolio = MockPortfolioManager(
        positions={symbol: position}
    )
    mock_data_provider = MockDataProvider(
        prices={symbol: current_price}
    )
    
    # Track signal emissions
    signal_data = []
    
    # Create PortfolioView (requires Qt app context)
    try:
        from PySide6.QtWidgets import QApplication
        import sys
        
        # Create app if not exists
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)
        
        portfolio_view = PortfolioView(mock_portfolio, mock_data_provider)
        
        # Connect to signal to capture emitted data
        portfolio_view.closePositionRequested.connect(
            lambda s, q: signal_data.append((s, q))
        )
        
        # Simulate clicking the close button by calling the handler directly
        portfolio_view._on_close_clicked(symbol, quantity)
        
        # Verify signal was emitted with correct data
        assert len(signal_data) == 1, "Signal should be emitted exactly once"
        emitted_symbol, emitted_quantity = signal_data[0]
        
        assert emitted_symbol == symbol, f"Expected symbol {symbol}, got {emitted_symbol}"
        assert emitted_quantity == quantity, f"Expected quantity {quantity}, got {emitted_quantity}"
        
    except ImportError:
        pytest.skip("PySide6 not available for testing")
