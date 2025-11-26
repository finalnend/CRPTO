"""Property-based tests for theme module.

Tests the theme contrast ratio compliance using Hypothesis.
"""

from __future__ import annotations

from decimal import Decimal
from hypothesis import given, settings, strategies as st

from PySide6.QtGui import QColor

from app.theme import (
    calculate_contrast_ratio,
    ensure_contrast_ratio,
    get_theme_colors,
    get_acrylic_colors,
    get_relative_luminance,
    get_price_change_color,
    MIN_CONTRAST_RATIO,
)


# Strategy for generating valid RGB color components
rgb_component = st.integers(min_value=0, max_value=255)

# Strategy for generating QColor objects
qcolor_strategy = st.builds(
    QColor,
    rgb_component,
    rgb_component,
    rgb_component,
)

# Strategy for theme modes
theme_mode_strategy = st.sampled_from(["dark", "light"])

# Strategy for accent colors (common UI accent colors)
accent_color_strategy = st.sampled_from([
    QColor("#0A84FF"),  # Blue
    QColor("#30D158"),  # Green
    QColor("#FF453A"),  # Red
    QColor("#FF9F0A"),  # Orange
    QColor("#BF5AF2"),  # Purple
    QColor("#64D2FF"),  # Cyan
])


@given(
    mode=theme_mode_strategy,
    accent=accent_color_strategy
)
@settings(max_examples=100)
def test_theme_contrast_ratio_compliance(mode: str, accent: QColor):
    """
    **Feature: modern-ui-market-sim, Property 1: Theme contrast ratio compliance**
    **Validates: Requirements 1.3**
    
    For any theme mode (dark or light) and any accent color, the generated
    text color and background color combination SHALL produce a contrast
    ratio of at least 4.5:1.
    """
    theme_colors = get_theme_colors(mode, accent)
    
    # Check text on main background
    text_color = theme_colors["text"]
    bg_color = theme_colors["background"]
    
    contrast_ratio = calculate_contrast_ratio(text_color, bg_color)
    
    assert contrast_ratio >= MIN_CONTRAST_RATIO, (
        f"Text on background contrast ratio {contrast_ratio:.2f} is below "
        f"minimum {MIN_CONTRAST_RATIO} for mode={mode}"
    )
    
    # Check text on panel background
    text_on_panel = theme_colors["text_on_panel"]
    panel_color = theme_colors["panel"]
    
    panel_contrast_ratio = calculate_contrast_ratio(text_on_panel, panel_color)
    
    assert panel_contrast_ratio >= MIN_CONTRAST_RATIO, (
        f"Text on panel contrast ratio {panel_contrast_ratio:.2f} is below "
        f"minimum {MIN_CONTRAST_RATIO} for mode={mode}"
    )


@given(
    text_color=qcolor_strategy,
    background_color=qcolor_strategy
)
@settings(max_examples=100)
def test_ensure_contrast_ratio_meets_minimum(
    text_color: QColor,
    background_color: QColor
):
    """
    **Feature: modern-ui-market-sim, Property 1: Theme contrast ratio compliance**
    **Validates: Requirements 1.3**
    
    For any text color and background color combination, the ensure_contrast_ratio
    function SHALL return a text color that produces a contrast ratio of at
    least 4.5:1 with the background.
    """
    adjusted_text = ensure_contrast_ratio(text_color, background_color)
    
    contrast_ratio = calculate_contrast_ratio(adjusted_text, background_color)
    
    assert contrast_ratio >= MIN_CONTRAST_RATIO, (
        f"Adjusted text contrast ratio {contrast_ratio:.2f} is below "
        f"minimum {MIN_CONTRAST_RATIO}"
    )


@given(mode=theme_mode_strategy)
@settings(max_examples=100)
def test_acrylic_colors_contrast_compliance(mode: str):
    """
    **Feature: modern-ui-market-sim, Property 1: Theme contrast ratio compliance**
    **Validates: Requirements 1.3**
    
    For any theme mode, the acrylic background colors SHALL support text
    with a contrast ratio of at least 4.5:1.
    """
    tint_color, opacity, blur_radius = get_acrylic_colors(mode)
    
    # Determine appropriate text color for the mode
    if mode == "dark":
        text_color = QColor("#E6E6E6")
    else:
        text_color = QColor("#111111")
    
    # Calculate contrast with the tint color
    # Note: The actual rendered color would be affected by opacity,
    # but we test against the solid tint color as worst case
    contrast_ratio = calculate_contrast_ratio(text_color, tint_color)
    
    assert contrast_ratio >= MIN_CONTRAST_RATIO, (
        f"Acrylic text contrast ratio {contrast_ratio:.2f} is below "
        f"minimum {MIN_CONTRAST_RATIO} for mode={mode}"
    )


