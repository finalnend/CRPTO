"""Property-based tests for performance analytics module.

Tests the analytics correctness properties using Hypothesis.
"""

from __future__ import annotations

import csv
import os
import tempfile
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List

import pytest
from hypothesis import given, settings, strategies as st, assume

from app.trading.analytics import PerformanceAnalytics, PerformanceMetrics
from app.trading.models import Transaction


# Strategies for generating valid test data
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

order_type_strategy = st.sampled_from(["BUY", "SELL"])


@st.composite
def transaction_strategy(draw):
    """Generate a valid transaction."""
    return Transaction(
        symbol=draw(symbol_strategy),
        order_type=draw(order_type_strategy),
        quantity=draw(positive_quantity_strategy),
        price=draw(positive_price_strategy),
        timestamp=draw(st.datetimes(
            min_value=datetime(2020, 1, 1),
            max_value=datetime(2025, 12, 31)
        ))
    )


@st.composite
def transaction_list_strategy(draw, min_size=0, max_size=20):
    """Generate a list of transactions."""
    return draw(st.lists(transaction_strategy(), min_size=min_size, max_size=max_size))


@st.composite
def buy_sell_pair_strategy(draw):
    """Generate a valid buy-sell pair for a symbol (buy first, then sell)."""
    symbol = draw(symbol_strategy)
    buy_quantity = draw(positive_quantity_strategy)
    buy_price = draw(positive_price_strategy)
    sell_price = draw(positive_price_strategy)
    
    # Sell quantity must be <= buy quantity
    sell_quantity = draw(st.decimals(
        min_value=Decimal("0.001"),
        max_value=buy_quantity,
        places=8,
        allow_nan=False,
        allow_infinity=False
    ))
    
    base_time = draw(st.datetimes(
        min_value=datetime(2020, 1, 1),
        max_value=datetime(2025, 6, 1)
    ))
    
    buy_txn = Transaction(
        symbol=symbol,
        order_type="BUY",
        quantity=buy_quantity,
        price=buy_price,
        timestamp=base_time
    )
    
    sell_txn = Transaction(
        symbol=symbol,
        order_type="SELL",
        quantity=sell_quantity,
        price=sell_price,
        timestamp=base_time + timedelta(days=draw(st.integers(min_value=1, max_value=180)))
    )
    
    return [buy_txn, sell_txn]


@given(transactions=transaction_list_strategy(min_size=0, max_size=20))
@settings(max_examples=100)
def test_trade_history_sorting(transactions: List[Transaction]):
    """
    **Feature: modern-ui-market-sim, Property 11: Trade history sorting**
    **Validates: Requirements 6.1**
    
    For any list of transactions, the sorted history SHALL have each
    transaction's timestamp greater than or equal to the next transaction's
    timestamp (descending order).
    """
    analytics = PerformanceAnalytics()
    
    sorted_txns = analytics.sort_transactions_by_timestamp(transactions, descending=True)
    
    # Verify descending order
    for i in range(len(sorted_txns) - 1):
        assert sorted_txns[i].timestamp >= sorted_txns[i + 1].timestamp, \
            f"Transaction at index {i} should have timestamp >= transaction at index {i + 1}"
    
    # Verify all original transactions are present
    assert len(sorted_txns) == len(transactions), \
        "Sorted list should have same length as original"
    
    original_ids = {t.id for t in transactions}
    sorted_ids = {t.id for t in sorted_txns}
    assert original_ids == sorted_ids, \
        "Sorted list should contain all original transactions"


@given(pairs=st.lists(buy_sell_pair_strategy(), min_size=1, max_size=5))
@settings(max_examples=100)
def test_realized_pnl_calculation(pairs: List[List[Transaction]]):
    """
    **Feature: modern-ui-market-sim, Property 12: Realized PnL calculation**
    **Validates: Requirements 6.2**
    
    For any sequence of buy and sell transactions for a symbol, the realized
    PnL SHALL equal the sum of (sell_price - average_cost) × sell_quantity
    for all sell transactions.
    """
    analytics = PerformanceAnalytics()
    
    # Flatten pairs into transaction list
    transactions = []
    for pair in pairs:
        transactions.extend(pair)
    
    # Calculate expected PnL manually
    # Track cost basis per symbol: {symbol: (total_quantity, total_cost)}
    cost_basis = {}
    expected_pnl = Decimal("0")
    
    # Sort by timestamp to process in order
    sorted_txns = sorted(transactions, key=lambda t: t.timestamp)
    
    for txn in sorted_txns:
        symbol = txn.symbol
        
        if txn.order_type == "BUY":
            if symbol in cost_basis:
                qty, cost = cost_basis[symbol]
                new_qty = qty + txn.quantity
                new_cost = cost + txn.total_value
                cost_basis[symbol] = (new_qty, new_cost)
            else:
                cost_basis[symbol] = (txn.quantity, txn.total_value)
                
        elif txn.order_type == "SELL":
            if symbol in cost_basis and cost_basis[symbol][0] > Decimal("0"):
                qty, cost = cost_basis[symbol]
                avg_cost = cost / qty
                
                # PnL = (sell_price - avg_cost) * sell_quantity
                pnl = (txn.price - avg_cost) * txn.quantity
                expected_pnl += pnl
                
                # Update cost basis
                remaining_qty = qty - txn.quantity
                if remaining_qty > Decimal("0"):
                    remaining_cost = avg_cost * remaining_qty
                    cost_basis[symbol] = (remaining_qty, remaining_cost)
                else:
                    cost_basis[symbol] = (Decimal("0"), Decimal("0"))
    
    calculated_pnl = analytics.calculate_realized_pnl(transactions)
    
    # Use approximate comparison due to potential decimal precision differences
    assert abs(calculated_pnl - expected_pnl) < Decimal("0.0001"), \
        f"Calculated PnL {calculated_pnl} should equal expected PnL {expected_pnl}"


