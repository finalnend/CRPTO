"""Property-based tests for order service module.

Tests the order service correctness properties using Hypothesis.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Optional

import pytest
from hypothesis import given, settings, strategies as st, assume

from app.trading.portfolio import PortfolioManager
from app.trading.orders import (
    OrderService,
    OrderStatus,
    OrderRejectionReason,
    IDataProvider,
)


class MockDataProvider(IDataProvider):
    """Mock data provider for testing that returns configurable prices."""

    def __init__(self, prices: dict[str, Decimal] | None = None, connected: bool = True):
        self._prices = prices or {}
        self._connected = connected

    def get_current_price(self, symbol: str) -> Optional[Decimal]:
        return self._prices.get(symbol.upper())

    def is_connected(self) -> bool:
        return self._connected

    def set_price(self, symbol: str, price: Decimal) -> None:
        self._prices[symbol.upper()] = price


# Strategies for generating valid test data
valid_balance_strategy = st.decimals(
    min_value=Decimal("1000"),
    max_value=Decimal("10000000"),
    places=2,
    allow_nan=False,
    allow_infinity=False
)

positive_quantity_strategy = st.decimals(
    min_value=Decimal("0.001"),
    max_value=Decimal("1000"),
    places=8,
    allow_nan=False,
    allow_infinity=False
)

positive_price_strategy = st.decimals(
    min_value=Decimal("0.01"),
    max_value=Decimal("100000"),
    places=2,
    allow_nan=False,
    allow_infinity=False
)

symbol_strategy = st.sampled_from(["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "ADAUSDT"])



@given(
    initial_balance=valid_balance_strategy,
    quantity=positive_quantity_strategy,
    price=positive_price_strategy,
    symbol=symbol_strategy
)
@settings(max_examples=100)
def test_insufficient_balance_rejection(
    initial_balance: Decimal,
    quantity: Decimal,
    price: Decimal,
    symbol: str
):
    """
    **Feature: modern-ui-market-sim, Property 8: Insufficient balance rejection**
    **Validates: Requirements 5.3**
    
    For any buy order where (quantity × price) exceeds available balance,
    the order SHALL be rejected with INSUFFICIENT_BALANCE reason.
    """
    order_value = quantity * price
    
    # Only test cases where order value exceeds balance
    assume(order_value > initial_balance)
    
    portfolio = PortfolioManager(initial_balance)
    data_provider = MockDataProvider({symbol: price})
    order_service = OrderService(portfolio, data_provider)
    
    original_balance = portfolio.get_balance()
    result = order_service.submit_buy(symbol, quantity)
    
    # Order should be rejected
    assert result.status == OrderStatus.REJECTED, \
        "Order should be rejected when balance is insufficient"
    assert result.rejection_reason == OrderRejectionReason.INSUFFICIENT_BALANCE, \
        "Rejection reason should be INSUFFICIENT_BALANCE"
    assert result.transaction is None, \
        "No transaction should be created for rejected order"
    
    # Balance should remain unchanged
    assert portfolio.get_balance() == original_balance, \
        "Balance should not change when order is rejected"
    
    # No position should be created
    assert portfolio.get_position(symbol) is None, \
        "No position should be created when order is rejected"



@given(
    initial_balance=valid_balance_strategy,
    buy_quantity=positive_quantity_strategy,
    sell_quantity=positive_quantity_strategy,
    buy_price=positive_price_strategy,
    sell_price=positive_price_strategy,
    symbol=symbol_strategy
)
@settings(max_examples=100)
def test_insufficient_holdings_rejection(
    initial_balance: Decimal,
    buy_quantity: Decimal,
    sell_quantity: Decimal,
    buy_price: Decimal,
    sell_price: Decimal,
    symbol: str
):
    """
    **Feature: modern-ui-market-sim, Property 9: Insufficient holdings rejection**
    **Validates: Requirements 5.4**
    
    For any sell order where quantity exceeds held quantity for that symbol,
    the order SHALL be rejected with INSUFFICIENT_HOLDINGS reason.
    """
    buy_value = buy_quantity * buy_price
    
    # Need sufficient balance to buy first
    assume(buy_value <= initial_balance)
    # Sell quantity must exceed holdings for this test
    assume(sell_quantity > buy_quantity)
    
    portfolio = PortfolioManager(initial_balance)
    data_provider = MockDataProvider({symbol: sell_price})
    order_service = OrderService(portfolio, data_provider)
    
    # First buy to establish holdings
    portfolio.execute_buy(symbol, buy_quantity, buy_price)
    balance_after_buy = portfolio.get_balance()
    position_after_buy = portfolio.get_position(symbol)
    
    # Attempt to sell more than we have
    result = order_service.submit_sell(symbol, sell_quantity)
    
    # Order should be rejected
    assert result.status == OrderStatus.REJECTED, \
        "Order should be rejected when holdings are insufficient"
    assert result.rejection_reason == OrderRejectionReason.INSUFFICIENT_HOLDINGS, \
        "Rejection reason should be INSUFFICIENT_HOLDINGS"
    assert result.transaction is None, \
        "No transaction should be created for rejected order"
    
    # Balance should remain unchanged
    assert portfolio.get_balance() == balance_after_buy, \
        "Balance should not change when order is rejected"
    
    # Position should remain unchanged
    current_position = portfolio.get_position(symbol)
    assert current_position is not None, \
        "Position should still exist after rejected sell"
    assert current_position.quantity == position_after_buy.quantity, \
        "Holdings should not change when order is rejected"



@given(
    initial_balance=valid_balance_strategy,
    quantity=positive_quantity_strategy,
    price=positive_price_strategy,
    symbol=symbol_strategy
)
@settings(max_examples=100)
def test_order_execution_uses_current_price(
    initial_balance: Decimal,
    quantity: Decimal,
    price: Decimal,
    symbol: str
):
    """
    **Feature: modern-ui-market-sim, Property 15: Order execution uses current price**
    **Validates: Requirements 7.2**
    
    For any paper trade order execution, the execution price SHALL equal
    the current price returned by the data provider at execution time.
    """
    order_value = quantity * price
    
    # Skip if insufficient balance
    assume(order_value <= initial_balance)
    
    portfolio = PortfolioManager(initial_balance)
    data_provider = MockDataProvider({symbol: price})
    order_service = OrderService(portfolio, data_provider)
    
    # Execute buy order
    result = order_service.submit_buy(symbol, quantity)
    
    # Order should be executed
    assert result.status == OrderStatus.EXECUTED, \
        "Order should be executed when balance is sufficient"
    assert result.transaction is not None, \
        "Transaction should be created for executed order"
    
    # Verify execution price matches data provider price
    assert result.transaction.price == price, \
        "Execution price should equal current price from data provider"
    
    # Verify the transaction value is calculated correctly
    expected_value = quantity * price
    assert result.transaction.total_value == expected_value, \
        "Transaction value should equal quantity × price"
    
    # Verify balance was deducted by the correct amount
    assert portfolio.get_balance() == initial_balance - expected_value, \
        "Balance should be reduced by quantity × current price"


@given(
    initial_balance=valid_balance_strategy,
    buy_quantity=positive_quantity_strategy,
    sell_quantity=positive_quantity_strategy,
    buy_price=positive_price_strategy,
    sell_price=positive_price_strategy,
    symbol=symbol_strategy
)
@settings(max_examples=100)
def test_sell_order_execution_uses_current_price(
    initial_balance: Decimal,
    buy_quantity: Decimal,
    sell_quantity: Decimal,
    buy_price: Decimal,
    sell_price: Decimal,
    symbol: str
):
    """
    **Feature: modern-ui-market-sim, Property 15: Order execution uses current price**
    **Validates: Requirements 7.2**
    
    For any paper trade sell order execution, the execution price SHALL equal
    the current price returned by the data provider at execution time.
    """
    buy_value = buy_quantity * buy_price
    
    # Need sufficient balance to buy first
    assume(buy_value <= initial_balance)
    # Can only sell what we have
    assume(sell_quantity <= buy_quantity)
    
    portfolio = PortfolioManager(initial_balance)
    data_provider = MockDataProvider({symbol: buy_price})
    order_service = OrderService(portfolio, data_provider)
    
    # First buy to establish holdings
    portfolio.execute_buy(symbol, buy_quantity, buy_price)
    balance_after_buy = portfolio.get_balance()
    
    # Update price for sell (simulating price change)
    data_provider.set_price(symbol, sell_price)
    
    # Execute sell order
    result = order_service.submit_sell(symbol, sell_quantity)
    
    # Order should be executed
    assert result.status == OrderStatus.EXECUTED, \
        "Order should be executed when holdings are sufficient"
    assert result.transaction is not None, \
        "Transaction should be created for executed order"
    
    # Verify execution price matches current data provider price (sell_price)
    assert result.transaction.price == sell_price, \
        "Execution price should equal current price from data provider"
    
    # Verify balance was credited by the correct amount
    expected_credit = sell_quantity * sell_price
    assert portfolio.get_balance() == balance_after_buy + expected_credit, \
        "Balance should increase by quantity × current price"
