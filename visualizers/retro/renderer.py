"""Retro 80s visualizer — segmented LED equalizer with peak-hold and scanlines.

Each band is a stack of discrete LED segments that light green -> yellow -> red.
A bright peak-hold segment lingers at the top. CRT scanlines and a soft glow
sell the vintage-stereo look.

Interactions:
  * Left-click : "burn out" a segment of a bar (blinks dark, then recovers).
  * Right-click: cycle the LED colour scheme (classic / cyan / amber mono).
"""
from __future__ import annotations

import time

import numpy as np
from PyQt6.QtCore import QPoint, QRectF, Qt
from PyQt6.QtGui import QColor, QPainter

from ..base import BaseVisualizer

SEGMENTS = 16  # LED cells per bar

SCHEMES = {
    "classic": None,  # computed by height (green/yellow/red)
    "cyan": [(0, 200, 255)],
    "amber": [(255, 170, 40)],
}
SCHEME_ORDER = ("classic", "cyan", "amber")


class RetroVisualizer(BaseVisualizer):
    theme_key = "retro"

    def __init__(self, num_bands: int, parent=None) -> None:
        super().__init__(num_bands, parent)
        self._scheme = "classic"
        self._burn = np.full((num_bands, SEGMENTS), -1.0, dtype=np.float32)  # burnout timers
        self._vu = 0.0
        self._last_t = time.perf_counter()

    def on_frame(self, frame) -> None:
        now = time.perf_counter()
        dt = now - self._last_t
        self._last_t = now
        self._burn = np.where(self._burn > 0, self._burn - dt, self._burn)
        self._vu += (frame.level - self._vu) * min(1.0, dt * 8.0)

    def _seg_color(self, seg: int, lit: bool) -> QColor:
        if not lit:
            return QColor(28, 28, 28)
        if self._scheme == "classic":
            frac = seg / (SEGMENTS - 1)
            if frac > 0.82:
                return QColor(255, 60, 50)
            if frac > 0.6:
                return QColor(255, 210, 50)
            return QColor(60, 230, 90)
        rgb = SCHEMES[self._scheme][0]
        return QColor(*rgb)

    def render(self, painter: QPainter) -> None:
        w, h = self.width(), self.height()
        painter.fillRect(0, 0, w, h, QColor(18, 18, 20))
        if self.frame is None:
            return

        margin = 14
        meter_h = h - margin * 2 - 40  # leave room for VU strip
        slot = (w - margin * 2) / self.num_bands
        seg_h = meter_h / SEGMENTS
        gap = seg_h * 0.18

        for i in range(self.num_bands):
            val = float(self.frame.bands[i])
            lit_count = int(round(val * SEGMENTS))
            peak_seg = int(round(float(self.frame.peaks[i]) * (SEGMENTS - 1)))
            x = margin + i * slot
            bw = slot * 0.8
            for s in range(SEGMENTS):
                y = margin + meter_h - (s + 1) * seg_h
                lit = s < lit_count
                if self._burn[i, s] > 0:  # burned-out segment stays dark
                    lit = False
                color = self._seg_color(s, lit or s == peak_seg)
                if s == peak_seg and not lit:
                    color = QColor(255, 255, 255)
                painter.fillRect(QRectF(x, y + gap / 2, bw, seg_h - gap), color)

        self._draw_vu(painter, w, h, margin)
        self._draw_scanlines(painter, w, h)

    def _draw_vu(self, painter: QPainter, w: int, h: int, margin: int) -> None:
        # Simple horizontal VU strip at the bottom.
        y = h - margin - 24
        painter.setPen(QColor(90, 90, 90))
        painter.drawRect(QRectF(margin, y, w - margin * 2, 18))
        fill = (w - margin * 2) * float(np.clip(self._vu, 0, 1))
        col = QColor(60, 230, 90) if self._vu < 0.7 else QColor(255, 60, 50)
        painter.fillRect(QRectF(margin + 1, y + 1, max(0.0, fill - 2), 16), col)

    def _draw_scanlines(self, painter: QPainter, w: int, h: int) -> None:
        painter.setPen(QColor(0, 0, 0, 50))
        for y in range(0, h, 3):
            painter.drawLine(0, y, w, y)

    # --- interactions ------------------------------------------------------
    def on_press(self, button, pos: QPoint) -> None:
        if button == Qt.MouseButton.LeftButton:
            idx = self.band_at(pos.x())
            seg = int(np.random.randint(0, SEGMENTS))
            self._burn[idx, seg] = 1.5  # dark for 1.5s
        elif button == Qt.MouseButton.RightButton:
            cur = SCHEME_ORDER.index(self._scheme)
            self._scheme = SCHEME_ORDER[(cur + 1) % len(SCHEME_ORDER)]