@given(pairs=st.lists(buy_sell_pair_strategy(), min_size=0, max_size=10))
@settings(max_examples=100)
def test_win_rate_calculation(pairs: List[List[Transaction]]):
    """
    **Feature: modern-ui-market-sim, Property 13: Win rate calculation**
    **Validates: Requirements 6.3**
    
    For any set of completed trades, win rate SHALL equal
    (number of trades with positive PnL) / (total number of trades) × 100.
    """
    analytics = PerformanceAnalytics()
    
    # Flatten pairs into transaction list
    transactions = []
    for pair in pairs:
        transactions.extend(pair)
    
    metrics = analytics.calculate_metrics(transactions)
    
    # Calculate expected win rate manually
    # Track cost basis per symbol
    cost_basis = {}
    profitable_count = 0
    total_sell_count = 0
    
    sorted_txns = sorted(transactions, key=lambda t: t.timestamp)
    
    for txn in sorted_txns:
        symbol = txn.symbol
        
        if txn.order_type == "BUY":
            if symbol in cost_basis:
                qty, cost = cost_basis[symbol]
                new_qty = qty + txn.quantity
                new_cost = cost + txn.total_value
                cost_basis[symbol] = (new_qty, new_cost)
            else:
                cost_basis[symbol] = (txn.quantity, txn.total_value)
                
        elif txn.order_type == "SELL":
            total_sell_count += 1
            if symbol in cost_basis and cost_basis[symbol][0] > Decimal("0"):
                qty, cost = cost_basis[symbol]
                avg_cost = cost / qty
                pnl = (txn.price - avg_cost) * txn.quantity
                
                if pnl > Decimal("0"):
                    profitable_count += 1
                
                # Update cost basis
                remaining_qty = qty - txn.quantity
                if remaining_qty > Decimal("0"):
                    remaining_cost = avg_cost * remaining_qty
                    cost_basis[symbol] = (remaining_qty, remaining_cost)
                else:
                    cost_basis[symbol] = (Decimal("0"), Decimal("0"))
    
    if total_sell_count > 0:
        expected_win_rate = (Decimal(profitable_count) / Decimal(total_sell_count)) * Decimal("100")
    else:
        expected_win_rate = Decimal("0")
    
    assert metrics.total_trades == total_sell_count, \
        f"Total trades {metrics.total_trades} should equal sell count {total_sell_count}"
    assert metrics.profitable_trades == profitable_count, \
        f"Profitable trades {metrics.profitable_trades} should equal {profitable_count}"
    
    # Use approximate comparison for win rate
    assert abs(metrics.win_rate - expected_win_rate) < Decimal("0.01"), \
        f"Win rate {metrics.win_rate} should equal expected {expected_win_rate}"


@given(transactions=transaction_list_strategy(min_size=0, max_size=15))
@settings(max_examples=100)
def test_csv_export_completeness(transactions: List[Transaction]):
    """
    **Feature: modern-ui-market-sim, Property 14: CSV export completeness**
    **Validates: Requirements 6.4**
    
    For any list of transactions, the exported CSV SHALL contain exactly
    one row per transaction plus a header row, with all required fields present.
    """
    analytics = PerformanceAnalytics()
    
    # Create a temporary file for the CSV
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        temp_path = f.name
    
    try:
        # Export to CSV
        analytics.export_to_csv(transactions, temp_path)
        
        # Read and verify the CSV
        with open(temp_path, 'r', newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            rows = list(reader)
        
        # Verify row count (should equal transaction count)
        assert len(rows) == len(transactions), \
            f"CSV should have {len(transactions)} data rows, got {len(rows)}"
        
        # Verify all required fields are present in each row
        required_fields = ["id", "symbol", "order_type", "quantity", "price", "total_value", "timestamp"]
        
        for i, row in enumerate(rows):
            for field in required_fields:
                assert field in row, \
                    f"Row {i} missing required field '{field}'"
                assert row[field] is not None and row[field] != "", \
                    f"Row {i} has empty value for field '{field}'"
        
        # Verify transaction data matches
        txn_ids = {t.id for t in transactions}
        csv_ids = {row["id"] for row in rows}
        assert txn_ids == csv_ids, \
            "CSV should contain all transaction IDs"
            
    finally:
        # Clean up temp file
        if os.path.exists(temp_path):
            os.remove(temp_path)
