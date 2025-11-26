"""Property-based tests for portfolio manager module.

Tests the portfolio management correctness properties using Hypothesis.
"""

from __future__ import annotations

from decimal import Decimal
from datetime import datetime

import pytest
from hypothesis import given, settings, strategies as st, assume

from app.trading.portfolio import PortfolioManager
from app.trading.models import Position, Transaction


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


@given(initial_balance=valid_balance_strategy)
@settings(max_examples=100)
def test_portfolio_initialization_with_valid_balance(initial_balance: Decimal):
    """
    **Feature: modern-ui-market-sim, Property 3: Portfolio initialization with valid balance**
    **Validates: Requirements 4.1**
    
    For any starting balance between 1,000 and 10,000,000 USD, creating a new
    portfolio SHALL result in a portfolio with that exact balance and zero positions.
    """
    portfolio = PortfolioManager(initial_balance)
    
    assert portfolio.get_balance() == initial_balance, "Balance should equal initial balance"
    assert len(portfolio.get_positions()) == 0, "Should have zero positions"
    assert len(portfolio.get_transactions()) == 0, "Should have zero transactions"



@given(
    initial_balance=valid_balance_strategy,
    prices=st.dictionaries(
        keys=symbol_strategy,
        values=positive_price_strategy,
        min_size=0,
        max_size=5
    )
)
@settings(max_examples=100)
def test_portfolio_value_calculation_correctness(
    initial_balance: Decimal,
    prices: dict
):
    """
    **Feature: modern-ui-market-sim, Property 4: Portfolio value calculation correctness**
    **Validates: Requirements 4.2, 4.3**
    
    For any set of positions and corresponding market prices, the calculated
    portfolio value SHALL equal the sum of (quantity × current_price) for all
    positions plus the available balance.
    """
    portfolio = PortfolioManager(initial_balance)
    
    # Portfolio with no positions should equal balance
    assert portfolio.get_portfolio_value(prices) == initial_balance
    
    # Add some positions if we have prices
    positions_added = {}
    remaining_balance = initial_balance
    
    for symbol, price in prices.items():
        # Buy a small quantity if we have enough balance
        quantity = Decimal("0.1")
        order_value = quantity * price
        if order_value <= remaining_balance:
            portfolio.execute_buy(symbol, quantity, price)
            positions_added[symbol] = quantity
            remaining_balance -= order_value
    
    # Calculate expected value
    expected_value = portfolio.get_balance()
    for symbol, position in portfolio.get_positions().items():
        if symbol in prices:
            expected_value += position.quantity * prices[symbol]
        else:
            expected_value += position.total_cost
    
    assert portfolio.get_portfolio_value(prices) == expected_value


@given(
    initial_balance=valid_balance_strategy,
    reset_balance=valid_balance_strategy
)
@settings(max_examples=100)
def test_portfolio_reset_restores_initial_state(
    initial_balance: Decimal,
    reset_balance: Decimal
):
    """
    **Feature: modern-ui-market-sim, Property 5: Portfolio reset restores initial state**
    **Validates: Requirements 4.4**
    
    For any portfolio state with any number of positions and transactions,
    calling reset SHALL result in zero positions, zero transactions, and
    balance equal to the specified initial balance.
    """
    portfolio = PortfolioManager(initial_balance)
    
    # Add some positions and transactions
    price = Decimal("100")
    quantity = Decimal("1")
    if initial_balance >= price * quantity:
        portfolio.execute_buy("BTCUSDT", quantity, price)
        portfolio.execute_buy("ETHUSDT", quantity, price)
    
    # Reset the portfolio
    portfolio.reset(reset_balance)
    
    assert portfolio.get_balance() == reset_balance, "Balance should equal reset balance"
    assert len(portfolio.get_positions()) == 0, "Should have zero positions after reset"
    assert len(portfolio.get_transactions()) == 0, "Should have zero transactions after reset"


