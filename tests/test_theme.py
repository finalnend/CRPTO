from __future__ import annotations

from PySide6.QtGui import QColor
from PySide6.QtCharts import QChart, QLineSeries, QAreaSeries
from PySide6.QtCharts import QValueAxis
from PySide6.QtCore import Qt
import app.theme as theme


def test_build_stylesheet_dark():
    css = theme.build_stylesheet("dark", QColor("#0A84FF"))
    assert isinstance(css, str) and "QMainWindow" in css


def test_apply_chart_theme_no_crash():
    chart = QChart()
    series_main = QLineSeries()
    series_base = QLineSeries()
    area = QAreaSeries(series_main, series_base)
    ax_x = QValueAxis(); ax_y = QValueAxis()
    chart.addSeries(area); chart.addSeries(series_main)
    chart.addAxis(ax_x, Qt.AlignBottom); chart.addAxis(ax_y, Qt.AlignLeft)
    series_main.attachAxis(ax_x); series_main.attachAxis(ax_y)
    area.attachAxis(ax_x); area.attachAxis(ax_y)

    # Should not raise
    theme.apply_chart_theme(chart, None, series_main, QLineSeries(), QLineSeries(), area, ax_x, ax_y, (QValueAxis(), QValueAxis()), "dark", QColor("#0A84FF"))

