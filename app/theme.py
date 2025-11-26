from __future__ import annotations

from typing import Tuple
from decimal import Decimal
from PySide6.QtGui import QColor, QLinearGradient, QBrush, QPen
from PySide6.QtCore import Qt


# Minimum contrast ratio for WCAG AA compliance (normal text)
MIN_CONTRAST_RATIO = 4.5


# Price color gradients for positive/negative values
# Dark mode colors
POSITIVE_COLOR_DARK = QColor("#30D158")  # Green for positive
NEGATIVE_COLOR_DARK = QColor("#FF453A")  # Red for negative
NEUTRAL_COLOR_DARK = QColor("#E6E6E6")   # Neutral/zero

# Light mode colors
POSITIVE_COLOR_LIGHT = QColor("#28A745")  # Green for positive
NEGATIVE_COLOR_LIGHT = QColor("#DC3545")  # Red for negative
NEUTRAL_COLOR_LIGHT = QColor("#111111")   # Neutral/zero


def get_relative_luminance(color: QColor) -> float:
    """Calculate the relative luminance of a color per WCAG 2.1.
    
    Uses the formula from https://www.w3.org/TR/WCAG21/#dfn-relative-luminance
    
    Args:
        color: The color to calculate luminance for
        
    Returns:
        Relative luminance value between 0 and 1
    """
    def linearize(value: int) -> float:
        """Convert sRGB component to linear RGB."""
        v = value / 255.0
        if v <= 0.03928:
            return v / 12.92
        return ((v + 0.055) / 1.055) ** 2.4
    
    r = linearize(color.red())
    g = linearize(color.green())
    b = linearize(color.blue())
    
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def calculate_contrast_ratio(foreground: QColor, background: QColor) -> float:
    """Calculate the contrast ratio between two colors per WCAG 2.1.
    
    Args:
        foreground: The foreground (text) color
        background: The background color
        
    Returns:
        Contrast ratio between 1 and 21
    """
    lum1 = get_relative_luminance(foreground)
    lum2 = get_relative_luminance(background)
    
    lighter = max(lum1, lum2)
    darker = min(lum1, lum2)
    
    return (lighter + 0.05) / (darker + 0.05)


def ensure_contrast_ratio(
    text_color: QColor,
    background_color: QColor,
    min_ratio: float = MIN_CONTRAST_RATIO
) -> QColor:
    """Adjust text color to ensure minimum contrast ratio with background.
    
    If the current contrast ratio is below the minimum, the text color
    is adjusted (lightened or darkened) to meet the requirement.
    
    Args:
        text_color: The original text color
        background_color: The background color
        min_ratio: Minimum required contrast ratio (default: 4.5 for WCAG AA)
        
    Returns:
        Adjusted text color that meets the contrast requirement
    """
    current_ratio = calculate_contrast_ratio(text_color, background_color)
    
    if current_ratio >= min_ratio:
        return text_color
    
    # Determine if we should lighten or darken the text
    bg_luminance = get_relative_luminance(background_color)
    
    # Try both directions and pick the one that achieves better contrast
    # Start with the direction based on background luminance
    
    if bg_luminance > 0.5:
        # Light background: try darkening first, then lightening
        primary_direction = "darken"
    else:
        # Dark background: try lightening first, then darkening
        primary_direction = "lighten"
    
    def try_adjust(color: QColor, direction: str) -> QColor:
        """Try to adjust color in given direction to meet contrast."""
        adjusted = QColor(color)
        for _ in range(200):  # More iterations for edge cases
            if direction == "darken":
                adjusted = adjusted.darker(110)  # More aggressive adjustment
            else:
                adjusted = adjusted.lighter(110)
            if calculate_contrast_ratio(adjusted, background_color) >= min_ratio:
                return adjusted
        return None
    
    # Try primary direction
    result = try_adjust(text_color, primary_direction)
    if result is not None:
        return result
    
    # Try opposite direction
    opposite = "lighten" if primary_direction == "darken" else "darken"
    result = try_adjust(text_color, opposite)
    if result is not None:
        return result
    
    # Fallback: use black or white based on which gives better contrast
    black_contrast = calculate_contrast_ratio(QColor(0, 0, 0), background_color)
    white_contrast = calculate_contrast_ratio(QColor(255, 255, 255), background_color)
    
    return QColor(0, 0, 0) if black_contrast >= white_contrast else QColor(255, 255, 255)