@given(color=qcolor_strategy)
@settings(max_examples=100)
def test_relative_luminance_bounds(color: QColor):
    """
    Test that relative luminance is always between 0 and 1.
    """
    luminance = get_relative_luminance(color)
    
    assert 0.0 <= luminance <= 1.0, (
        f"Luminance {luminance} is outside valid range [0, 1]"
    )


@given(
    foreground=qcolor_strategy,
    background=qcolor_strategy
)
@settings(max_examples=100)
def test_contrast_ratio_bounds(foreground: QColor, background: QColor):
    """
    Test that contrast ratio is always between 1 and 21.
    """
    ratio = calculate_contrast_ratio(foreground, background)
    
    assert 1.0 <= ratio <= 21.0, (
        f"Contrast ratio {ratio} is outside valid range [1, 21]"
    )


@given(color=qcolor_strategy)
@settings(max_examples=100)
def test_contrast_ratio_symmetry(color: QColor):
    """
    Test that contrast ratio is symmetric (same regardless of which color
    is foreground vs background).
    """
    other_color = QColor(255 - color.red(), 255 - color.green(), 255 - color.blue())
    
    ratio1 = calculate_contrast_ratio(color, other_color)
    ratio2 = calculate_contrast_ratio(other_color, color)
    
    assert abs(ratio1 - ratio2) < 0.001, (
        f"Contrast ratio is not symmetric: {ratio1} vs {ratio2}"
    )


# Strategy for generating price change values (positive, negative, zero)
price_change_strategy = st.one_of(
    st.decimals(min_value=Decimal("0.0001"), max_value=Decimal("1000000"), places=4),  # Positive
    st.decimals(min_value=Decimal("-1000000"), max_value=Decimal("-0.0001"), places=4),  # Negative
    st.just(Decimal("0")),  # Zero
)


@given(
    positive_value=st.decimals(min_value=Decimal("0.0001"), max_value=Decimal("1000000"), places=4),
    negative_value=st.decimals(min_value=Decimal("-1000000"), max_value=Decimal("-0.0001"), places=4),
    mode=theme_mode_strategy
)
@settings(max_examples=100)
def test_price_color_distinction(positive_value: Decimal, negative_value: Decimal, mode: str):
    """
    **Feature: modern-ui-market-sim, Property 2: Positive/negative price color distinction**
    **Validates: Requirements 3.1**
    
    For any price change value, positive values SHALL produce a different color
    than negative values from the color selection function.
    """
    positive_color = get_price_change_color(positive_value, mode)
    negative_color = get_price_change_color(negative_value, mode)
    
    # Colors must be different for positive vs negative values
    assert positive_color != negative_color, (
        f"Positive ({positive_value}) and negative ({negative_value}) values "
        f"produced the same color {positive_color.name()} in {mode} mode"
    )
    
    # Verify the colors are the expected ones for the mode
    if mode == "dark":
        # Positive should be green-ish, negative should be red-ish
        assert positive_color.green() > positive_color.red(), (
            f"Positive color {positive_color.name()} should have more green than red in dark mode"
        )
        assert negative_color.red() > negative_color.green(), (
            f"Negative color {negative_color.name()} should have more red than green in dark mode"
        )
    else:
        # Light mode should also have distinct green/red colors
        assert positive_color.green() > positive_color.red(), (
            f"Positive color {positive_color.name()} should have more green than red in light mode"
        )
        assert negative_color.red() > negative_color.green(), (
            f"Negative color {negative_color.name()} should have more red than green in light mode"
        )


@given(mode=theme_mode_strategy)
@settings(max_examples=100)
def test_zero_value_color_is_neutral(mode: str):
    """
    **Feature: modern-ui-market-sim, Property 2: Positive/negative price color distinction**
    **Validates: Requirements 3.1**
    
    For zero price change, the color should be neutral (neither green nor red).
    """
    zero_color = get_price_change_color(Decimal("0"), mode)
    positive_color = get_price_change_color(Decimal("1"), mode)
    negative_color = get_price_change_color(Decimal("-1"), mode)
    
    # Zero color should be different from both positive and negative
    assert zero_color != positive_color, (
        f"Zero value color should differ from positive color in {mode} mode"
    )
    assert zero_color != negative_color, (
        f"Zero value color should differ from negative color in {mode} mode"
    )
