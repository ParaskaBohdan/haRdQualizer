"""Layered "paper-doll" rig for a goth-girl character.

A character is a stack of *layers* (hair_back, torso, head, arm_l, arm_r,
hair_front). Each layer is drawn around a pivot and can be rotated/translated
independently, so the same artwork articulates: arms raise on the drop, the
head bobs on the beat, hair sways with the bass, the whole body sways and
breathes, and she hops on a drop.

Art is optional. If a layer has a loaded ``QPixmap`` (real art, see
``assets/characters/<name>/``) it is drawn transformed; otherwise a procedural
silhouette stands in. The animation maths is identical either way, so dropping
in AI-generated PNGs needs no code changes.

Angle convention (degrees): an arm angle of 0 hangs straight down; positive
swings the arm outward/up, ~165 raises it overhead.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QPainter, QPixmap, QPolygonF

# Layer draw order (back to front).
LAYER_ORDER = ("hair_back", "arm_back", "torso", "head", "arm_l", "arm_r", "hair_front")

# Per-pose target arm angles (left, right) in degrees.
POSE_ARMS = {
    "idle":     (14.0, -14.0),
    "sway":     (22.0, -22.0),
    "dance":    (60.0, -60.0),   # amplitude; oscillated by body sway
    "hands_up": (158.0, -158.0),
    "horns":    (150.0, -18.0),  # left fist up, right hand low (devil horns)
}


@dataclass
class CharacterRig:
    """One animated character. Positions are fractions of the widget size."""

    x_frac: float
    feet_frac: float
    scale: float
    depth: str = "front"          # "back" | "front"
    name: str = "goth_a"
    hair_hue: int = 300           # base hair tint (HSV degrees); art overrides

    # --- runtime animation state (not set by caller) ---
    pose: str = "idle"
    pose_timer: float = 0.0
    _sway_phase: float = field(default_factory=lambda: 0.0)
    _breathe: float = 0.0
    _hair_angle: float = 0.0
    _hair_vel: float = 0.0
    _arm_l: float = 14.0
    _arm_r: float = -14.0
    _head_bob: float = 0.0        # downward px-ish, eased back
    _jump: float = 0.0            # upward offset
    _jump_vel: float = 0.0
    _pixmaps: dict = field(default_factory=dict)

    # --- asset loading -----------------------------------------------------
    def load_assets(self, base_dir: Path) -> int:
        """Load ``<base_dir>/<name>/<layer>.png`` for any present layers.

        Returns the number of layers found. Missing layers fall back to the
        procedural silhouette, so partial art is fine.
        """
        char_dir = base_dir / self.name
        found = 0
        if not char_dir.is_dir():
            return 0
        for layer in LAYER_ORDER:
            path = char_dir / f"{layer}.png"
            if path.is_file():
                pm = QPixmap(str(path))
                if not pm.isNull():
                    self._pixmaps[layer] = pm
                    found += 1
        return found

    # --- pose control ------------------------------------------------------
    def set_pose(self, pose: str, hold: float = 2.0) -> None:
        if pose in POSE_ARMS:
            self.pose = pose
            self.pose_timer = hold

    # --- per-frame update --------------------------------------------------
    def update(self, dt: float, level: float, beat: bool, drop: bool, bass: float) -> None:
        dt = min(dt, 0.05)

        # Pose lifetime: fall back to a loudness-driven pose when it expires.
        self.pose_timer = max(0.0, self.pose_timer - dt)
        if self.pose_timer == 0.0:
            self.pose = "dance" if level > 0.4 else ("sway" if level > 0.15 else "idle")

        # Body sway + breathing oscillators; faster/wider when louder.
        self._sway_phase += dt * (1.4 + level * 3.5)
        self._breathe = math.sin(self._sway_phase * 0.6) * (0.5 + level)

        # Target arm angles from pose; "dance" swings with the sway.
        tl, tr = POSE_ARMS.get(self.pose, POSE_ARMS["idle"])
        if self.pose == "dance":
            swing = math.sin(self._sway_phase * 2.0) * 35.0
            tl, tr = 50.0 + swing, -50.0 + swing
        ease = min(1.0, dt * 9.0)
        self._arm_l += (tl - self._arm_l) * ease
        self._arm_r += (tr - self._arm_r) * ease

        # Hair: damped spring pushed by sway velocity and bass hits.
        sway_force = math.cos(self._sway_phase * (1.4 + level * 3.5)) * 6.0
        self._hair_vel += (sway_force - self._hair_angle * 60.0 - self._hair_vel * 6.0) * dt
        if beat:
            self._hair_vel += bass * 8.0
        self._hair_angle += self._hair_vel * dt
        self._hair_angle = max(-0.5, min(0.5, self._hair_angle))

        # Head bob: a downward nudge on each beat, eased back.
        if beat:
            self._head_bob = min(1.0, self._head_bob + 0.6)
        self._head_bob = max(0.0, self._head_bob - dt * 3.0)

        # Jump on the drop: ballistic hop.
        if drop:
            self._jump_vel = 1.0
        self._jump_vel -= 3.0 * dt
        self._jump += self._jump_vel * dt
        if self._jump < 0.0:
            self._jump = 0.0
            self._jump_vel = 0.0

    # --- drawing -----------------------------------------------------------
    def draw(self, painter: QPainter, w: int, h: int) -> None:
        body_h = h * self.scale
        anchor_x = self.x_frac * w + math.sin(self._sway_phase) * body_h * 0.04
        feet_y = self.feet_frac * h - self._jump * body_h * 0.18

        geom = _Geometry(anchor_x, feet_y, body_h, self._breathe, self._head_bob)

        for layer in LAYER_ORDER:
            pm = self._pixmaps.get(layer)
            painter.save()
            self._apply_layer_transform(painter, layer, geom)
            if pm is not None:
                # Real art: drawn centred on the pivot at the layer's box.
                target = geom.layer_box(layer, pm)
                painter.drawPixmap(target, pm, QRectF(pm.rect()))
            else:
                _draw_procedural(painter, layer, geom, self)
            painter.restore()

    def _apply_layer_transform(self, painter: QPainter, layer: str, geom: "_Geometry") -> None:
        """Translate to the layer pivot and rotate per animation state."""
        if layer in ("arm_l", "arm_r", "arm_back"):
            sign = 1.0 if layer == "arm_l" else -1.0
            sx = geom.anchor_x + sign * geom.shoulder_dx
            sy = geom.shoulder_y
            painter.translate(sx, sy)
            angle = self._arm_l if layer == "arm_l" else self._arm_r
            painter.rotate(sign * angle)  # outward/up
        elif layer in ("hair_back", "hair_front"):
            painter.translate(geom.anchor_x, geom.head_y)
            painter.rotate(math.degrees(self._hair_angle))
        elif layer == "head":
            painter.translate(geom.anchor_x, geom.head_y - geom.head_bob_px)
        else:  # torso and anything else: anchored at the body centre
            painter.translate(geom.anchor_x, geom.shoulder_y)


@dataclass
class _Geometry:
    """Resolved pixel geometry for one frame, shared by all layers."""

    anchor_x: float
    feet_y: float
    body_h: float
    breathe: float
    head_bob: float

    def __post_init__(self) -> None:
        self.head_r = self.body_h * 0.13
        self.hip_y = self.feet_y - self.body_h * 0.45
        self.shoulder_dx = self.body_h * 0.1
        self.shoulder_y = self.feet_y - self.body_h * 0.78 + self.breathe
        self.head_y = self.shoulder_y - self.head_r * 1.6
        self.head_bob_px = -self.head_bob * self.body_h * 0.03

    def layer_box(self, layer: str, pm: QPixmap) -> QRectF:
        """Where a real-art pixmap for ``layer`` is drawn (centred on pivot)."""
        s = self.body_h / max(1, pm.height()) * 2.2  # scale art to body height
        bw, bh = pm.width() * s, pm.height() * s
        if layer in ("arm_l", "arm_r", "arm_back"):
            return QRectF(-bw * 0.2, 0.0, bw, bh)       # pivot near shoulder
        if layer in ("hair_back", "hair_front", "head"):
            return QRectF(-bw / 2, -bh / 2, bw, bh)     # pivot at centre
        return QRectF(-bw / 2, -self.head_r * 1.2, bw, bh)


def _draw_procedural(painter: QPainter, layer: str, g: "_Geometry", rig: CharacterRig) -> None:
    """Fallback silhouette art for a single layer, in the layer's local frame."""
    dress = QColor(15, 10, 20)
    skin = QColor(235, 225, 230)
    accent = QColor(150, 30, 95)
    hair = QColor.fromHsv(rig.hair_hue, 120, 40)

    painter.setPen(Qt.PenStyle.NoPen)
    bh = g.body_h

    if layer == "hair_back":
        painter.setBrush(hair)
        painter.drawEllipse(QRectF(-g.head_r * 1.5, -g.head_r * 1.1, g.head_r * 3.0, g.head_r * 4.2))
    elif layer == "torso":
        # Local origin at shoulder. Torso down to hips, then a skirt triangle.
        painter.setBrush(dress)
        torso_h = g.hip_y - g.shoulder_y
        painter.drawRect(QRectF(-bh * 0.09, 0.0, bh * 0.18, torso_h))
        skirt = QPolygonF([
            QPointF(-bh * 0.22, torso_h + bh * 0.45),
            QPointF(bh * 0.22, torso_h + bh * 0.45),
            QPointF(bh * 0.09, torso_h),
            QPointF(-bh * 0.09, torso_h),
        ])
        painter.drawPolygon(skirt)
    elif layer == "head":
        painter.setBrush(skin)
        painter.drawEllipse(QRectF(-g.head_r, -g.head_r, g.head_r * 2, g.head_r * 2))
        painter.setBrush(accent)  # choker
        painter.drawRect(QRectF(-g.head_r * 0.7, g.head_r * 0.9, g.head_r * 1.4, g.head_r * 0.3))
    elif layer in ("arm_l", "arm_r"):
        painter.setBrush(dress)
        arm_w = bh * 0.05
        arm_len = bh * 0.34
        painter.drawRoundedRect(QRectF(-arm_w / 2, 0.0, arm_w, arm_len), arm_w / 2, arm_w / 2)
        painter.setBrush(skin)  # hand
        painter.drawEllipse(QRectF(-arm_w * 0.7, arm_len - arm_w * 0.5, arm_w * 1.4, arm_w * 1.4))
    elif layer == "hair_front":
        painter.setBrush(hair)
        # Two side bangs framing the face.
        for sx in (-1, 1):
            painter.drawRect(QRectF(sx * g.head_r * 0.9 - g.head_r * 0.2,
                                    -g.head_r * 0.9, g.head_r * 0.4, g.head_r * 2.0))
