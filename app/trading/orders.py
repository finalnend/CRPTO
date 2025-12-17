"""Order service for paper trading.

This module provides order execution functionality including:
- Order status and rejection reason enums
- OrderResult dataclass for order outcomes
- IDataProvider interface for price data abstraction
- OrderService for submitting buy/sell orders
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Optional

from .models import Transaction
from .portfolio import IPortfolioManager


class OrderStatus(Enum):
    """Status of an order after submission."""
    PENDING = "pending"
    EXECUTED = "executed"
    REJECTED = "rejected"


class OrderRejectionReason(Enum):
    """Reason for order rejection."""
    INSUFFICIENT_BALANCE = "insufficient_balance"
    INSUFFICIENT_HOLDINGS = "insufficient_holdings"
    INVALID_QUANTITY = "invalid_quantity"
    NO_PRICE_DATA = "no_price_data"


@dataclass
class OrderResult:
    """Result of an order submission.
    
    Attributes:
        status: The status of the order (PENDING, EXECUTED, REJECTED)
        transaction: The transaction record if order was executed
        rejection_reason: The reason for rejection if order was rejected
        message: Human-readable message describing the result
    """
    status: OrderStatus
    transaction: Optional[Transaction] = None
    rejection_reason: Optional[OrderRejectionReason] = None
    message: str = ""


class IDataProvider(ABC):
    """Interface for market data providers.
    
    Abstracts the data source for order execution, allowing
    the OrderService to work with any data provider implementation.
    """

    @abstractmethod
    def get_current_price(self, symbol: str) -> Optional[Decimal]:
        """Get the current price for a symbol.
        
        Args:
            symbol: Trading pair symbol (e.g., "BTCUSDT")
            
        Returns:
            Current price as Decimal, or None if unavailable
        """
        ...

    @abstractmethod
    def is_connected(self) -> bool:
        """Check if the data provider is connected.
        
        Returns:
            True if connected and receiving data, False otherwise
        """
        ...


class IOrderService(ABC):
    """Interface for order submission service."""

    @abstractmethod
    def submit_buy(self, symbol: str, quantity: Decimal) -> OrderResult:
        """Submit a buy order.
        
        Args:
            symbol: Trading pair symbol
            quantity: Amount to buy
            
        Returns:
            OrderResult with execution status
        """
        ...

    @abstractmethod
    def submit_sell(self, symbol: str, quantity: Decimal) -> OrderResult:
        """Submit a sell order.
        
        Args:
            symbol: Trading pair symbol
            quantity: Amount to sell
            
        Returns:
            OrderResult with execution status
        """
        ...


class OrderService(IOrderService):
    """Order execution service for paper trading.
    
    Validates orders against portfolio state and executes them
    using current market prices from the data provider.
    """

    def __init__(self, portfolio: IPortfolioManager, data_provider: IDataProvider) -> None:
        """Initialize order service.
        
        Args:
            portfolio: Portfolio manager for balance/holdings management
            data_provider: Data provider for current price lookup
        """
        self._portfolio = portfolio
        self._data_provider = data_provider

    def submit_buy(self, symbol: str, quantity: Decimal) -> OrderResult:
        """Submit a buy order.
        
        Validates sufficient balance before execution.
        
        Args:
            symbol: Trading pair symbol
            quantity: Amount to buy
            
        Returns:
            OrderResult with EXECUTED status if successful,
            REJECTED status with reason if validation fails
        """
        # Validate quantity
        if quantity <= Decimal("0"):
            return OrderResult(
                status=OrderStatus.REJECTED,
                rejection_reason=OrderRejectionReason.INVALID_QUANTITY,
                message="Quantity must be greater than zero"
            )

        # Get current price
        price = self._data_provider.get_current_price(symbol)
        if price is None:
            return OrderResult(
                status=OrderStatus.REJECTED,
                rejection_reason=OrderRejectionReason.NO_PRICE_DATA,
                message=f"No price data available for {symbol}"
            )

        # Calculate order value and validate balance
        order_value = quantity * price
        available_balance = self._portfolio.get_balance()

        if order_value > available_balance:
            return OrderResult(
                status=OrderStatus.REJECTED,
                rejection_reason=OrderRejectionReason.INSUFFICIENT_BALANCE,
                message=f"Insufficient balance: need {order_value}, have {available_balance}"
            )

        # Execute the buy order
        transaction = self._portfolio.execute_buy(symbol, quantity, price)
        return OrderResult(
            status=OrderStatus.EXECUTED,
            transaction=transaction,
            message=f"Bought {quantity} {symbol} at {price}"
        )

    def submit_sell(self, symbol: str, quantity: Decimal) -> OrderResult:
        """Submit a sell order.
        
        Validates sufficient holdings before execution.
        
        Args:
            symbol: Trading pair symbol
            quantity: Amount to sell
            
        Returns:
            OrderResult with EXECUTED status if successful,
            REJECTED status with reason if validation fails
        """
        # Validate quantity
        if quantity <= Decimal("0"):
            return OrderResult(
                status=OrderStatus.REJECTED,
                rejection_reason=OrderRejectionReason.INVALID_QUANTITY,
                message="Quantity must be greater than zero"
            )

        # Get current price
        price = self._data_provider.get_current_price(symbol)
        if price is None:
            return OrderResult(
                status=OrderStatus.REJECTED,
                rejection_reason=OrderRejectionReason.NO_PRICE_DATA,
                message=f"No price data available for {symbol}"
            )

        # Validate holdings
        position = self._portfolio.get_position(symbol)
        held_quantity = position.quantity if position else Decimal("0")

        if quantity > held_quantity:
            return OrderResult(
                status=OrderStatus.REJECTED,
                rejection_reason=OrderRejectionReason.INSUFFICIENT_HOLDINGS,
                message=f"Insufficient holdings: need {quantity}, have {held_quantity}"
            )

        # Execute the sell order
        transaction = self._portfolio.execute_sell(symbol, quantity, price)
        return OrderResult(
            status=OrderStatus.EXECUTED,
            transaction=transaction,
            message=f"Sold {quantity} {symbol} at {price}"
        )



class BinanceDataProviderAdapter(IDataProvider):
    """Adapter to wrap existing Binance data sources as IDataProvider.
    
    Can use either WebSocket client for real-time prices or REST provider
    for on-demand price fetching.
    """

    def __init__(self) -> None:
        """Initialize the adapter with empty price cache."""
        self._prices: dict[str, Decimal] = {}
        self._connected: bool = False

    def update_price(self, symbol: str, price: float) -> None:
        """Update cached price for a symbol.
        
        Called by WebSocket client when new tick data arrives.
        
        Args:
            symbol: Trading pair symbol
            price: Current price as float
        """
        self._prices[symbol.upper()] = Decimal(str(price))

    def set_connected(self, connected: bool) -> None:
        """Update connection status.
        
        Args:
            connected: True if connected, False otherwise
        """
        self._connected = connected

    def get_current_price(self, symbol: str) -> Optional[Decimal]:
        """Get the current price for a symbol from cache.
        
        Args:
            symbol: Trading pair symbol
            
        Returns:
            Cached price as Decimal, or None if not available
        """
        return self._prices.get(symbol.upper())

    def is_connected(self) -> bool:
        """Check if the data provider is connected.
        
        Returns:
            True if connected and receiving data
        """
        return self._connected

    def get_prices_snapshot(self) -> dict[str, Decimal]:
        """Get a shallow copy of the current price cache."""
        return dict(self._prices)
