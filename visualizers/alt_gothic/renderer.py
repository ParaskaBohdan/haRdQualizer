"""Alt / Gothic visualizer — goth-girl silhouettes over a purple flame spectrum.

Characters are drawn procedurally (silhouettes) for now; real sprite assets can
drop into ``assets/`` later and replace ``_draw_character``. Poses:
  idle -> sway -> dance -> hands_up (on drop) -> horns (left-click cycles).

Backdrop: moon + a mirrored purple "flame" spectrum that pulses red on bass.
Particles: bats drifting across, rose petals falling.
"""
from __future__ import annotations

import time

import numpy as np
from PyQt6.QtCore import QPoint, QRectF, Qt
from PyQt6.QtGui import QColor, QPainter, QPolygonF
from PyQt6.QtCore import QPointF

from ..base import BaseVisualizer

POSES = ("idle", "sway", "dance", "hands_up", "horns")


class AltGothicVisualizer(BaseVisualizer):
    theme_key = "alt_gothic"

    def __init__(self, num_bands: int, parent=None) -> None:
        super().__init__(num_bands, parent)
        # Three characters at fixed horizontal anchors (fractions of width).
        self._anchors = [0.25, 0.5, 0.75]
        self._poses = ["idle", "sway", "idle"]
        self._pose_timer = [0.0, 0.0, 0.0]
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
        for i in range(len(self._poses)):
            self._pose_timer[i] = max(0.0, self._pose_timer[i] - dt)
            if self._pose_timer[i] == 0.0:  # return to audio-driven pose
                self._poses[i] = "dance" if frame.level > 0.4 else (
                    "sway" if frame.level > 0.15 else "idle"
                )
        if frame.drop:
            for i in range(len(self._poses)):
                self._poses[i] = "hands_up"
                self._pose_timer[i] = 1.2

        # Spawn the occasional bat.
        if np.random.random() < 0.02:
            self._bats.append([
                -20.0, np.random.uniform(0.1, 0.5) * self.height(),
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
        top = QColor(int(20 + 40 * pulse), 5, int(25 + 20 * pulse))
        painter.fillRect(0, 0, w, h, top)
        if self.frame is None:
            return

        # Moon.
        painter.setBrush(QColor(230, 230, 245, 180))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QRectF(w * 0.8, h * 0.12, 70, 70))

        self._draw_flame_spectrum(painter)

        for petal in self._petals:
            painter.setBrush(QColor(180, 40, 80, 200))
            painter.drawEllipse(QRectF(petal[0], petal[1], 6, 9))

        for i, ax in enumerate(self._anchors):
            self._draw_character(painter, ax * w, h * 0.95, self._poses[i])

        for bat in self._bats:
            self._draw_bat(painter, bat[0], bat[1], bat[3])

    def _draw_flame_spectrum(self, painter: QPainter) -> None:
        w, h = self.width(), self.height()
        base_y = h * 0.78
        slot = w / self.num_bands
        pulse = self._bass_pulse
        for i in range(self.num_bands):
            val = float(self.frame.bands[i])
            bh = val * base_y * 0.7
            cx = (i + 0.5) * slot
            r = int(120 + 120 * pulse)
            color = QColor(r, 30, 160, 130)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(color)
            painter.drawRect(QRectF(cx - slot * 0.3, base_y - bh, slot * 0.6, bh))

    def _draw_character(self, painter: QPainter, x: float, feet_y: float, pose: str) -> None:
        """Stylized goth-girl silhouette with a few pose variations."""
        body_h = self.height() * 0.42
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
        # Pick the nearest character.
        x = pos.x() / max(1, self.width())
        i = int(np.argmin([abs(a - x) for a in self._anchors]))
        if button == Qt.MouseButton.LeftButton:
            cur = self._poses[i]
            nxt = POSES[(POSES.index(cur) + 1) % len(POSES)] if cur in POSES else "dance"
            self._poses[i] = nxt
            self._pose_timer[i] = 2.0