@given(
    initial_balance=valid_balance_strategy,
    quantity=positive_quantity_strategy,
    price=positive_price_strategy,
    symbol=symbol_strategy
)
@settings(max_examples=100)
def test_buy_order_balance_and_holdings_update(
    initial_balance: Decimal,
    quantity: Decimal,
    price: Decimal,
    symbol: str
):
    """
    **Feature: modern-ui-market-sim, Property 6: Buy order balance and holdings update**
    **Validates: Requirements 5.1**
    
    For any valid buy order (quantity > 0, sufficient balance), executing the
    order SHALL decrease balance by (quantity × price) and increase the
    symbol's holdings by quantity.
    """
    order_value = quantity * price
    
    # Skip if insufficient balance (this is tested by Property 8)
    assume(order_value <= initial_balance)
    
    portfolio = PortfolioManager(initial_balance)
    original_balance = portfolio.get_balance()
    
    portfolio.execute_buy(symbol, quantity, price)
    
    assert portfolio.get_balance() == original_balance - order_value, \
        "Balance should decrease by order value"
    
    position = portfolio.get_position(symbol)
    assert position is not None, "Position should exist after buy"
    assert position.quantity == quantity, "Holdings should equal purchased quantity"


@given(
    initial_balance=valid_balance_strategy,
    buy_quantity=positive_quantity_strategy,
    sell_quantity=positive_quantity_strategy,
    buy_price=positive_price_strategy,
    sell_price=positive_price_strategy,
    symbol=symbol_strategy
)
@settings(max_examples=100)
def test_sell_order_balance_and_holdings_update(
    initial_balance: Decimal,
    buy_quantity: Decimal,
    sell_quantity: Decimal,
    buy_price: Decimal,
    sell_price: Decimal,
    symbol: str
):
    """
    **Feature: modern-ui-market-sim, Property 7: Sell order balance and holdings update**
    **Validates: Requirements 5.2**
    
    For any valid sell order (quantity > 0, sufficient holdings), executing
    the order SHALL increase balance by (quantity × price) and decrease the
    symbol's holdings by quantity.
    """
    buy_value = buy_quantity * buy_price
    
    # Need sufficient balance to buy first
    assume(buy_value <= initial_balance)
    # Can only sell what we have
    assume(sell_quantity <= buy_quantity)
    
    portfolio = PortfolioManager(initial_balance)
    
    # First buy to have holdings
    portfolio.execute_buy(symbol, buy_quantity, buy_price)
    balance_after_buy = portfolio.get_balance()
    
    # Now sell
    sell_value = sell_quantity * sell_price
    portfolio.execute_sell(symbol, sell_quantity, sell_price)
    
    assert portfolio.get_balance() == balance_after_buy + sell_value, \
        "Balance should increase by sell value"
    
    position = portfolio.get_position(symbol)
    expected_remaining = buy_quantity - sell_quantity
    
    if expected_remaining == Decimal("0"):
        assert position is None, "Position should be removed when fully sold"
    else:
        assert position is not None, "Position should exist with remaining holdings"
        assert position.quantity == expected_remaining, \
            "Holdings should decrease by sold quantity"


@given(
    initial_balance=valid_balance_strategy,
    quantity=positive_quantity_strategy,
    price=positive_price_strategy,
    symbol=symbol_strategy
)
@settings(max_examples=100)
def test_transaction_record_completeness(
    initial_balance: Decimal,
    quantity: Decimal,
    price: Decimal,
    symbol: str
):
    """
    **Feature: modern-ui-market-sim, Property 10: Transaction record completeness**
    **Validates: Requirements 5.5**
    
    For any executed order, the resulting transaction record SHALL contain
    non-null values for id, symbol, order_type, quantity, price, and timestamp.
    """
    order_value = quantity * price
    assume(order_value <= initial_balance)
    
    portfolio = PortfolioManager(initial_balance)
    transaction = portfolio.execute_buy(symbol, quantity, price)
    
    # Verify all required fields are present and non-null
    assert transaction.id is not None and transaction.id != "", \
        "Transaction ID should be non-null and non-empty"
    assert transaction.symbol is not None and transaction.symbol != "", \
        "Transaction symbol should be non-null and non-empty"
    assert transaction.order_type is not None and transaction.order_type in ("BUY", "SELL"), \
        "Transaction order_type should be BUY or SELL"
    assert transaction.quantity is not None and transaction.quantity > 0, \
        "Transaction quantity should be positive"
    assert transaction.price is not None and transaction.price > 0, \
        "Transaction price should be positive"
    assert transaction.timestamp is not None, \
        "Transaction timestamp should be non-null"
    assert isinstance(transaction.timestamp, datetime), \
        "Transaction timestamp should be a datetime"
    
    # Verify transaction is recorded in history
    transactions = portfolio.get_transactions()
    assert len(transactions) == 1, "Should have one transaction"
    assert transactions[0].id == transaction.id, "Transaction should be in history"