def get_price_change_color(value: Decimal | float | int, mode: str = "dark") -> QColor:
    """Get the appropriate color for a price change value.
    
    Returns distinct colors for positive, negative, and zero values
    based on the current theme mode.
    
    Args:
        value: The price change value (can be Decimal, float, or int)
        mode: Theme mode ("dark" or "light")
        
    Returns:
        QColor for the price change - green for positive, red for negative,
        neutral for zero
    """
    # Convert to float for comparison if needed
    if isinstance(value, Decimal):
        numeric_value = float(value)
    else:
        numeric_value = float(value)
    
    if mode == "light":
        if numeric_value > 0:
            return QColor(POSITIVE_COLOR_LIGHT)
        elif numeric_value < 0:
            return QColor(NEGATIVE_COLOR_LIGHT)
        else:
            return QColor(NEUTRAL_COLOR_LIGHT)
    else:
        # Default to dark mode
        if numeric_value > 0:
            return QColor(POSITIVE_COLOR_DARK)
        elif numeric_value < 0:
            return QColor(NEGATIVE_COLOR_DARK)
        else:
            return QColor(NEUTRAL_COLOR_DARK)


def get_price_gradient(value: Decimal | float | int, mode: str = "dark") -> QLinearGradient:
    """Get a gradient for price change visualization.
    
    Creates a subtle gradient based on the price change direction
    for enhanced visual feedback.
    
    Args:
        value: The price change value
        mode: Theme mode ("dark" or "light")
        
    Returns:
        QLinearGradient for the price change
    """
    base_color = get_price_change_color(value, mode)
    
    gradient = QLinearGradient(0, 0, 1, 0)
    gradient.setCoordinateMode(QLinearGradient.ObjectBoundingMode)
    
    # Create a subtle gradient from the base color
    lighter = QColor(base_color)
    lighter.setAlpha(180)
    
    gradient.setColorAt(0.0, base_color)
    gradient.setColorAt(1.0, lighter)
    
    return gradient


def get_theme_colors(mode: str, accent: QColor) -> dict:
    """Get theme colors for a given mode with contrast-compliant text colors.
    
    Args:
        mode: Theme mode ("dark" or "light")
        accent: Accent color for the theme
        
    Returns:
        Dictionary with theme color values
    """
    if mode == "light":
        bg = QColor("#F7F7F7")
        panel = QColor("#FFFFFF")
        text = QColor("#111111")
    else:
        bg = QColor("#121212")
        panel = QColor("#1e1e1e")
        text = QColor("#E6E6E6")
    
    # Ensure text has sufficient contrast with backgrounds
    text_on_bg = ensure_contrast_ratio(text, bg)
    text_on_panel = ensure_contrast_ratio(text, panel)
    
    return {
        "background": bg,
        "panel": panel,
        "text": text_on_bg,
        "text_on_panel": text_on_panel,
        "accent": accent,
        "mode": mode,
    }


def get_acrylic_colors(mode: str) -> Tuple[QColor, float, int]:
    """Get acrylic effect colors for a given theme mode.
    
    Returns colors optimized for contrast compliance with text.
    
    Args:
        mode: Theme mode ("dark" or "light")
        
    Returns:
        Tuple of (tint_color, opacity, blur_radius)
    """
    if mode == "dark":
        # Dark mode: darker tint with higher opacity for better contrast
        return QColor(18, 18, 18), 0.85, 20
    else:
        # Light mode: lighter tint with good opacity
        return QColor(247, 247, 247), 0.80, 15


