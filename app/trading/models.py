"""Data models for paper trading."""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Literal
import uuid


@dataclass
class Position:
    """Represents a holding position in the portfolio.
    
    Attributes:
        symbol: Trading pair symbol (e.g., "BTCUSDT")
        quantity: Amount of asset held
        average_cost: Average purchase price per unit
    """
    symbol: str
    quantity: Decimal
    average_cost: Decimal

    @property
    def total_cost(self) -> Decimal:
        """Calculate total cost basis for this position."""
        return self.quantity * self.average_cost


@dataclass
class Transaction:
    """Represents a completed trade transaction.
    
    Attributes:
        id: Unique transaction identifier (UUID)
        symbol: Trading pair symbol
        order_type: Type of order ("BUY" or "SELL")
        quantity: Amount traded
        price: Execution price per unit
        timestamp: Time of execution
    """
    symbol: str
    order_type: Literal["BUY", "SELL"]
    quantity: Decimal
    price: Decimal
    timestamp: datetime = field(default_factory=datetime.now)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    @property
    def total_value(self) -> Decimal:
        """Calculate total value of this transaction."""
        return self.quantity * self.price
