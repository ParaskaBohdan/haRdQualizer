"""Per-bar physics state for the Dark Physics theme.

Each bar normally tracks the audio band height, but interactions can override
that with physical behaviour:

* **toss**    — bar launched upward, falls under gravity, bounces (left-drag).
* **frozen**  — bar ignores audio for a few seconds, then thaws (right-click).
* **shatter** — bar collapses to zero and regrows (left-click); particles are
  emitted by the renderer.

A global ``squeeze`` factor (right-drag) horizontally compresses/expands the
whole bar field around the cursor.
"""
from __future__ import annotations

import numpy as np

GRAVITY = 2.2          # in normalized-height units per second^2
BOUNCE = 0.55
FREEZE_SECONDS = 3.0
SHATTER_REGROW = 1.8   # how fast a shattered bar returns to live tracking


class BarPhysics:
    """Holds physical state for ``n`` bars and blends it with audio heights."""

    def __init__(self, n: int) -> None:
        self.n = n
        self.height = np.zeros(n, dtype=np.float32)     # displayed height [0,1]
        self.velocity = np.zeros(n, dtype=np.float32)   # for tossed bars
        self.tossed = np.zeros(n, dtype=bool)
        self.freeze_timer = np.zeros(n, dtype=np.float32)
        self.shatter = np.zeros(n, dtype=np.float32)    # 0..1 regrow blend

        # Global horizontal squeeze: 1.0 = neutral; <1 compress, >1 expand.
        self.squeeze = 1.0
        self.squeeze_center = 0.5  # normalized x the squeeze pivots around

    # --- interactions ------------------------------------------------------
    def toss(self, idx: int, power: float) -> None:
        self.tossed[idx] = True
        self.velocity[idx] = max(self.velocity[idx], power)
        self.freeze_timer[idx] = 0.0

    def freeze(self, idx: int) -> None:
        self.freeze_timer[idx] = FREEZE_SECONDS
        self.tossed[idx] = False

    def shatter_bar(self, idx: int) -> None:
        self.shatter[idx] = 1.0
        self.height[idx] = 0.0
        self.tossed[idx] = False

    def set_squeeze(self, factor: float, center: float) -> None:
        self.squeeze = float(np.clip(factor, 0.25, 3.0))
        self.squeeze_center = float(np.clip(center, 0.0, 1.0))

    def reset_squeeze(self) -> None:
        self.squeeze = 1.0

    # --- per-frame update --------------------------------------------------
    def step(self, audio_heights: np.ndarray, dt: float) -> np.ndarray:
        """Blend audio with physics and return the heights to draw."""
        dt = min(dt, 0.05)  # clamp to avoid blow-ups on hitches

        # Tick down freeze timers.
        self.freeze_timer = np.maximum(self.freeze_timer - dt, 0.0)
        frozen = self.freeze_timer > 0.0

        # Tossed bars follow ballistic motion until they land.
        if self.tossed.any():
            self.velocity[self.tossed] -= GRAVITY * dt
            self.height[self.tossed] += self.velocity[self.tossed] * dt
            landed = self.tossed & (self.height <= audio_heights)
            # Bounce a few times, then hand back to audio tracking.
            bounce = landed & (np.abs(self.velocity) > 0.25)
            self.height[bounce] = audio_heights[bounce]
            self.velocity[bounce] = -self.velocity[bounce] * BOUNCE
            settled = landed & (np.abs(self.velocity) <= 0.25)
            self.tossed[settled] = False

        # Shattered bars regrow toward audio.
        regrow = self.shatter > 0.0
        self.shatter[regrow] = np.maximum(
            self.shatter[regrow] - SHATTER_REGROW * dt, 0.0
        )

        # Bars that are neither tossed/frozen/shattering track audio directly.
        free = ~self.tossed & ~frozen
        self.height[free] = audio_heights[free]

        # Frozen bars hold their height (do nothing).
        # Apply shatter blend (scales height down toward 0 while shattering).
        display = self.height * (1.0 - self.shatter)
        return np.clip(display, 0.0, 4.0)
