"""A tiny vectorized particle system for shatter / spark effects.

All particles live in flat numpy arrays so updates are a few array ops per
frame regardless of count. Positions are in widget pixel space. Each particle
carries a colour, a shrinking size and a velocity used both for motion and for
drawing a short motion-streak (trail) in the renderer.
"""
from __future__ import annotations

import numpy as np

GRAVITY = 820.0  # px/s^2
DRAG = 0.86      # per-second velocity damping (applied as drag**dt)


class ParticleSystem:
    """Fixed-capacity pool of short-lived particles."""

    def __init__(self, capacity: int = 1400) -> None:
        self._cap = capacity
        self.pos = np.zeros((capacity, 2), dtype=np.float32)
        self.vel = np.zeros((capacity, 2), dtype=np.float32)
        self.life = np.zeros(capacity, dtype=np.float32)      # seconds remaining
        self.max_life = np.ones(capacity, dtype=np.float32)
        self.color = np.zeros((capacity, 3), dtype=np.float32)  # RGB 0..255
        self.size = np.zeros(capacity, dtype=np.float32)
        self.spark = np.zeros(capacity, dtype=np.float32)     # 0=ember, 1=hot spark
        self._cursor = 0

    def emit(
        self,
        x: float,
        y: float,
        count: int,
        color: tuple[float, float, float],
        speed: float = 360.0,
        spread: float = 1.0,
    ) -> None:
        """Spawn ``count`` particles bursting outward from (x, y).

        Colours are jittered around the base hue; a fraction of particles are
        white-hot "sparks" that burn brighter and shorter for visual variety.
        """
        base = np.array(color, dtype=np.float32)
        for _ in range(count):
            i = self._cursor
            self._cursor = (self._cursor + 1) % self._cap

            angle = np.random.uniform(0, 2 * np.pi)
            mag = (np.random.uniform(0.15, 1.0) ** 0.5) * speed
            self.pos[i] = (x, y)
            self.vel[i] = (
                np.cos(angle) * mag * spread,
                np.sin(angle) * mag - speed * 0.35,  # bias upward
            )

            is_spark = np.random.random() < 0.35
            self.spark[i] = 1.0 if is_spark else 0.0
            if is_spark:
                # White-hot, small, short-lived.
                tint = np.random.uniform(0.55, 0.9)
                self.color[i] = base + (255.0 - base) * tint
                self.size[i] = np.random.uniform(1.5, 3.0)
                life = np.random.uniform(0.5, 1.1)
            else:
                # Coloured ember, larger, longer-lived.
                jitter = np.random.uniform(0.75, 1.15, size=3)
                self.color[i] = np.clip(base * jitter, 0, 255)
                self.size[i] = np.random.uniform(3.0, 7.0)
                life = np.random.uniform(1.0, 2.0)
            self.life[i] = life
            self.max_life[i] = life

    def update(self, dt: float, bounds_h: float) -> None:
        """Advance physics by ``dt`` seconds; floor bounce at ``bounds_h``."""
        alive = self.life > 0
        if not alive.any():
            return
        damp = DRAG ** dt
        self.vel[alive, 1] += GRAVITY * dt
        self.vel[alive] *= damp
        self.pos[alive] += self.vel[alive] * dt

        # Soft floor bounce with energy loss.
        below = alive & (self.pos[:, 1] > bounds_h)
        self.pos[below, 1] = bounds_h
        self.vel[below, 1] *= -0.4
        self.vel[below, 0] *= 0.75

        self.life[alive] -= dt

    def active_mask(self) -> np.ndarray:
        return self.life > 0
