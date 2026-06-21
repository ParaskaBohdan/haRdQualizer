"""Alt / Gothic visualizer — layered goth-girl rigs over a smooth purple flame.

Characters are :class:`CharacterRig` instances (see ``rig.py``): paper-dolls that
articulate to the music. ``back`` characters are smaller and drawn behind the
spectrum; ``front`` ones stand before it. Real art drops into
``assets/characters/<name>/``; until then a procedural silhouette stands in.

Scene atmosphere: a glowing moon, a twinkling star field, a gothic city skyline
silhouette and a low fog band. The spectrum is a single smooth connected flame
that pulses red on bass and flares on the drop, while the girls rim-glow with the
bass and hop on the drop. Particles: bats drifting across, rose petals on beats.
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
    QRadialGradient,
)

from ..base import BaseVisualizer
from .rig import CharacterRig

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
        # A central back girl appears only once real goth_b art is dropped in.
        center = CharacterRig(0.50, 0.86, 0.20, depth="back", name="goth_b", hair_hue=280)
        if center.load_assets(_ASSET_DIR) and center.has_body_art:
            self._rigs.insert(0, center)
        # The realistic "hero" (goth_d) takes front-centre stage once she exists.
        hero = CharacterRig(0.50, 0.99, 0.34, depth="front", name="goth_d", hair_hue=290)
        if hero.load_assets(_ASSET_DIR) and hero.has_body_art:
            self._rigs.append(hero)

        self._bass_pulse = 0.0
        self._drop_flash = 0.0       # flame flare on the drop
        self._screen_pulse = 0.0     # full-screen flash on the drop
        self._t = 0.0                # time accumulator for twinkling
        self._bats: list[list[float]] = []    # [x, y, vx, phase]
        self._petals: list[list[float]] = []  # [x, y, vy, drift]
        self._stars = self._make_stars(70)
        self._skyline = self._make_skyline()
        self._last_t = time.perf_counter()

    # --- procedural scene props -------------------------------------------
    @staticmethod
    def _make_stars(n: int) -> list[tuple[float, float, float, float]]:
        rng = np.random.default_rng(7)
        return [(float(rng.uniform(0, 1)), float(rng.uniform(0, 0.55)),
                 float(rng.uniform(0.6, 1.8)), float(rng.uniform(0, 6.28)))
                for _ in range(n)]

    @staticmethod
    def _make_skyline() -> list[tuple[float, float, float, bool]]:
        """List of (x_frac, width_frac, top_y_frac, has_spire) buildings."""
        rng = np.random.default_rng(13)
        out = []
        x = -0.02
        while x < 1.02:
            wf = float(rng.uniform(0.04, 0.10))
            top = float(rng.uniform(0.60, 0.80))
            out.append((x, wf, top, bool(rng.random() < 0.35)))
            x += wf * float(rng.uniform(0.9, 1.3))
        return out

    # --- per-frame update --------------------------------------------------
    def on_frame(self, frame) -> None:
        now = time.perf_counter()
        dt = now - self._last_t
        self._last_t = now
        self._t += dt

        bass = float(frame.bands[: max(1, self.num_bands // 8)].mean())
        self._bass_pulse += (bass - self._bass_pulse) * min(1.0, dt * 6.0)
        if frame.drop:
            self._drop_flash = 1.0
            self._screen_pulse = 1.0
        self._drop_flash = max(0.0, self._drop_flash - dt * 1.6)
        self._screen_pulse = max(0.0, self._screen_pulse - dt * 2.2)

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

    # --- painting ----------------------------------------------------------
    def render(self, painter: QPainter) -> None:
        w, h = self.width(), self.height()
        pulse = self._bass_pulse
        sky = QLinearGradient(0, 0, 0, h)
        sky.setColorAt(0.0, QColor(int(22 + 45 * pulse), 6, int(30 + 24 * pulse)))
        sky.setColorAt(1.0, QColor(6, 3, 10))
        painter.fillRect(0, 0, w, h, sky)
        if self.frame is None:
            return

        self._draw_backdrop(painter, w, h)

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

        if self._screen_pulse > 0.0:
            self._draw_screen_pulse(painter, w, h)

    def _draw_backdrop(self, painter: QPainter, w: int, h: int) -> None:
        """Moon + glow, twinkling stars, gothic skyline silhouette, fog."""
        painter.setPen(Qt.PenStyle.NoPen)

        # Stars (drawn first, faint, twinkling).
        for xf, yf, r, phase in self._stars:
            tw = 0.55 + 0.45 * np.sin(self._t * 2.0 + phase)
            painter.setBrush(QColor(220, 215, 240, int(150 * tw)))
            painter.drawEllipse(QRectF(xf * w, yf * h, r, r))

        # Moon with a soft halo, brightening slightly on bass.
        mx, my, mr = w * 0.80, h * 0.13, 46.0
        halo = QRadialGradient(mx, my, mr * 2.4)
        halo.setColorAt(0.0, QColor(220, 220, 245, int(120 + 60 * self._bass_pulse)))
        halo.setColorAt(1.0, QColor(220, 220, 245, 0))
        painter.setBrush(halo)
        painter.drawEllipse(QRectF(mx - mr * 2.4, my - mr * 2.4, mr * 4.8, mr * 4.8))
        painter.setBrush(QColor(235, 235, 248))
        painter.drawEllipse(QRectF(mx - mr, my - mr, mr * 2, mr * 2))
        painter.setBrush(QColor(210, 210, 230, 90))  # a couple of craters
        painter.drawEllipse(QRectF(mx - mr * 0.4, my - mr * 0.3, mr * 0.5, mr * 0.5))
        painter.drawEllipse(QRectF(mx + mr * 0.1, my + mr * 0.2, mr * 0.35, mr * 0.35))

        # Horizon glow so the black skyline reads against it.
        horizon = h * 0.9
        hg = QLinearGradient(0, h * 0.5, 0, horizon)
        hg.setColorAt(0.0, QColor(50, 12, 70, 0))
        hg.setColorAt(1.0, QColor(120, 45, 150, 95))
        painter.fillRect(QRectF(0, h * 0.5, w, horizon - h * 0.5), hg)

        # Gothic skyline silhouette along the horizon.
        painter.setBrush(QColor(6, 3, 11))
        for xf, wf, top, spire in self._skyline:
            bx, bw, by = xf * w, wf * w, top * h
            painter.drawRect(QRectF(bx, by, bw, horizon - by))
            if spire:  # a pointed roof / cathedral spire
                roof = QPolygonF([
                    QPointF(bx, by), QPointF(bx + bw / 2, by - bw * 0.9),
                    QPointF(bx + bw, by),
                ])
                painter.drawPolygon(roof)

        # Low fog band blending skyline, flame base and ground.
        fog = QLinearGradient(0, h * 0.66, 0, h)
        fog.setColorAt(0.0, QColor(60, 25, 80, 0))
        fog.setColorAt(0.6, QColor(70, 30, 95, 60))
        fog.setColorAt(1.0, QColor(40, 15, 60, 110))
        painter.fillRect(QRectF(0, h * 0.66, w, h * 0.34), fog)

    def _draw_flame_spectrum(self, painter: QPainter) -> None:
        """A single smooth, connected flame built from a spline through bands."""
        w, h = self.width(), self.height()
        bands = self.frame.bands
        n = self.num_bands
        base_y = h * 0.82
        flare = 1.0 + self._drop_flash * 0.4
        span = base_y * 0.62 * flare
        pulse = min(1.0, self._bass_pulse + self._drop_flash * 0.5)

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

        # Glowing top edge, drawn additively; brighter on the drop.
        painter.save()
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Plus)
        edge = QPainterPath()
        edge.moveTo(float(xs[0]), float(ys[0]))
        for i in range(1, n):
            mx = (xs[i - 1] + xs[i]) / 2.0
            my = (ys[i - 1] + ys[i]) / 2.0
            edge.quadTo(float(xs[i - 1]), float(ys[i - 1]), float(mx), float(my))
        edge.lineTo(float(xs[-1]), float(ys[-1]))
        boost = int(80 * self._drop_flash)
        for width, alpha in ((6.0, 60 + boost), (2.5, 150 + boost)):
            pen = QPen(QColor(220, 90, 220, min(255, alpha)))
            pen.setWidthF(width)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(edge)
        painter.restore()

    def _draw_screen_pulse(self, painter: QPainter, w: int, h: int) -> None:
        """A brief purple vignette flash on the drop."""
        p = self._screen_pulse
        vig = QRadialGradient(w / 2, h / 2, max(w, h) * 0.75)
        vig.setColorAt(0.0, QColor(150, 40, 200, 0))
        vig.setColorAt(0.7, QColor(150, 40, 200, int(30 * p)))
        vig.setColorAt(1.0, QColor(120, 20, 170, int(90 * p)))
        painter.save()
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Plus)
        painter.fillRect(QRectF(0, 0, w, h), vig)
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
