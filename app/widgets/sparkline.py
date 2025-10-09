from __future__ import annotations

from typing import List

from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget


class SparklineWidget(QWidget):
    """Minimal sparkline drawn on the right side of a table cell.

    - Does NOT draw title text; lets the table item render the symbol text to avoid overlap.
    - Supports updating color and data.
    """

    def __init__(self, color: QColor, left_padding: int = 64, parent=None) -> None:
        super().__init__(parent)
        self._color = QColor(color)
        self._data: List[float] = []
        self._left_padding = left_padding
        self.setMinimumHeight(24)

    def update_color(self, c: QColor) -> None:
        self._color = QColor(c)
        self.update()

    def update_data(self, data: List[float], color: QColor | None = None) -> None:
        if color is not None:
            self._color = QColor(color)
        self._data = data
        self.update()

    def paintEvent(self, event):  # type: ignore[override]
        if not self._data:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = self.rect()
        top = r.top() + 4
        h = r.height() - 8
        left = r.left() + self._left_padding
        w = max(8, r.width() - self._left_padding - 6)

        lo = min(self._data)
        hi = max(self._data)
        rng = (hi - lo) or 1.0
        pts: List[QPointF] = []
        for i, v in enumerate(self._data):
            x = left + (i / max(1, len(self._data) - 1)) * w
            y = top + (1 - (v - lo) / rng) * h
            pts.append(QPointF(x, y))
        pen = QPen(self._color)
        pen.setWidth(2)
        p.setPen(pen)
        for i in range(1, len(pts)):
            p.drawLine(pts[i - 1], pts[i])
        p.end()

