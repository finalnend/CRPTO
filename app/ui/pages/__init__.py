"""Page widgets for sidebar navigation.

This module contains full-page widgets for each navigation destination:
- MarketOverviewPage: Cryptocurrency price table and chart
- PaperTradingFullPage: Full-page paper trading interface
- ChartAnalysisPage: Detailed chart analysis
- SettingsPage: Application settings
"""

from app.ui.pages.market_overview import MarketOverviewPage
from app.ui.pages.paper_trading_page import PaperTradingFullPage
from app.ui.pages.chart_analysis import ChartAnalysisPage
from app.ui.pages.settings import SettingsPage

__all__ = [
    "MarketOverviewPage",
    "PaperTradingFullPage",
    "ChartAnalysisPage",
    "SettingsPage",
]
