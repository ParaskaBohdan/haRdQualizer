"""Dark Physics visualizer — neon bars on black with physics interactions.

Interactions:
  * Left-click   : shatter a bar into particles, then it regrows.
  * Left-drag    : toss bars upward; they fall and bounce under gravity.
  * Right-click  : freeze a bar (ignores audio for a few seconds, then thaws).
  * Right-drag   : squeeze/stretch the whole bar field around the cursor.
"""
from __future__ import annotations

import time

import numpy as np
from PyQt6.QtCore import QPoint, QRectF, Qt
from PyQt6.QtGui import QColor, QLinearGradient, QPainter

from ..base import BaseVisualizer
from .particles import ParticleSystem
from .physics import BarPhysics


def _neon_for(t: float) -> tuple[int, int, int]:
    """Blue -> purple -> pink gradient sample for t in [0, 1]."""
    t = max(0.0, min(1.0, t))
    stops = [
        (0.0, (60, 120, 255)),
        (0.5, (160, 70, 255)),
        (1.0, (255, 70, 180)),
    ]
    for (t0, c0), (t1, c1) in zip(stops, stops[1:]):
        if t <= t1:
            f = (t - t0) / (t1 - t0) if t1 > t0 else 0.0
            return tuple(int(a + (b - a) * f) for a, b in zip(c0, c1))  # type: ignore
    return stops[-1][1]


class DarkPhysicsVisualizer(BaseVisualizer):
    theme_key = "dark_physics"

    def __init__(self, num_bands: int, parent=None) -> None:
        super().__init__(num_bands, parent)
        self.physics = BarPhysics(num_bands)
        self.particles = ParticleSystem()
        self._last_t = time.perf_counter()
        self._last_drag: QPoint | None = None
        self._beat_flash = 0.0

    # --- frame handling ----------------------------------------------------
    def on_frame(self, frame) -> None:
        now = time.perf_counter()
        dt = now - self._last_t
        self._last_t = now

        heights = frame.bands
        self.physics.step(heights, dt)
        self.particles.update(dt, self.height_px())

        if frame.beat:
            self._beat_flash = 1.0
        else:
            self._beat_flash = max(0.0, self._beat_flash - dt * 3.0)

        if frame.drop:
            # On a drop, give every bar a little kick upward.
            for i in range(self.num_bands):
                self.physics.toss(i, 1.2 + float(np.random.uniform(0, 0.6)))

    def height_px(self) -> float:
        return self.height() * 0.92

    # --- painting ----------------------------------------------------------
    def render(self, painter: QPainter) -> None:
        w, h = self.width(), self.height()
        painter.fillRect(0, 0, w, h, QColor(8, 8, 12))

        if self.frame is None:
            return

        base_y = self.height_px()
        display = self.physics.height * (1.0 - self.physics.shatter)
        peaks = self.frame.peaks

        # Horizontal squeeze maps band index -> x around a pivot.
        sq = self.physics.squeeze
        pivot = self.physics.squeeze_center * w
        slot = w / self.num_bands
        bar_w = slot * 0.7

        for i in range(self.num_bands):
            cx = (i + 0.5) * slot
            cx = pivot + (cx - pivot) * sq
            bh = float(display[i]) * base_y
            x = cx - bar_w / 2.0
            y = base_y - bh

            color = _neon_for(i / max(1, self.num_bands - 1))
            grad = QLinearGradient(0, y, 0, base_y)
            top = QColor(*color)
            bottom = QColor(color[0] // 3, color[1] // 3, color[2] // 3)
            grad.setColorAt(0.0, top)
            grad.setColorAt(1.0, bottom)
            painter.fillRect(QRectF(x, y, bar_w, bh), grad)

            # Frozen bars get an icy outline.
            if self.physics.freeze_timer[i] > 0:
                painter.setPen(QColor(150, 220, 255))
                painter.drawRect(QRectF(x, y, bar_w, bh))

            # Peak marker.
            py = base_y - float(peaks[i]) * base_y
            painter.fillRect(QRectF(x, py, bar_w, 2.0), QColor(255, 255, 255, 200))

        self._draw_particles(painter)

        if self._beat_flash > 0:
            a = int(40 * self._beat_flash)
            painter.fillRect(0, 0, w, h, QColor(255, 255, 255, a))

    def _draw_particles(self, painter: QPainter) -> None:
        ps = self.particles
        mask = ps.active_mask()
        idxs = np.nonzero(mask)[0]
        for i in idxs:
            life_frac = ps.life[i] / ps.max_life[i]
            r, g, b = ps.color[i]
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(int(r), int(g), int(b), int(255 * life_frac)))
            s = float(ps.size[i])
            painter.drawEllipse(QRectF(ps.pos[i, 0], ps.pos[i, 1], s, s))

    # --- interactions ------------------------------------------------------
    def on_press(self, button, pos: QPoint) -> None:
        idx = self.band_at(pos.x())
        if button == Qt.MouseButton.LeftButton:
            self._shatter(idx)
        elif button == Qt.MouseButton.RightButton:
            self.physics.freeze(idx)
        self._last_drag = pos

    def on_drag(self, button, start: QPoint, pos: QPoint) -> None:
        if button == Qt.MouseButton.LeftButton:
            idx = self.band_at(pos.x())
            dy = (self._last_drag.y() - pos.y()) if self._last_drag else 0
            if dy > 0:  # moving up tosses
                self.physics.toss(idx, min(2.5, dy / 60.0 + 0.6))
        elif button == Qt.MouseButton.RightButton:
            # Horizontal drag distance controls squeeze factor.
            dx = pos.x() - start.x()
            factor = 1.0 + dx / max(1, self.width()) * 2.0
            self.physics.set_squeeze(factor, start.x() / max(1, self.width()))
        self._last_drag = pos

    def on_release(self, button, pos: QPoint) -> None:
        if button == Qt.MouseButton.RightButton:
            self.physics.reset_squeeze()
        self._last_drag = None

    def _shatter(self, idx: int) -> None:
        slot = self.width() / self.num_bands
        cx = (idx + 0.5) * slot
        bh = float(self.physics.height[idx]) * self.height_px()
        cy = self.height_px() - bh
        color = _neon_for(idx / max(1, self.num_bands - 1))
        self.particles.emit(cx, cy, count=24, color=color, speed=360.0)
        self.physics.shatter_bar(idx)
