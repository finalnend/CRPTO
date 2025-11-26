"""Property-based tests for OrderConfirmationDialog.

Tests the large order confirmation threshold property using Hypothesis.
"""

from __future__ import annotations

from decimal import Decimal

from hypothesis import given, settings, strategies as st, assume

from app.ui.widgets.order_confirmation_dialog import OrderConfirmationDialog


# Strategies for generating valid test data
positive_balance_strategy = st.decimals(
    min_value=Decimal("100"),
    max_value=Decimal("10000000"),
    places=2,
    allow_nan=False,
    allow_infinity=False
)

positive_value_strategy = st.decimals(
    min_value=Decimal("1"),
    max_value=Decimal("10000000"),
    places=2,
    allow_nan=False,
    allow_infinity=False
)


@given(
    total_value=positive_value_strategy,
    balance=positive_balance_strategy
)
@settings(max_examples=100)
def test_large_order_confirmation_threshold(
    total_value: Decimal,
    balance: Decimal
):
    """
    **Feature: ui-ux-convenience, Property 8: Large Order Confirmation Threshold**
    **Validates: Requirements 4.1**
    
    For any order where total_value > balance * 0.5, the confirmation dialog
    SHALL be displayed before execution.
    """
    # Skip invalid cases where balance is zero or negative
    assume(balance > Decimal("0"))
    
    # Calculate the threshold
    threshold = balance * Decimal("0.5")
    
    # Check if confirmation is required
    requires_confirmation = OrderConfirmationDialog.requires_confirmation(total_value, balance)
    
    # Verify the property
    if total_value > threshold:
        assert requires_confirmation is True, \
            f"Orders exceeding 50% of balance should require confirmation: " \
            f"total_value={total_value}, balance={balance}, threshold={threshold}"
    else:
        assert requires_confirmation is False, \
            f"Orders not exceeding 50% of balance should not require confirmation: " \
            f"total_value={total_value}, balance={balance}, threshold={threshold}"