def build_stylesheet(mode: str, accent: QColor, text_col: QColor | None = None) -> str:
    if mode == "light":
        bg = "#F7F7F7"; panel = "#FFFFFF"; text = "#111111"; sel = accent.name()
        hover_bg = "#E8E8E8"
        btn_hover = "#E0E0E0"
    else:
        bg = "#121212"; panel = "#1e1e1e"; text = "#E6E6E6"; sel = accent.name()
        hover_bg = "#2a2a2a"
        btn_hover = "#3a3a3a"
    
    # Create accent hover color
    accent_hover = QColor(accent)
    accent_hover.setAlpha(40)
    
    return f"""
    QWidget {{ font-family: 'SF Pro Text', 'Segoe UI', 'Helvetica Neue', Arial; font-size: 11pt; color: {text}; }}
    QMainWindow {{ background-color: {bg}; }}
    QToolBar {{ background: {panel}; border: 0px; spacing: 8px; }}
    QLineEdit, QComboBox {{ color: {text}; background: {panel}; border: 1px solid #3a3a3a; padding: 6px; border-radius: 6px; }}
    QPushButton {{ 
        color: {text}; 
        background: {panel}; 
        border: 1px solid #3a3a3a; 
        padding: 6px; 
        border-radius: 6px; 
    }}
    QPushButton:hover {{ 
        background: {btn_hover}; 
        border: 1px solid {sel}; 
    }}
    QPushButton:pressed {{ 
        background: {sel}; 
        color: white; 
    }}
    QComboBox QAbstractItemView {{ background: {panel}; color: {text}; selection-background-color: {sel}; selection-color: white; }}
    QCheckBox {{ color: {text}; }}
    QCheckBox:hover {{ color: {sel}; }}
    QLabel {{ color: {text}; }}
    QDockWidget {{ background: {bg}; titlebar-close-icon: url(none); titlebar-normal-icon: url(none); }}
    QDockWidget::title {{ background: {panel}; color: {text}; padding: 6px; border: 0px; }}
    QScrollArea {{ background: {bg}; border: 0px; }}
    QGroupBox {{ background: {panel}; border: 1px solid #3a3a3a; border-radius: 6px; margin-top: 12px; }}
    QGroupBox::title {{ subcontrol-origin: margin; left: 8px; padding: 0 4px; color: {text}; }}
    QPushButton::menu-indicator {{ image: none; width: 0; }}
    QTableWidget {{ background: {panel}; color: {text}; gridline-color: #2a2a2a; selection-background-color: {sel}; selection-color: white; }}
    QTableWidget::item:hover {{ background-color: {hover_bg}; }}
    QHeaderView::section {{ background: {panel}; color: {text}; padding: 8px; border: 0px; font-weight: 600; }}
    QHeaderView::section:hover {{ background: {hover_bg}; }}
    """


def get_alternating_row_colors(mode: str) -> Tuple[QColor, QColor]:
    """Get alternating row background colors for tables.
    
    Returns two colors for alternating rows with subtle depth shadows.
    
    Args:
        mode: Theme mode ("dark" or "light")
        
    Returns:
        Tuple of (even_row_color, odd_row_color)
    """
    if mode == "light":
        even_color = QColor("#FFFFFF")
        odd_color = QColor("#F5F5F5")
    else:
        even_color = QColor("#1e1e1e")
        odd_color = QColor("#252525")
    
    return even_color, odd_color


def get_row_selection_style(accent: QColor, mode: str = "dark") -> dict:
    """Get selection styling for table rows with accent-colored glow effect.
    
    Args:
        accent: The accent color for the theme
        mode: Theme mode ("dark" or "light")
        
    Returns:
        Dictionary with selection styling properties
    """
    # Create glow color from accent with transparency
    glow_color = QColor(accent)
    glow_color.setAlpha(100)
    
    # Selection background with accent
    selection_bg = QColor(accent)
    selection_bg.setAlpha(180)
    
    # Text color for selection (ensure contrast)
    if mode == "light":
        selection_text = QColor("#FFFFFF")
    else:
        selection_text = QColor("#FFFFFF")
    
    return {
        "selection_background": selection_bg,
        "selection_text": selection_text,
        "glow_color": glow_color,
        "glow_radius": 8,
    }


