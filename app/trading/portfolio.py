"""Portfolio management for paper trading."""

from abc import ABC, abstractmethod
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional

from .models import Position, Transaction


class IPortfolioManager(ABC):
    """Interface for portfolio management operations."""

    @abstractmethod
    def get_balance(self) -> Decimal:
        """Get current available cash balance."""
        ...

    @abstractmethod
    def get_positions(self) -> Dict[str, Position]:
        """Get all current positions."""
        ...

    @abstractmethod
    def get_position(self, symbol: str) -> Optional[Position]:
        """Get position for a specific symbol."""
        ...

    @abstractmethod
    def get_portfolio_value(self, prices: Dict[str, Decimal]) -> Decimal:
        """Calculate total portfolio value including cash and positions."""
        ...

    @abstractmethod
    def get_unrealized_pnl(self, symbol: str, current_price: Decimal) -> Decimal:
        """Calculate unrealized PnL for a specific position."""
        ...

    @abstractmethod
    def execute_buy(self, symbol: str, quantity: Decimal, price: Decimal) -> Transaction:
        """Execute a buy order and update portfolio."""
        ...

    @abstractmethod
    def execute_sell(self, symbol: str, quantity: Decimal, price: Decimal) -> Transaction:
        """Execute a sell order and update portfolio."""
        ...

    @abstractmethod
    def reset(self, initial_balance: Decimal) -> None:
        """Reset portfolio to initial state."""
        ...

    @abstractmethod
    def get_transactions(self) -> List[Transaction]:
        """Get all transaction history."""
        ...


class PortfolioManager(IPortfolioManager):
    """Concrete implementation of portfolio management.
    
    Uses weighted average cost method for position tracking.
    """

    def __init__(self, initial_balance: Decimal = Decimal("10000")) -> None:
        """Initialize portfolio with starting balance.
        
        Args:
            initial_balance: Starting cash balance (default: 10,000 USD)
        """
        self._initial_balance = initial_balance
        self._balance = initial_balance
        self._positions: Dict[str, Position] = {}
        self._transactions: List[Transaction] = []

    def get_balance(self) -> Decimal:
        """Get current available cash balance."""
        return self._balance

    def get_positions(self) -> Dict[str, Position]:
        """Get all current positions."""
        return self._positions.copy()

    def get_position(self, symbol: str) -> Optional[Position]:
        """Get position for a specific symbol."""
        return self._positions.get(symbol)

    def get_portfolio_value(self, prices: Dict[str, Decimal]) -> Decimal:
        """Calculate total portfolio value including cash and positions.
        
        Args:
            prices: Dictionary mapping symbols to current prices
            
        Returns:
            Total portfolio value (cash + sum of position values)
        """
        total = self._balance
        for symbol, position in self._positions.items():
            if symbol in prices:
                total += position.quantity * prices[symbol]
            else:
                # Use cost basis if no current price available
                total += position.total_cost
        return total

    def get_unrealized_pnl(self, symbol: str, current_price: Decimal) -> Decimal:
        """Calculate unrealized PnL for a specific position.
        
        Args:
            symbol: Trading pair symbol
            current_price: Current market price
            
        Returns:
            Unrealized profit/loss (can be negative)
        """
        position = self._positions.get(symbol)
        if position is None:
            return Decimal("0")
        current_value = position.quantity * current_price
        cost_basis = position.total_cost
        return current_value - cost_basis

    def execute_buy(self, symbol: str, quantity: Decimal, price: Decimal) -> Transaction:
        """Execute a buy order and update portfolio.
        
        Updates balance, creates/updates position with weighted average cost.
        
        Args:
            symbol: Trading pair symbol
            quantity: Amount to buy
            price: Execution price per unit
            
        Returns:
            Transaction record for the executed order
        """
        order_value = quantity * price
        self._balance -= order_value

        # Update or create position with weighted average cost
        existing = self._positions.get(symbol)
        if existing:
            total_quantity = existing.quantity + quantity
            total_cost = existing.total_cost + order_value
            new_avg_cost = total_cost / total_quantity
            self._positions[symbol] = Position(
                symbol=symbol,
                quantity=total_quantity,
                average_cost=new_avg_cost
            )
        else:
            self._positions[symbol] = Position(
                symbol=symbol,
                quantity=quantity,
                average_cost=price
            )

        transaction = Transaction(
            symbol=symbol,
            order_type="BUY",
            quantity=quantity,
            price=price,
            timestamp=datetime.now()
        )
        self._transactions.append(transaction)
        return transaction

    def execute_sell(self, symbol: str, quantity: Decimal, price: Decimal) -> Transaction:
        """Execute a sell order and update portfolio.
        
        Updates balance and reduces position quantity.
        Average cost remains unchanged for remaining shares.
        
        Args:
            symbol: Trading pair symbol
            quantity: Amount to sell
            price: Execution price per unit
            
        Returns:
            Transaction record for the executed order
        """
        order_value = quantity * price
        self._balance += order_value

        # Update position
        position = self._positions[symbol]
        new_quantity = position.quantity - quantity
        
        if new_quantity == Decimal("0"):
            del self._positions[symbol]
        else:
            self._positions[symbol] = Position(
                symbol=symbol,
                quantity=new_quantity,
                average_cost=position.average_cost
            )

        transaction = Transaction(
            symbol=symbol,
            order_type="SELL",
            quantity=quantity,
            price=price,
            timestamp=datetime.now()
        )
        self._transactions.append(transaction)
        return transaction

    def reset(self, initial_balance: Decimal) -> None:
        """Reset portfolio to initial state.
        
        Clears all positions and transactions, sets balance to specified amount.
        
        Args:
            initial_balance: New starting balance
        """
        self._initial_balance = initial_balance
        self._balance = initial_balance
        self._positions.clear()
        self._transactions.clear()

    def get_transactions(self) -> List[Transaction]:
        """Get all transaction history."""
        return self._transactions.copy()

    def get_initial_balance(self) -> Decimal:
        """Get the initial balance the portfolio was created with."""
        return self._initial_balance



