"""Cartoon visualizer — bouncy jelly bars with googly eyes.

Each bar is a rounded "jelly" body with eyes. Bass bars are fat and sleepy,
treble bars are thin and jittery. On a drop every bar hops. Left-click makes a
bar pull a surprised face; right-click pops a star burst above it.
"""
from __future__ import annotations

import time

import numpy as np
from PyQt6.QtCore import QPoint, QRectF, Qt
from PyQt6.QtGui import QColor, QPainter

from ..base import BaseVisualizer

PALETTE = [
    (255, 105, 97), (255, 179, 71), (253, 253, 150),
    (119, 221, 119), (108, 198, 247), (177, 156, 217),
]


class CartoonVisualizer(BaseVisualizer):
    theme_key = "cartoon"

    def __init__(self, num_bands: int, parent=None) -> None:
        super().__init__(num_bands, parent)
        self._hop = np.zeros(num_bands, dtype=np.float32)
        self._surprise = np.zeros(num_bands, dtype=np.float32)
        self._stars: list[list[float]] = []  # [x, y, vy, life]
        self._bg_hue = 0.0
        self._last_t = time.perf_counter()

    def on_frame(self, frame) -> None:
        now = time.perf_counter()
        dt = now - self._last_t
        self._last_t = now

        self._hop = np.maximum(self._hop - dt * 2.5, 0.0)
        self._surprise = np.maximum(self._surprise - dt * 1.5, 0.0)
        if frame.drop:
            self._hop[:] = 1.0

        # Drift background hue toward the dominant band.
        dom = int(np.argmax(frame.bands)) / max(1, self.num_bands - 1)
        self._bg_hue += (dom - self._bg_hue) * min(1.0, dt * 2.0)

        # Update floating stars.
        for s in self._stars:
            s[1] += s[2] * dt
            s[3] -= dt
        self._stars = [s for s in self._stars if s[3] > 0]

    def render(self, painter: QPainter) -> None:
        w, h = self.width(), self.height()
        bg = QColor.fromHslF(self._bg_hue, 0.45, 0.18)
        painter.fillRect(0, 0, w, h, bg)
        if self.frame is None:
            return

        base_y = h * 0.9
        slot = w / self.num_bands
        for i in range(self.num_bands):
            val = float(self.frame.bands[i])
            hop = float(self._hop[i]) * 30.0
            bh = val * base_y * 0.85 + 14
            cx = (i + 0.5) * slot
            body_w = slot * (0.85 if i < self.num_bands // 3 else 0.6)
            y = base_y - bh - hop

            color = QColor(*PALETTE[i % len(PALETTE)])
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(color)
            painter.drawRoundedRect(
                QRectF(cx - body_w / 2, y, body_w, bh + hop), body_w * 0.4, 14
            )
            self._draw_face(painter, cx, y, body_w, i)

        for x, y, _vy, life in self._stars:
            painter.setBrush(QColor(255, 245, 150, int(255 * min(1.0, life))))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QRectF(x - 4, y - 4, 8, 8))

    def _draw_face(self, painter: QPainter, cx: float, y: float, bw: float, i: int) -> None:
        eye_r = max(3.0, bw * 0.12)
        surprised = self._surprise[i] > 0
        scale = 1.6 if surprised else 1.0
        ex = bw * 0.22
        ey = y + eye_r * 2.2
        for sign in (-1, 1):
            painter.setBrush(QColor(255, 255, 255))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QRectF(cx + sign * ex - eye_r * scale, ey - eye_r * scale,
                                       eye_r * 2 * scale, eye_r * 2 * scale))
            painter.setBrush(QColor(20, 20, 20))
            painter.drawEllipse(QRectF(cx + sign * ex - eye_r * 0.5, ey - eye_r * 0.5,
                                       eye_r, eye_r))

    # --- interactions ------------------------------------------------------
    def on_press(self, button, pos: QPoint) -> None:
        idx = self.band_at(pos.x())
        if button == Qt.MouseButton.LeftButton:
            self._surprise[idx] = 1.0
        elif button == Qt.MouseButton.RightButton:
            slot = self.width() / self.num_bands
            cx = (idx + 0.5) * slot
            for _ in range(8):
                self._stars.append([
                    cx + np.random.uniform(-20, 20),
                    self.height() * 0.5,
                    np.random.uniform(-120, -40),
                    np.random.uniform(0.5, 1.2),
                ])