def build_table_stylesheet(mode: str, accent: QColor) -> str:
    """Build a stylesheet for QTableWidget with enhanced visual styling.
    
    Includes alternating row backgrounds with depth shadows and
    accent-colored glow effect for selection.
    
    Args:
        mode: Theme mode ("dark" or "light")
        accent: Accent color for the theme
        
    Returns:
        CSS stylesheet string for QTableWidget
    """
    even_color, odd_color = get_alternating_row_colors(mode)
    selection_style = get_row_selection_style(accent, mode)
    
    if mode == "light":
        text_color = "#111111"
        border_color = "#d0d0d0"
        header_bg = "#F0F0F0"
    else:
        text_color = "#E6E6E6"
        border_color = "#3a3a3a"
        header_bg = "#2a2a2a"
    
    return f"""
    QTableWidget {{
        background-color: {even_color.name()};
        color: {text_color};
        gridline-color: {border_color};
        border: none;
        border-radius: 6px;
    }}
    QTableWidget::item {{
        padding: 8px;
        border-bottom: 1px solid {border_color};
    }}
    QTableWidget::item:alternate {{
        background-color: {odd_color.name()};
    }}
    QTableWidget::item:selected {{
        background-color: {selection_style['selection_background'].name()};
        color: {selection_style['selection_text'].name()};
    }}
    QTableWidget::item:hover {{
        background-color: {selection_style['glow_color'].name()};
    }}
    QHeaderView::section {{
        background-color: {header_bg};
        color: {text_color};
        padding: 10px;
        border: none;
        border-bottom: 2px solid {accent.name()};
        font-weight: 600;
    }}
    QTableCornerButton::section {{
        background-color: {header_bg};
        border: none;
    }}
    """


def apply_chart_theme(chart, chart_view, series_main, series_ma_fast, series_ma_slow, area_fill, axisX, axisY, vol_axes, mode: str, accent: QColor):
    text_col = QColor("#E6E6E6") if mode == "dark" else QColor("#111111")
    grid_col = QColor("#2a2a2a") if mode == "dark" else QColor("#d0d0d0")

    main_pen = QPen(accent); main_pen.setWidth(2)
    fast_pen = QPen(QColor(accent.red(), accent.green(), accent.blue(), 180)); fast_pen.setWidth(2)
    slow_pen = QPen(QColor(accent.red(), accent.green(), accent.blue(), 110)); slow_pen.setWidth(2)
    series_main.setPen(main_pen)
    series_ma_fast.setPen(fast_pen)
    series_ma_slow.setPen(slow_pen)

    grad = QLinearGradient(0, 0, 0, 1)
    col_top = QColor(accent.red(), accent.green(), accent.blue(), 90)
    col_bot = QColor(accent.red(), accent.green(), accent.blue(), 10)
    grad.setCoordinateMode(QLinearGradient.ObjectBoundingMode)
    grad.setColorAt(0.0, col_top)
    grad.setColorAt(1.0, col_bot)
    area_fill.setBrush(QBrush(grad))
    area_fill.setPen(Qt.NoPen)

    gp = QPen(grid_col); gp.setWidth(1)
    axisX.setLabelsBrush(text_col); axisY.setLabelsBrush(text_col)
    axisX.setGridLinePen(gp); axisY.setGridLinePen(gp)
    chart.setTitleBrush(text_col)

    if vol_axes:
        vx, vy = vol_axes
        vx.setLabelsBrush(text_col); vy.setLabelsBrush(text_col)
        vx.setGridLinePen(gp); vy.setGridLinePen(gp)

