"""Alt / Gothic visualizer — goth-girl silhouettes over a smooth purple flame.

Characters are drawn procedurally (silhouettes) for now; real sprite assets can
drop into ``assets/`` later and replace ``_draw_character``. Each character has
a *depth*: ``back`` characters are smaller and drawn behind the spectrum, ``front``
characters are larger and drawn in front, giving a layered stage look.

The spectrum is a single smooth, connected flame (a filled spline, not separate
bars) that glows and pulses red on bass. Poses:
  idle -> sway -> dance -> hands_up (on drop) -> horns (left-click cycles).

Particles: bats drifting across, rose petals falling on beats.
"""
from __future__ import annotations

import time

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

POSES = ("idle", "sway", "dance", "hands_up", "horns")


class AltGothicVisualizer(BaseVisualizer):
    theme_key = "alt_gothic"

    def __init__(self, num_bands: int, parent=None) -> None:
        super().__init__(num_bands, parent)
        # Stage of characters: smaller "back" ones sit behind the flame,
        # larger "front" ones stand before it. (anchor_x, depth, scale, feet_y)
        self._chars = [
            {"x": 0.50, "depth": "back", "scale": 0.20, "feet": 0.80,
             "pose": "idle", "timer": 0.0},
            {"x": 0.14, "depth": "back", "scale": 0.18, "feet": 0.82,
             "pose": "sway", "timer": 0.0},
            {"x": 0.86, "depth": "back", "scale": 0.18, "feet": 0.82,
             "pose": "idle", "timer": 0.0},
            {"x": 0.32, "depth": "front", "scale": 0.30, "feet": 0.99,
             "pose": "sway", "timer": 0.0},
            {"x": 0.68, "depth": "front", "scale": 0.30, "feet": 0.99,
             "pose": "idle", "timer": 0.0},
        ]
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

        # Loudness drives default pose energy.
        for c in self._chars:
            c["timer"] = max(0.0, c["timer"] - dt)
            if c["timer"] == 0.0:  # return to audio-driven pose
                c["pose"] = "dance" if frame.level > 0.4 else (
                    "sway" if frame.level > 0.15 else "idle"
                )
        if frame.drop:
            for c in self._chars:
                c["pose"] = "hands_up"
                c["timer"] = 1.2

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
        # Night gradient, pulsing toward red-purple on bass.
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

        # Back characters first, so the flame overlaps them.
        for c in self._chars:
            if c["depth"] == "back":
                self._draw_character(painter, c)

        self._draw_flame_spectrum(painter)

        for petal in self._petals:
            painter.setBrush(QColor(180, 40, 80, 200))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QRectF(petal[0], petal[1], 6, 9))

        # Front characters in front of the flame.
        for c in self._chars:
            if c["depth"] == "front":
                self._draw_character(painter, c)

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

        # Smooth top edge using midpoint quadratic segments.
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

        # Filled body with a purple->red vertical gradient.
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

    def _draw_character(self, painter: QPainter, c: dict) -> None:
        """Stylized goth-girl silhouette with a few pose variations."""
        x = c["x"] * self.width()
        feet_y = c["feet"] * self.height()
        pose = c["pose"]
        body_h = self.height() * c["scale"]
        head_r = body_h * 0.13
        hip_y = feet_y - body_h * 0.45
        shoulder_y = feet_y - body_h * 0.78
        head_y = shoulder_y - head_r * 1.6

        skin = QColor(235, 225, 230)
        dress = QColor(15, 10, 20)
        accent = QColor(140, 30, 90)

        painter.setPen(Qt.PenStyle.NoPen)
        # Dress (triangle skirt + torso).
        painter.setBrush(dress)
        skirt = QPolygonF([
            QPointF(x - body_h * 0.22, feet_y),
            QPointF(x + body_h * 0.22, feet_y),
            QPointF(x + body_h * 0.08, hip_y),
            QPointF(x - body_h * 0.08, hip_y),
        ])
        painter.drawPolygon(skirt)
        painter.drawRect(QRectF(x - body_h * 0.08, shoulder_y, body_h * 0.16, hip_y - shoulder_y))

        # Head + long hair.
        painter.setBrush(QColor(10, 8, 14))
        painter.drawEllipse(QRectF(x - head_r * 1.3, head_y - head_r, head_r * 2.6, head_r * 3.2))
        painter.setBrush(skin)
        painter.drawEllipse(QRectF(x - head_r, head_y - head_r, head_r * 2, head_r * 2))
        # Choker.
        painter.setBrush(accent)
        painter.drawRect(QRectF(x - head_r * 0.7, head_y + head_r * 0.9, head_r * 1.4, head_r * 0.3))

        # Arms depend on pose.
        painter.setBrush(dress)
        arm_w = body_h * 0.05
        if pose == "hands_up" or pose == "horns":
            painter.drawRect(QRectF(x - body_h * 0.18, shoulder_y - body_h * 0.35, arm_w, body_h * 0.4))
            painter.drawRect(QRectF(x + body_h * 0.13, shoulder_y - body_h * 0.35, arm_w, body_h * 0.4))
        elif pose == "dance":
            painter.drawRect(QRectF(x - body_h * 0.22, shoulder_y, arm_w, body_h * 0.3))
            painter.drawRect(QRectF(x + body_h * 0.17, shoulder_y - body_h * 0.15, arm_w, body_h * 0.3))
        else:  # idle / sway
            painter.drawRect(QRectF(x - body_h * 0.12, shoulder_y, arm_w, body_h * 0.32))
            painter.drawRect(QRectF(x + body_h * 0.07, shoulder_y, arm_w, body_h * 0.32))

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
        i = int(np.argmin([abs(c["x"] - xf) for c in self._chars]))
        if button == Qt.MouseButton.LeftButton:
            cur = self._chars[i]["pose"]
            nxt = POSES[(POSES.index(cur) + 1) % len(POSES)] if cur in POSES else "dance"
            self._chars[i]["pose"] = nxt
            self._chars[i]["timer"] = 2.0
