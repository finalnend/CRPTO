# UI components module
"""Modern UI components with acrylic effects, animations, and enhanced visual styling."""

# Note: Imports are done lazily to avoid metaclass conflicts with ABC and QWidget
# Import directly from submodules when needed:
#   from app.ui.acrylic import AcrylicWidget, AcrylicPanel
#   from app.ui.paper_trading import PaperTradingPanel, PortfolioView, TradeHistoryView
#   from app.ui.animations import FadeAnimator, PulseAnimator, AnimatedTableItem
#   from app.ui.navigation import PageType, NavigationState, NavigationSidebar
#   from app.ui.page_container import PageContainer

__all__ = [
    "AcrylicWidget",
    "AcrylicPanel",
    "IAcrylicEffect",
    "PaperTradingPanel",
    "PortfolioView",
    "TradeHistoryView",
    "PaperTradingDockContent",
    "FadeAnimator",
    "ValueTransitionAnimator",
    "ExpandCollapseAnimator",
    "HoverAnimator",
    "PulseAnimator",
    "AnimatedTableItem",
    "PageType",
    "NavigationState",
    "NavigationSidebar",
    "PageContainer",
]


def __getattr__(name: str):
    """Lazy import to avoid metaclass conflicts."""
    if name in ("AcrylicWidget", "AcrylicPanel", "IAcrylicEffect"):
        from app.ui.acrylic import AcrylicWidget, AcrylicPanel, IAcrylicEffect
        return {"AcrylicWidget": AcrylicWidget, "AcrylicPanel": AcrylicPanel, "IAcrylicEffect": IAcrylicEffect}[name]
    elif name in ("PaperTradingPanel", "PortfolioView", "TradeHistoryView", "PaperTradingDockContent"):
        from app.ui.paper_trading import PaperTradingPanel, PortfolioView, TradeHistoryView, PaperTradingDockContent
        return {"PaperTradingPanel": PaperTradingPanel, "PortfolioView": PortfolioView, 
                "TradeHistoryView": TradeHistoryView, "PaperTradingDockContent": PaperTradingDockContent}[name]
    elif name in ("FadeAnimator", "ValueTransitionAnimator", "ExpandCollapseAnimator", 
                  "HoverAnimator", "PulseAnimator", "AnimatedTableItem"):
        from app.ui.animations import (
            FadeAnimator, ValueTransitionAnimator, ExpandCollapseAnimator,
            HoverAnimator, PulseAnimator, AnimatedTableItem
        )
        return {
            "FadeAnimator": FadeAnimator,
            "ValueTransitionAnimator": ValueTransitionAnimator,
            "ExpandCollapseAnimator": ExpandCollapseAnimator,
            "HoverAnimator": HoverAnimator,
            "PulseAnimator": PulseAnimator,
            "AnimatedTableItem": AnimatedTableItem,
        }[name]
    elif name in ("PageType", "NavigationState", "NavigationSidebar"):
        from app.ui.navigation import PageType, NavigationState, NavigationSidebar
        return {
            "PageType": PageType,
            "NavigationState": NavigationState,
            "NavigationSidebar": NavigationSidebar,
        }[name]
    elif name == "PageContainer":
        from app.ui.page_container import PageContainer
        return PageContainer
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