class PortfolioSerializer:
    """Serializer for portfolio state to/from JSON-compatible dictionaries."""

    @staticmethod
    def serialize(portfolio: IPortfolioManager) -> dict:
        """Serialize portfolio state to a JSON-compatible dictionary.
        
        Args:
            portfolio: Portfolio manager instance to serialize
            
        Returns:
            Dictionary containing serialized portfolio state
        """
        positions = {}
        for symbol, position in portfolio.get_positions().items():
            positions[symbol] = {
                "symbol": position.symbol,
                "quantity": str(position.quantity),
                "average_cost": str(position.average_cost)
            }
        
        transactions = []
        for txn in portfolio.get_transactions():
            transactions.append({
                "id": txn.id,
                "symbol": txn.symbol,
                "order_type": txn.order_type,
                "quantity": str(txn.quantity),
                "price": str(txn.price),
                "timestamp": txn.timestamp.isoformat()
            })
        
        return {
            "balance": str(portfolio.get_balance()),
            "initial_balance": str(portfolio.get_initial_balance()),
            "positions": positions,
            "transactions": transactions,
            "created_at": datetime.now().isoformat()
        }

    @staticmethod
    def deserialize(data: dict) -> "PortfolioManager":
        """Deserialize portfolio state from a dictionary.
        
        Args:
            data: Dictionary containing serialized portfolio state
            
        Returns:
            Restored PortfolioManager instance
        """
        initial_balance = Decimal(data["initial_balance"])
        portfolio = PortfolioManager(initial_balance)
        
        # Restore balance (may differ from initial due to trades)
        portfolio._balance = Decimal(data["balance"])
        
        # Restore positions
        for symbol, pos_data in data.get("positions", {}).items():
            portfolio._positions[symbol] = Position(
                symbol=pos_data["symbol"],
                quantity=Decimal(pos_data["quantity"]),
                average_cost=Decimal(pos_data["average_cost"])
            )
        
        # Restore transactions
        for txn_data in data.get("transactions", []):
            portfolio._transactions.append(Transaction(
                id=txn_data["id"],
                symbol=txn_data["symbol"],
                order_type=txn_data["order_type"],
                quantity=Decimal(txn_data["quantity"]),
                price=Decimal(txn_data["price"]),
                timestamp=datetime.fromisoformat(txn_data["timestamp"])
            ))
        
        return portfolio
