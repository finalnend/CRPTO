"""Property-based tests for InputValidator class.

Tests the input validation correctness properties using Hypothesis.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from hypothesis import given, settings, strategies as st, assume

from app.ui.utils import InputValidator, ValidationState


# Strategies for generating valid test data
positive_balance_strategy = st.decimals(
    min_value=Decimal("100"),
    max_value=Decimal("10000000"),
    places=2,
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

positive_position_strategy = st.decimals(
    min_value=Decimal("0.001"),
    max_value=Decimal("10000"),
    places=8,
    allow_nan=False,
    allow_infinity=False
)

positive_quantity_strategy = st.decimals(
    min_value=Decimal("0.001"),
    max_value=Decimal("10000"),
    places=8,
    allow_nan=False,
    allow_infinity=False
)

# Strategy for invalid quantity strings (negative, zero, non-numeric)
invalid_quantity_strategy = st.one_of(
    st.just("0"),
    st.just("-1"),
    st.just("-0.5"),
    st.just("abc"),
    st.just("12.34.56"),
    st.just("--5"),
    st.just("1e999999"),  # Overflow - should be caught as invalid
)


@given(invalid_quantity=invalid_quantity_strategy)
@settings(max_examples=100)
def test_invalid_input_detection(invalid_quantity: str):
    """
    **Feature: ui-ux-convenience, Property 4: Invalid Input Detection**
    **Validates: Requirements 3.1**
    
    For any quantity string that is negative, zero, or non-numeric,
    the validation state SHALL be INVALID.
    """
    validator = InputValidator()
    
    state, message = validator.validate_quantity(
        quantity_str=invalid_quantity,
        order_type="BUY",
        balance=Decimal("10000"),
        position_size=Decimal("0"),
        current_price=Decimal("100")
    )
    
    assert state == ValidationState.INVALID, \
        f"Invalid input '{invalid_quantity}' should return INVALID state, got {state}"


@given(
    quantity=positive_quantity_strategy,
    balance=positive_balance_strategy,
    price=positive_price_strategy
)
@settings(max_examples=100)
def test_buy_over_budget_warning(
    quantity: Decimal,
    balance: Decimal,
    price: Decimal
):
    """
    **Feature: ui-ux-convenience, Property 5: Buy Over-Budget Warning**
    **Validates: Requirements 3.2**
    
    For any buy quantity where quantity * price > balance,
    the validation state SHALL be WARNING.
    """
    order_value = quantity * price
    
    # Only test cases where order value exceeds balance
    assume(order_value > balance)
    
    validator = InputValidator()
    
    state, message = validator.validate_quantity(
        quantity_str=str(quantity),
        order_type="BUY",
        balance=balance,
        position_size=Decimal("0"),
        current_price=price
    )
    
    assert state == ValidationState.WARNING, \
        f"Buy quantity exceeding balance should return WARNING state, got {state}"
    assert "balance" in message.lower(), \
        "Warning message should mention balance"


@given(
    quantity=positive_quantity_strategy,
    position_size=positive_position_strategy
)
@settings(max_examples=100)
def test_sell_over_position_warning(
    quantity: Decimal,
    position_size: Decimal
):
    """
    **Feature: ui-ux-convenience, Property 6: Sell Over-Position Warning**
    **Validates: Requirements 3.3**
    
    For any sell quantity where quantity > position_size,
    the validation state SHALL be WARNING.
    """
    # Only test cases where quantity exceeds position
    assume(quantity > position_size)
    
    validator = InputValidator()
    
    state, message = validator.validate_quantity(
        quantity_str=str(quantity),
        order_type="SELL",
        balance=Decimal("10000"),
        position_size=position_size,
        current_price=Decimal("100")
    )
    
    assert state == ValidationState.WARNING, \
        f"Sell quantity exceeding position should return WARNING state, got {state}"
    assert "position" in message.lower(), \
        "Warning message should mention position"


@given(
    quantity=positive_quantity_strategy,
    balance=positive_balance_strategy,
    price=positive_price_strategy,
    position_size=positive_position_strategy
)
@settings(max_examples=100)
def test_valid_input_detection_buy(
    quantity: Decimal,
    balance: Decimal,
    price: Decimal,
    position_size: Decimal
):
    """
    **Feature: ui-ux-convenience, Property 7: Valid Input Detection**
    **Validates: Requirements 3.4**
    
    For any quantity that is positive, numeric, and within limits
    (buy: quantity * price <= balance), the validation state SHALL be VALID.
    """
    order_value = quantity * price
    
    # Only test cases where order value is within balance
    assume(order_value <= balance)
    
    validator = InputValidator()
    
    state, message = validator.validate_quantity(
        quantity_str=str(quantity),
        order_type="BUY",
        balance=balance,
        position_size=position_size,
        current_price=price
    )
    
    assert state == ValidationState.VALID, \
        f"Valid buy input should return VALID state, got {state}"
    assert message == "", \
        "Valid input should have empty message"


@given(
    quantity=positive_quantity_strategy,
    position_size=positive_position_strategy
)
@settings(max_examples=100)
def test_valid_input_detection_sell(
    quantity: Decimal,
    position_size: Decimal
):
    """
    **Feature: ui-ux-convenience, Property 7: Valid Input Detection**
    **Validates: Requirements 3.4**
    
    For any quantity that is positive, numeric, and within limits
    (sell: quantity <= position_size), the validation state SHALL be VALID.
    """
    # Only test cases where quantity is within position
    assume(quantity <= position_size)
    
    validator = InputValidator()
    
    state, message = validator.validate_quantity(
        quantity_str=str(quantity),
        order_type="SELL",
        balance=Decimal("10000"),
        position_size=position_size,
        current_price=Decimal("100")
    )
    
    assert state == ValidationState.VALID, \
        f"Valid sell input should return VALID state, got {state}"
    assert message == "", \
        "Valid input should have empty message"


# Additional edge case tests
def test_empty_input_returns_neutral():
    """Test that empty input returns NEUTRAL state."""
    validator = InputValidator()
    
    state, message = validator.validate_quantity(
        quantity_str="",
        order_type="BUY",
        balance=Decimal("10000"),
        position_size=Decimal("0"),
        current_price=Decimal("100")
    )
    
    assert state == ValidationState.NEUTRAL
    assert message == ""


def test_whitespace_input_returns_neutral():
    """Test that whitespace-only input returns NEUTRAL state."""
    validator = InputValidator()
    
    state, message = validator.validate_quantity(
        quantity_str="   ",
        order_type="BUY",
        balance=Decimal("10000"),
        position_size=Decimal("0"),
        current_price=Decimal("100")
    )
    
    assert state == ValidationState.NEUTRAL
    assert message == ""


def test_buy_without_price_returns_warning():
    """Test that buy order without price data returns WARNING."""
    validator = InputValidator()
    
    state, message = validator.validate_quantity(
        quantity_str="10",
        order_type="BUY",
        balance=Decimal("10000"),
        position_size=Decimal("0"),
        current_price=None
    )
    
    assert state == ValidationState.WARNING
    assert "price" in message.lower()
