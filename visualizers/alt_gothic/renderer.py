"""Alt / Gothic visualizer — layered goth-girl rigs over a smooth purple flame.

Characters are :class:`CharacterRig` instances (see ``rig.py``): layered
paper-dolls that articulate to the music. ``back`` characters are smaller and
drawn behind the spectrum; ``front`` ones stand before it. Real AI-generated art
drops into ``assets/characters/<name>/`` as per-layer PNGs; until then a
procedural silhouette stands in.

The spectrum is a single smooth, connected flame (a filled spline, not separate
bars) that glows and pulses red on bass. Particles: bats drifting across, rose
petals falling on beats.
"""
from __future__ import annotations

import time
from pathlib import Path

import numpy as np
from PyQt6.QtCore import QPoint, QPointF, QRectF, Qt
from PyQt6.QtGui import (
    QColor,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPolygonF,
)

from ..base import BaseVisualizer
from .rig import POSE_ARMS, CharacterRig

_POSE_CYCLE = ("idle", "sway", "dance", "hands_up", "horns")
_ASSET_DIR = Path(__file__).resolve().parent.parent.parent / "assets" / "characters"


class AltGothicVisualizer(BaseVisualizer):
    theme_key = "alt_gothic"

    def __init__(self, num_bands: int, parent=None) -> None:
        super().__init__(num_bands, parent)
        # Stage: smaller "back" rigs behind the flame, larger "front" rigs ahead.
        # Each character appears once front and once back on opposite sides, one
        # of them mirrored, so the two real-art assets read as four distinct girls.
        self._rigs = [
            CharacterRig(0.13, 0.84, 0.17, depth="back", name="goth_c", hair_hue=320),
            CharacterRig(0.87, 0.84, 0.17, depth="back", name="goth_a", hair_hue=200,
                         flip=True),
            CharacterRig(0.30, 0.99, 0.30, depth="front", name="goth_a", hair_hue=300),
            CharacterRig(0.70, 0.99, 0.30, depth="front", name="goth_c", hair_hue=260,
                         flip=True),
        ]
        for rig in self._rigs:
            rig.load_assets(_ASSET_DIR)

        self._bass_pulse = 0.0
        self._bats: list[list[float]] = []   # [x, y, vx, phase]
        self._petals: list[list[float]] = []  # [x, y, vy, drift]
        self._last_t = time.perf_counter()

    def on_frame(self, frame) -> None:
        now = time.perf_counter()
        dt = now - self._last_t
        self._last_t = now

        bass = float(frame.bands[: max(1, self.num_bands // 8)].mean())
        self._bass_pulse += (bass - self._bass_pulse) * min(1.0, dt * 6.0)

        for rig in self._rigs:
            rig.update(dt, frame.level, frame.beat, frame.drop, bass)

        # Spawn the occasional bat.
        if np.random.random() < 0.02:
            self._bats.append([
                -20.0, np.random.uniform(0.08, 0.45) * self.height(),
                np.random.uniform(60, 130), np.random.uniform(0, 6.28),
            ])
        for b in self._bats:
            b[0] += b[2] * dt
            b[3] += dt * 8
        self._bats = [b for b in self._bats if b[0] < self.width() + 30]

        # Rose petals on beats.
        if frame.beat:
            self._petals.append([
                np.random.uniform(0, self.width()), -10.0,
                np.random.uniform(40, 90), np.random.uniform(-20, 20),
            ])
        for p in self._petals:
            p[1] += p[2] * dt
            p[0] += np.sin(p[1] * 0.02) * p[3] * dt
        self._petals = [p for p in self._petals if p[1] < self.height() + 10]

    def render(self, painter: QPainter) -> None:
        w, h = self.width(), self.height()
        pulse = self._bass_pulse
        sky = QLinearGradient(0, 0, 0, h)
        sky.setColorAt(0.0, QColor(int(22 + 45 * pulse), 6, int(30 + 24 * pulse)))
        sky.setColorAt(1.0, QColor(6, 3, 10))
        painter.fillRect(0, 0, w, h, sky)
        if self.frame is None:
            return

        # Moon.
        painter.setBrush(QColor(230, 230, 245, 180))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QRectF(w * 0.8, h * 0.12, 70, 70))

        for rig in self._rigs:
            if rig.depth == "back":
                rig.draw(painter, w, h)

        self._draw_flame_spectrum(painter)

        for petal in self._petals:
            painter.setBrush(QColor(180, 40, 80, 200))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QRectF(petal[0], petal[1], 6, 9))

        for rig in self._rigs:
            if rig.depth == "front":
                rig.draw(painter, w, h)

        for bat in self._bats:
            self._draw_bat(painter, bat[0], bat[1], bat[3])

    def _draw_flame_spectrum(self, painter: QPainter) -> None:
        """A single smooth, connected flame built from a spline through bands."""
        w, h = self.width(), self.height()
        bands = self.frame.bands
        n = self.num_bands
        base_y = h * 0.82
        span = base_y * 0.62
        pulse = self._bass_pulse

        xs = np.linspace(0, w, n)
        ys = base_y - bands * span

        path = QPainterPath()
        path.moveTo(0.0, base_y)
        path.lineTo(float(xs[0]), float(ys[0]))
        for i in range(1, n):
            mx = (xs[i - 1] + xs[i]) / 2.0
            my = (ys[i - 1] + ys[i]) / 2.0
            path.quadTo(float(xs[i - 1]), float(ys[i - 1]), float(mx), float(my))
        path.lineTo(float(xs[-1]), float(ys[-1]))
        path.lineTo(float(w), base_y)
        path.closeSubpath()

        grad = QLinearGradient(0, base_y - span, 0, base_y)
        r = int(150 + 90 * pulse)
        grad.setColorAt(0.0, QColor(r, 30, 170, 210))
        grad.setColorAt(0.6, QColor(110, 20, 150, 170))
        grad.setColorAt(1.0, QColor(40, 8, 70, 40))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(grad)
        painter.drawPath(path)

        # Glowing top edge, drawn additively.
        painter.save()
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Plus)
        edge = QPainterPath()
        edge.moveTo(float(xs[0]), float(ys[0]))
        for i in range(1, n):
            mx = (xs[i - 1] + xs[i]) / 2.0
            my = (ys[i - 1] + ys[i]) / 2.0
            edge.quadTo(float(xs[i - 1]), float(ys[i - 1]), float(mx), float(my))
        edge.lineTo(float(xs[-1]), float(ys[-1]))
        for width, alpha in ((6.0, 60), (2.5, 150)):
            pen = QPen(QColor(220, 90, 220, alpha))
            pen.setWidthF(width)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(edge)
        painter.restore()

    def _draw_bat(self, painter: QPainter, x: float, y: float, phase: float) -> None:
        flap = abs(np.sin(phase)) * 6
        painter.setBrush(QColor(0, 0, 0))
        painter.setPen(Qt.PenStyle.NoPen)
        wing = QPolygonF([
            QPointF(x, y), QPointF(x - 12, y - flap), QPointF(x - 6, y + 2),
            QPointF(x, y + 4), QPointF(x + 6, y + 2), QPointF(x + 12, y - flap),
        ])
        painter.drawPolygon(wing)

    # --- interactions ------------------------------------------------------
    def on_press(self, button, pos: QPoint) -> None:
        # Pick the nearest character by horizontal distance.
        xf = pos.x() / max(1, self.width())
        i = int(np.argmin([abs(r.x_frac - xf) for r in self._rigs]))
        if button == Qt.MouseButton.LeftButton:
            cur = self._rigs[i].pose
            nxt = _POSE_CYCLE[(_POSE_CYCLE.index(cur) + 1) % len(_POSE_CYCLE)] \
                if cur in _POSE_CYCLE else "dance"
            self._rigs[i].set_pose(nxt, hold=2.5)
