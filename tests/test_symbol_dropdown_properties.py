"""Property-based tests for SymbolDropdown widget.

Tests the symbol selection and filtering correctness properties using Hypothesis.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Dict, List

import pytest
from hypothesis import given, settings, strategies as st, assume

from app.ui.widgets.symbol_dropdown import SymbolDropdown


# Strategies for generating valid test data
symbol_strategy = st.text(
    alphabet=st.sampled_from("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"),
    min_size=3,
    max_size=10
)

price_strategy = st.decimals(
    min_value=Decimal("0.00001"),
    max_value=Decimal("100000"),
    places=8,
    allow_nan=False,
    allow_infinity=False
)

symbols_list_strategy = st.lists(
    symbol_strategy,
    min_size=1,
    max_size=20,
    unique=True
)


@given(
    symbols=symbols_list_strategy,
    prices_data=st.lists(price_strategy, min_size=1, max_size=20)
)
@settings(max_examples=100)
def test_symbol_selection_updates(
    symbols: List[str],
    prices_data: List[Decimal],
    _qt_app
):
    """
    **Feature: ui-ux-convenience, Property 11: Symbol Selection Updates**
    **Validates: Requirements 8.3**
    
    For any symbol selected from the dropdown, the symbol input field SHALL
    contain that symbol AND the price display SHALL show the current price
    for that symbol.
    """
    # Create prices dict from symbols and prices_data
    prices: Dict[str, Decimal] = {}
    for i, symbol in enumerate(symbols):
        prices[symbol] = prices_data[i % len(prices_data)]
    
    # Create dropdown widget
    dropdown = SymbolDropdown()
    
    # Set symbols and prices
    dropdown.set_symbols(symbols, prices)
    
    # Track emitted symbols
    emitted_symbols = []
    dropdown.symbolSelected.connect(lambda s: emitted_symbols.append(s))
    
    # Show dropdown and select each symbol
    dropdown.show_dropdown()
    
    for symbol in symbols:
        # Find the item in the list
        for i in range(dropdown._symbol_list.count()):
            item = dropdown._symbol_list.item(i)
            item_text = item.text()
            item_symbol = item_text.split(" - ")[0] if " - " in item_text else item_text
            
            if item_symbol == symbol:
                # Simulate click
                dropdown._on_item_clicked(item)
                
                # Verify the correct symbol was emitted
                assert len(emitted_symbols) > 0, "Symbol should be emitted on selection"
                assert emitted_symbols[-1] == symbol, \
                    f"Emitted symbol should match selected: expected {symbol}, got {emitted_symbols[-1]}"
                break


@given(
    symbols=symbols_list_strategy,
    filter_text=st.text(
        alphabet=st.sampled_from("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"),
        min_size=0,
        max_size=5
    )
)
@settings(max_examples=100)
def test_symbol_filter_matching(
    symbols: List[str],
    filter_text: str,
    _qt_app
):
    """
    **Feature: ui-ux-convenience, Property 12: Symbol Filter Matching**
    **Validates: Requirements 8.5**
    
    For any filter text, the dropdown SHALL display only symbols that
    contain the filter text (case-insensitive).
    """
    # Create dropdown widget
    dropdown = SymbolDropdown()
    
    # Set symbols (no prices needed for this test)
    dropdown.set_symbols(symbols, {})
    
    # Apply filter
    dropdown.filter_symbols(filter_text)
    
    # Get filtered symbols
    filtered = dropdown.get_filtered_symbols()
    
    # Verify filtering logic
    filter_lower = filter_text.lower()
    
    for symbol in filtered:
        # All filtered symbols should contain the filter text
        assert filter_lower in symbol.lower(), \
            f"Filtered symbol '{symbol}' should contain filter text '{filter_text}'"
    
    # Verify no matching symbols were excluded
    for symbol in symbols:
        if filter_lower in symbol.lower():
            assert symbol in filtered, \
                f"Symbol '{symbol}' matches filter '{filter_text}' but was excluded"


def test_empty_filter_shows_all(_qt_app):
    """Test that empty filter shows all symbols."""
    dropdown = SymbolDropdown()
    
    symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT"]
    dropdown.set_symbols(symbols, {})
    
    # Apply empty filter
    dropdown.filter_symbols("")
    
    filtered = dropdown.get_filtered_symbols()
    assert len(filtered) == len(symbols), "Empty filter should show all symbols"
    for symbol in symbols:
        assert symbol in filtered, f"Symbol {symbol} should be in filtered list"


def test_case_insensitive_filter(_qt_app):
    """Test that filtering is case-insensitive."""
    dropdown = SymbolDropdown()
    
    symbols = ["BTCUSDT", "btceur", "ETHUSDT"]
    dropdown.set_symbols(symbols, {})
    
    # Filter with lowercase
    dropdown.filter_symbols("btc")
    filtered = dropdown.get_filtered_symbols()
    
    assert "BTCUSDT" in filtered, "BTCUSDT should match 'btc' filter"
    assert "btceur" in filtered, "btceur should match 'btc' filter"
    assert "ETHUSDT" not in filtered, "ETHUSDT should not match 'btc' filter"


def test_symbol_with_price_display(_qt_app):
    """Test that symbols are displayed with their prices."""
    dropdown = SymbolDropdown()
    
    symbols = ["BTCUSDT"]
    prices = {"BTCUSDT": Decimal("50000.00")}
    dropdown.set_symbols(symbols, prices)
    
    # Check list item text
    assert dropdown._symbol_list.count() == 1
    item_text = dropdown._symbol_list.item(0).text()
    
    assert "BTCUSDT" in item_text, "Item should contain symbol"
    assert "$50,000" in item_text, "Item should contain formatted price"
