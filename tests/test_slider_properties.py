"""Property-based tests for QuantitySlider widget.

Tests the slider-input bidirectional sync correctness property using Hypothesis.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from hypothesis import given, settings, strategies as st

from app.ui.widgets.quantity_slider import QuantitySlider


# Strategies for generating valid test data
max_value_strategy = st.decimals(
    min_value=Decimal("1"),
    max_value=Decimal("100000"),
    places=8,
    allow_nan=False,
    allow_infinity=False
)


@given(
    max_val=max_value_strategy,
    value_ratio=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)
)
@settings(max_examples=100)
def test_slider_input_bidirectional_sync(
    max_val: Decimal,
    value_ratio: float,
    _qt_app
):
    """
    **Feature: ui-ux-convenience, Property 3: Slider-Input Bidirectional Sync**
    **Validates: Requirements 2.2, 2.3**
    
    For any valid quantity value, setting the slider SHALL update the input field
    to that value, AND setting the input field SHALL update the slider to that value.
    """
    # Create slider widget
    slider = QuantitySlider()
    
    # Set range
    min_val = Decimal("0")
    slider.set_range(min_val, max_val)
    
    # Calculate test value within range
    test_value = min_val + (max_val - min_val) * Decimal(str(value_ratio))
    
    # Test: Setting value updates slider position
    slider.set_value(test_value)
    retrieved_value = slider.get_value()
    
    # The retrieved value should be close to the set value
    # (allowing for slider step quantization)
    if max_val > min_val:
        tolerance = (max_val - min_val) / Decimal(str(slider.SLIDER_STEPS))
        assert abs(retrieved_value - test_value) <= tolerance, \
            f"Slider value should match set value within tolerance: set {test_value}, got {retrieved_value}"
    else:
        assert retrieved_value == min_val, \
            f"When max equals min, value should be min: expected {min_val}, got {retrieved_value}"


@given(
    max_val=max_value_strategy,
    slider_position=st.integers(min_value=0, max_value=1000)
)
@settings(max_examples=100)
def test_slider_position_to_value_consistency(
    max_val: Decimal,
    slider_position: int,
    _qt_app
):
    """
    **Feature: ui-ux-convenience, Property 3: Slider-Input Bidirectional Sync (reverse)**
    **Validates: Requirements 2.2, 2.3**
    
    For any slider position, the emitted value should be consistent with the position.
    """
    # Create slider widget
    slider = QuantitySlider()
    
    # Set range
    min_val = Decimal("0")
    slider.set_range(min_val, max_val)
    
    # Track emitted values
    emitted_values = []
    slider.valueChanged.connect(lambda v: emitted_values.append(v))
    
    # Simulate slider movement by directly setting the internal slider
    slider._slider.setValue(slider_position)
    
    # Check that value was emitted
    if emitted_values:
        emitted_value = emitted_values[-1]
        
        # Calculate expected value based on slider position
        expected_ratio = Decimal(str(slider_position)) / Decimal(str(slider.SLIDER_STEPS))
        expected_value = min_val + (max_val - min_val) * expected_ratio
        
        # Values should match
        assert emitted_value == expected_value, \
            f"Emitted value should match expected: expected {expected_value}, got {emitted_value}"


def test_slider_range_clamping(_qt_app):
    """Test that values are clamped to the set range."""
    slider = QuantitySlider()
    
    min_val = Decimal("10")
    max_val = Decimal("100")
    slider.set_range(min_val, max_val)
    
    # Set value below minimum
    slider.set_value(Decimal("5"))
    assert slider.get_value() == min_val, "Value below min should be clamped to min"
    
    # Set value above maximum
    slider.set_value(Decimal("200"))
    assert slider.get_value() == max_val, "Value above max should be clamped to max"


def test_slider_zero_range(_qt_app):
    """Test slider behavior when min equals max."""
    slider = QuantitySlider()
    
    value = Decimal("50")
    slider.set_range(value, value)
    
    slider.set_value(value)
    assert slider.get_value() == value, "When range is zero, value should equal min/max"
