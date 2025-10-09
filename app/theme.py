from __future__ import annotations

from PySide6.QtGui import QColor, QLinearGradient, QBrush, QPen
from PySide6.QtCore import Qt


def build_stylesheet(mode: str, accent: QColor, text_col: QColor | None = None) -> str:
    if mode == "light":
        bg = "#F7F7F7"; panel = "#FFFFFF"; text = "#111111"; sel = accent.name()
    else:
        bg = "#121212"; panel = "#1e1e1e"; text = "#E6E6E6"; sel = accent.name()
    return f"""
    QWidget {{ font-family: 'SF Pro Text', 'Segoe UI', 'Helvetica Neue', Arial; font-size: 11pt; color: {text}; }}
    QMainWindow {{ background-color: {bg}; }}
    QToolBar {{ background: {panel}; border: 0px; spacing: 8px; }}
    QLineEdit, QComboBox, QPushButton {{ color: {text}; background: {panel}; border: 1px solid #3a3a3a; padding: 6px; border-radius: 6px; }}
    QComboBox QAbstractItemView {{ background: {panel}; color: {text}; selection-background-color: {sel}; selection-color: white; }}
    QCheckBox {{ color: {text}; }}
    QLabel {{ color: {text}; }}
    QDockWidget {{ background: {bg}; titlebar-close-icon: url(none); titlebar-normal-icon: url(none); }}
    QDockWidget::title {{ background: {panel}; color: {text}; padding: 6px; border: 0px; }}
    QScrollArea {{ background: {bg}; border: 0px; }}
    QGroupBox {{ background: {panel}; border: 1px solid #3a3a3a; border-radius: 6px; margin-top: 12px; }}
    QGroupBox::title {{ subcontrol-origin: margin; left: 8px; padding: 0 4px; color: {text}; }}
    QPushButton::menu-indicator {{ image: none; width: 0; }}
    QTableWidget {{ background: {panel}; color: {text}; gridline-color: #2a2a2a; selection-background-color: {sel}; selection-color: white; }}
    QHeaderView::section {{ background: {panel}; color: {text}; padding: 8px; border: 0px; font-weight: 600; }}
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

