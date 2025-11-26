"""Utility classes for Paper Trading UI/UX convenience features.

This module provides:
- QuantityCalculator: Calculates order quantities based on presets
- ValidationState: Enum for input validation states
- InputValidator: Validates order inputs and returns validation state
"""

from decimal import Decimal, InvalidOperation, Overflow
from enum import Enum
from typing import Optional, Tuple


class QuantityCalculator:
    """Calculates order quantities based on presets and context.
    
    Provides static methods for calculating buy and sell quantities
    based on percentage presets (25%, 50%, 75%, 100%).
    """

    @staticmethod
    def calculate_buy_quantity(
        balance: Decimal,
        price: Decimal,
        percentage: float,
    ) -> Decimal:
        """Calculate buy quantity from balance percentage.
        
        Formula: quantity = (balance * percentage) / price
        
        Args:
            balance: Available balance in quote currency
            price: Current price per unit
            percentage: Percentage as decimal (0.25, 0.5, 0.75, 1.0)
            
        Returns:
            Calculated quantity as Decimal
            
        Raises:
            ValueError: If price is zero or negative, or if percentage is invalid
        """
        if price <= Decimal("0"):
            raise ValueError("Price must be greater than zero")
        if percentage < 0 or percentage > 1:
            raise ValueError("Percentage must be between 0 and 1")
        if balance < Decimal("0"):
            raise ValueError("Balance cannot be negative")
        
        return (balance * Decimal(str(percentage))) / price

    @staticmethod
    def calculate_sell_quantity(
        position_size: Decimal,
        percentage: float,
    ) -> Decimal:
        """Calculate sell quantity from position percentage.
        
        Formula: quantity = position_size * percentage
        
        Args:
            position_size: Current position size
            percentage: Percentage as decimal (0.25, 0.5, 0.75, 1.0)
            
        Returns:
            Calculated quantity as Decimal
            
        Raises:
            ValueError: If percentage is invalid or position_size is negative
        """
        if percentage < 0 or percentage > 1:
            raise ValueError("Percentage must be between 0 and 1")
        if position_size < Decimal("0"):
            raise ValueError("Position size cannot be negative")
        
        return position_size * Decimal(str(percentage))


class ValidationState(Enum):
    """Input validation states."""
    VALID = "valid"           # Green border
    WARNING = "warning"       # Orange border (exceeds limits but valid format)
    INVALID = "invalid"       # Red border (invalid format)
    NEUTRAL = "neutral"       # Default border (empty/no validation)


class InputValidator:
    """Validates order inputs and returns validation state.
    
    Provides validation for quantity inputs with appropriate
    visual feedback states (valid, warning, invalid, neutral).
    """

    def validate_quantity(
        self,
        quantity_str: str,
        order_type: str,  # "BUY" or "SELL"
        balance: Decimal,
        position_size: Decimal,
        current_price: Optional[Decimal],
    ) -> Tuple[ValidationState, str]:
        """Validate quantity input.
        
        Args:
            quantity_str: The quantity input as string
            order_type: Type of order ("BUY" or "SELL")
            balance: Available balance in quote currency
            position_size: Current position size for the symbol
            current_price: Current price per unit (None if unavailable)
            
        Returns:
            Tuple of (ValidationState, message)
        """
        # Handle empty input
        if not quantity_str or quantity_str.strip() == "":
            return (ValidationState.NEUTRAL, "")
        
        # Try to parse the quantity
        try:
            quantity = Decimal(quantity_str.strip())
        except InvalidOperation:
            return (ValidationState.INVALID, "Invalid number format")
        
        # Check for negative or zero values
        if quantity <= Decimal("0"):
            return (ValidationState.INVALID, "Quantity must be greater than zero")
        
        # For BUY orders, check against balance
        if order_type.upper() == "BUY":
            if current_price is None:
                return (ValidationState.WARNING, "Price data unavailable")
            
            try:
                order_value = quantity * current_price
            except (Overflow, InvalidOperation):
                return (ValidationState.INVALID, "Quantity too large")
            
            if order_value > balance:
                return (
                    ValidationState.WARNING,
                    f"Exceeds available balance ({balance})"
                )
        
        # For SELL orders, check against position
        elif order_type.upper() == "SELL":
            if quantity > position_size:
                return (
                    ValidationState.WARNING,
                    f"Exceeds position size ({position_size})"
                )
        
        return (ValidationState.VALID, "")
