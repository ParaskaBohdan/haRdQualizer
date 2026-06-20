"""A tiny vectorized particle system for shatter / spark effects.

All particles live in flat numpy arrays so updates are a few array ops per
frame regardless of count. Positions are in widget pixel space.
"""
from __future__ import annotations

import numpy as np

GRAVITY = 900.0  # px/s^2


class ParticleSystem:
    """Fixed-capacity pool of short-lived particles."""

    def __init__(self, capacity: int = 600) -> None:
        self._cap = capacity
        self.pos = np.zeros((capacity, 2), dtype=np.float32)
        self.vel = np.zeros((capacity, 2), dtype=np.float32)
        self.life = np.zeros(capacity, dtype=np.float32)      # seconds remaining
        self.max_life = np.ones(capacity, dtype=np.float32)
        self.color = np.zeros((capacity, 3), dtype=np.float32)  # RGB 0..255
        self.size = np.zeros(capacity, dtype=np.float32)
        self._cursor = 0

    def emit(
        self,
        x: float,
        y: float,
        count: int,
        color: tuple[float, float, float],
        speed: float = 320.0,
        spread: float = 1.0,
    ) -> None:
        """Spawn ``count`` particles bursting outward from (x, y)."""
        for _ in range(count):
            i = self._cursor
            self._cursor = (self._cursor + 1) % self._cap
            angle = np.random.uniform(0, 2 * np.pi)
            mag = np.random.uniform(0.3, 1.0) * speed
            self.pos[i] = (x, y)
            self.vel[i] = (
                np.cos(angle) * mag * spread,
                np.sin(angle) * mag - speed * 0.4,  # bias upward
            )
            life = np.random.uniform(0.4, 1.1)
            self.life[i] = life
            self.max_life[i] = life
            self.color[i] = color
            self.size[i] = np.random.uniform(2.0, 5.0)

    def update(self, dt: float, bounds_h: float) -> None:
        """Advance physics by ``dt`` seconds; floor bounce at ``bounds_h``."""
        alive = self.life > 0
        if not alive.any():
            return
        self.vel[alive, 1] += GRAVITY * dt
        self.pos[alive] += self.vel[alive] * dt

        # Simple floor bounce with energy loss.
        below = alive & (self.pos[:, 1] > bounds_h)
        self.pos[below, 1] = bounds_h
        self.vel[below, 1] *= -0.45
        self.vel[below, 0] *= 0.8

        self.life[alive] -= dt

    def active_mask(self) -> np.ndarray:
        return self.life > 0
