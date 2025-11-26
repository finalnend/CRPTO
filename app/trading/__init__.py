# Trading module
"""Paper trading components including portfolio management, order service, and analytics."""

from .models import Position, Transaction
from .portfolio import IPortfolioManager, PortfolioManager, PortfolioSerializer
from .orders import (
    OrderStatus,
    OrderRejectionReason,
    OrderResult,
    IDataProvider,
    IOrderService,
    OrderService,
    BinanceDataProviderAdapter,
)
from .analytics import (
    PerformanceMetrics,
    IPerformanceAnalytics,
    PerformanceAnalytics,
)

__all__ = [
    "Position",
    "Transaction",
    "IPortfolioManager",
    "PortfolioManager",
    "PortfolioSerializer",
    "OrderStatus",
    "OrderRejectionReason",
    "OrderResult",
    "IDataProvider",
    "IOrderService",
    "OrderService",
    "BinanceDataProviderAdapter",
    "PerformanceMetrics",
    "IPerformanceAnalytics",
    "PerformanceAnalytics",
]
