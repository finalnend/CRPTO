"""Performance analytics for paper trading."""

import csv
from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, List

from .models import Transaction


@dataclass
class PerformanceMetrics:
    """Performance metrics for trading activity.
    
    Attributes:
        total_trades: Total number of completed sell trades
        profitable_trades: Number of trades with positive PnL
        win_rate: Percentage of profitable trades (0-100)
        realized_pnl: Total realized profit/loss from closed positions
        total_volume: Total trading volume (sum of all transaction values)
    """
    total_trades: int
    profitable_trades: int
    win_rate: Decimal
    realized_pnl: Decimal
    total_volume: Decimal


class IPerformanceAnalytics(ABC):
    """Interface for performance analytics operations."""

    @abstractmethod
    def calculate_metrics(self, transactions: List[Transaction]) -> PerformanceMetrics:
        """Calculate comprehensive performance metrics from transactions.
        
        Args:
            transactions: List of all transactions
            
        Returns:
            PerformanceMetrics with calculated values
        """
        ...

    @abstractmethod
    def calculate_realized_pnl(self, transactions: List[Transaction]) -> Decimal:
        """Calculate total realized PnL from all closed positions.
        
        Args:
            transactions: List of all transactions
            
        Returns:
            Total realized profit/loss
        """
        ...

    @abstractmethod
    def export_to_csv(self, transactions: List[Transaction], filepath: str) -> None:
        """Export transaction history to CSV file.
        
        Args:
            transactions: List of transactions to export
            filepath: Path to output CSV file
        """
        ...

    @abstractmethod
    def sort_transactions_by_timestamp(
        self, transactions: List[Transaction], descending: bool = True
    ) -> List[Transaction]:
        """Sort transactions by timestamp.
        
        Args:
            transactions: List of transactions to sort
            descending: If True, most recent first (default)
            
        Returns:
            Sorted list of transactions
        """
        ...


class PerformanceAnalytics(IPerformanceAnalytics):
    """Concrete implementation of performance analytics.
    
    Tracks cost basis per symbol using FIFO method to calculate
    realized PnL on sell transactions.
    """

    def calculate_metrics(self, transactions: List[Transaction]) -> PerformanceMetrics:
        """Calculate comprehensive performance metrics from transactions.
        
        Args:
            transactions: List of all transactions
            
        Returns:
            PerformanceMetrics with calculated values
        """
        realized_pnl = self.calculate_realized_pnl(transactions)
        total_volume = sum(txn.total_value for txn in transactions)
        
        # Calculate trade statistics from sell transactions
        sell_pnls = self._calculate_per_trade_pnl(transactions)
        total_trades = len(sell_pnls)
        profitable_trades = sum(1 for pnl in sell_pnls if pnl > Decimal("0"))
        
        if total_trades > 0:
            win_rate = (Decimal(profitable_trades) / Decimal(total_trades)) * Decimal("100")
        else:
            win_rate = Decimal("0")
        
        return PerformanceMetrics(
            total_trades=total_trades,
            profitable_trades=profitable_trades,
            win_rate=win_rate,
            realized_pnl=realized_pnl,
            total_volume=total_volume
        )

    def calculate_realized_pnl(self, transactions: List[Transaction]) -> Decimal:
        """Calculate total realized PnL from all closed positions.
        
        Uses FIFO method to track cost basis per symbol.
        
        Args:
            transactions: List of all transactions
            
        Returns:
            Total realized profit/loss
        """
        sell_pnls = self._calculate_per_trade_pnl(transactions)
        return sum(sell_pnls, Decimal("0"))

    def _calculate_per_trade_pnl(self, transactions: List[Transaction]) -> List[Decimal]:
        """Calculate PnL for each sell transaction.
        
        Tracks cost basis per symbol using weighted average cost method.
        
        Args:
            transactions: List of all transactions
            
        Returns:
            List of PnL values for each sell transaction
        """
        # Track cost basis per symbol: {symbol: (total_quantity, total_cost)}
        cost_basis: Dict[str, tuple] = {}
        sell_pnls: List[Decimal] = []
        
        # Sort by timestamp to process in order
        sorted_txns = sorted(transactions, key=lambda t: t.timestamp)
        
        for txn in sorted_txns:
            symbol = txn.symbol
            
            if txn.order_type == "BUY":
                # Add to cost basis
                if symbol in cost_basis:
                    qty, cost = cost_basis[symbol]
                    new_qty = qty + txn.quantity
                    new_cost = cost + txn.total_value
                    cost_basis[symbol] = (new_qty, new_cost)
                else:
                    cost_basis[symbol] = (txn.quantity, txn.total_value)
                    
            elif txn.order_type == "SELL":
                # Calculate PnL based on average cost
                if symbol in cost_basis and cost_basis[symbol][0] > Decimal("0"):
                    qty, cost = cost_basis[symbol]
                    avg_cost = cost / qty
                    
                    # PnL = (sell_price - avg_cost) * sell_quantity
                    pnl = (txn.price - avg_cost) * txn.quantity
                    sell_pnls.append(pnl)
                    
                    # Update cost basis
                    remaining_qty = qty - txn.quantity
                    if remaining_qty > Decimal("0"):
                        remaining_cost = avg_cost * remaining_qty
                        cost_basis[symbol] = (remaining_qty, remaining_cost)
                    else:
                        cost_basis[symbol] = (Decimal("0"), Decimal("0"))
                else:
                    # Sell without prior buy (shouldn't happen in normal flow)
                    sell_pnls.append(Decimal("0"))
        
        return sell_pnls

    def sort_transactions_by_timestamp(
        self, transactions: List[Transaction], descending: bool = True
    ) -> List[Transaction]:
        """Sort transactions by timestamp.
        
        Args:
            transactions: List of transactions to sort
            descending: If True, most recent first (default)
            
        Returns:
            Sorted list of transactions
        """
        return sorted(transactions, key=lambda t: t.timestamp, reverse=descending)

    def export_to_csv(self, transactions: List[Transaction], filepath: str) -> None:
        """Export transaction history to CSV file.
        
        Args:
            transactions: List of transactions to export
            filepath: Path to output CSV file
        """
        fieldnames = ["id", "symbol", "order_type", "quantity", "price", "total_value", "timestamp"]
        
        with open(filepath, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for txn in transactions:
                writer.writerow({
                    "id": txn.id,
                    "symbol": txn.symbol,
                    "order_type": txn.order_type,
                    "quantity": str(txn.quantity),
                    "price": str(txn.price),
                    "total_value": str(txn.total_value),
                    "timestamp": txn.timestamp.isoformat()
                })
