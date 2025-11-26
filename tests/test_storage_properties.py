"""Property-based tests for storage module.

Tests the storage service round-trip properties using Hypothesis.
"""

from __future__ import annotations

import tempfile
from decimal import Decimal
from datetime import datetime
from typing import Any, Dict, List

import pytest
from hypothesis import given, settings, strategies as st

from app.storage import JsonFileStorage


# Strategy for generating portfolio-like data structures
# This mirrors the PortfolioState structure from the design document
@st.composite
def portfolio_state_strategy(draw):
    """Generate portfolio state data that mirrors the actual portfolio structure."""
    
    # Generate positions
    num_positions = draw(st.integers(min_value=0, max_value=10))
    positions = {}
    for _ in range(num_positions):
        symbol = draw(st.sampled_from(["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "ADAUSDT"]))
        if symbol not in positions:
            positions[symbol] = {
                "symbol": symbol,
                "quantity": str(draw(st.decimals(
                    min_value=Decimal("0.001"),
                    max_value=Decimal("1000"),
                    places=8
                ))),
                "average_cost": str(draw(st.decimals(
                    min_value=Decimal("0.01"),
                    max_value=Decimal("100000"),
                    places=2
                )))
            }
    
    # Generate transactions
    num_transactions = draw(st.integers(min_value=0, max_value=20))
    transactions = []
    for i in range(num_transactions):
        transactions.append({
            "id": f"txn-{i}-{draw(st.uuids())}",
            "symbol": draw(st.sampled_from(["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT"])),
            "order_type": draw(st.sampled_from(["BUY", "SELL"])),
            "quantity": str(draw(st.decimals(
                min_value=Decimal("0.001"),
                max_value=Decimal("100"),
                places=8
            ))),
            "price": str(draw(st.decimals(
                min_value=Decimal("0.01"),
                max_value=Decimal("100000"),
                places=2
            ))),
            "timestamp": datetime.now().isoformat()
        })
    
    balance = draw(st.decimals(
        min_value=Decimal("0"),
        max_value=Decimal("10000000"),
        places=2
    ))
    
    initial_balance = draw(st.decimals(
        min_value=Decimal("1000"),
        max_value=Decimal("10000000"),
        places=2
    ))
    
    return {
        "balance": str(balance),
        "positions": positions,
        "transactions": transactions,
        "initial_balance": str(initial_balance),
        "created_at": datetime.now().isoformat()
    }


@given(portfolio_data=portfolio_state_strategy())
@settings(max_examples=100)
def test_portfolio_serialization_round_trip(portfolio_data: Dict[str, Any]):
    """
    **Feature: modern-ui-market-sim, Property 16: Portfolio serialization round-trip**
    **Validates: Requirements 8.1, 8.2, 8.3**
    
    For any valid portfolio state, serializing to JSON and then deserializing
    SHALL produce an equivalent portfolio with the same balance, positions,
    and transactions.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = JsonFileStorage(tmpdir)
        key = "test_portfolio"
        
        # Save (serialize) the portfolio data
        storage.save(key, portfolio_data)
        
        # Load (deserialize) the portfolio data
        loaded_data = storage.load(key)
        
        # Verify round-trip produces equivalent data
        assert loaded_data is not None, "Loaded data should not be None"
        assert loaded_data["balance"] == portfolio_data["balance"], "Balance should match"
        assert loaded_data["initial_balance"] == portfolio_data["initial_balance"], "Initial balance should match"
        assert loaded_data["created_at"] == portfolio_data["created_at"], "Created timestamp should match"
        
        # Verify positions match
        assert len(loaded_data["positions"]) == len(portfolio_data["positions"]), "Position count should match"
        for symbol, position in portfolio_data["positions"].items():
            assert symbol in loaded_data["positions"], f"Position {symbol} should exist"
            loaded_pos = loaded_data["positions"][symbol]
            assert loaded_pos["symbol"] == position["symbol"], "Position symbol should match"
            assert loaded_pos["quantity"] == position["quantity"], "Position quantity should match"
            assert loaded_pos["average_cost"] == position["average_cost"], "Position average cost should match"
        
        # Verify transactions match
        assert len(loaded_data["transactions"]) == len(portfolio_data["transactions"]), "Transaction count should match"
        for i, txn in enumerate(portfolio_data["transactions"]):
            loaded_txn = loaded_data["transactions"][i]
            assert loaded_txn["id"] == txn["id"], "Transaction ID should match"
            assert loaded_txn["symbol"] == txn["symbol"], "Transaction symbol should match"
            assert loaded_txn["order_type"] == txn["order_type"], "Transaction order type should match"
            assert loaded_txn["quantity"] == txn["quantity"], "Transaction quantity should match"
            assert loaded_txn["price"] == txn["price"], "Transaction price should match"
            assert loaded_txn["timestamp"] == txn["timestamp"], "Transaction timestamp should match"


@given(key=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('L', 'N'))))
@settings(max_examples=100)
def test_storage_delete_removes_data(key: str):
    """Test that delete properly removes stored data."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = JsonFileStorage(tmpdir)
        test_data = {"test": "value"}
        
        # Save data
        storage.save(key, test_data)
        assert storage.load(key) == test_data
        
        # Delete data
        storage.delete(key)
        
        # Verify data is gone
        assert storage.load(key) is None


def test_storage_load_nonexistent_returns_none():
    """Test that loading a non-existent key returns None."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = JsonFileStorage(tmpdir)
        assert storage.load("nonexistent_key") is None
