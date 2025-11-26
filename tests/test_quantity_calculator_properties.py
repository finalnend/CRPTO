"""Property-based tests for QuantityCalculator class.

Tests the quantity calculation correctness properties using Hypothesis.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from hypothesis import given, settings, strategies as st, assume

from app.ui.utils import QuantityCalculator


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

percentage_strategy = st.sampled_from([0.25, 0.5, 0.75, 1.0])


@given(
    balance=positive_balance_strategy,
    price=positive_price_strategy,
    percentage=percentage_strategy
)
@settings(max_examples=100)
def test_buy_quantity_preset_calculation(
    balance: Decimal,
    price: Decimal,
    percentage: float
):
    """
    **Feature: ui-ux-convenience, Property 1: Buy Quantity Preset Calculation**
    **Validates: Requirements 1.2**
    
    For any available balance, current price (> 0), and percentage (0.25, 0.5, 0.75, 1.0),
    the calculated buy quantity SHALL equal (balance * percentage) / price.
    """
    # Calculate expected quantity
    expected_quantity = (balance * Decimal(str(percentage))) / price
    
    # Calculate using QuantityCalculator
    actual_quantity = QuantityCalculator.calculate_buy_quantity(balance, price, percentage)
    
    assert actual_quantity == expected_quantity, \
        f"Buy quantity should equal (balance * percentage) / price: expected {expected_quantity}, got {actual_quantity}"


@given(
    position_size=positive_position_strategy,
    percentage=percentage_strategy
)
@settings(max_examples=100)
def test_sell_quantity_preset_calculation(
    position_size: Decimal,
    percentage: float
):
    """
    **Feature: ui-ux-convenience, Property 2: Sell Quantity Preset Calculation**
    **Validates: Requirements 1.3**
    
    For any position size and percentage (0.25, 0.5, 0.75, 1.0),
    the calculated sell quantity SHALL equal position_size * percentage.
    """
    # Calculate expected quantity
    expected_quantity = position_size * Decimal(str(percentage))
    
    # Calculate using QuantityCalculator
    actual_quantity = QuantityCalculator.calculate_sell_quantity(position_size, percentage)
    
    assert actual_quantity == expected_quantity, \
        f"Sell quantity should equal position_size * percentage: expected {expected_quantity}, got {actual_quantity}"


# Edge case tests for validation
def test_buy_quantity_zero_price_raises():
    """Test that zero price raises ValueError."""
    with pytest.raises(ValueError, match="Price must be greater than zero"):
        QuantityCalculator.calculate_buy_quantity(
            Decimal("1000"),
            Decimal("0"),
            0.5
        )


def test_buy_quantity_negative_price_raises():
    """Test that negative price raises ValueError."""
    with pytest.raises(ValueError, match="Price must be greater than zero"):
        QuantityCalculator.calculate_buy_quantity(
            Decimal("1000"),
            Decimal("-100"),
            0.5
        )


def test_buy_quantity_invalid_percentage_raises():
    """Test that invalid percentage raises ValueError."""
    with pytest.raises(ValueError, match="Percentage must be between 0 and 1"):
        QuantityCalculator.calculate_buy_quantity(
            Decimal("1000"),
            Decimal("100"),
            1.5
        )


def test_sell_quantity_invalid_percentage_raises():
    """Test that invalid percentage raises ValueError."""
    with pytest.raises(ValueError, match="Percentage must be between 0 and 1"):
        QuantityCalculator.calculate_sell_quantity(
            Decimal("10"),
            -0.5
        )
