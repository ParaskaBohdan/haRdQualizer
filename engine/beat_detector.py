"""Beat and drop detection from the bass energy of the spectrum.

* **Beat** — instantaneous bass energy exceeds a multiple of its running
  average (a classic energy-based onset detector).
* **Drop** — a stretch of quiet frames followed by a sudden energy surge,
  i.e. the build-up-then-explosion common in electronic music.

Both are returned as one-shot boolean flags per frame; visualizers subscribe to
them to trigger animations.
"""
from __future__ import annotations

import numpy as np


class BeatDetector:
    """Tracks bass energy to flag beats and drops on each processed frame."""

    def __init__(
        self,
        freqs: np.ndarray,
        band_hz: tuple[float, float] = (30.0, 150.0),
        beat_sensitivity: float = 1.4,
        drop_silence_frames: int = 12,
        drop_sensitivity: float = 2.2,
        history: int = 43,  # ~1s of frames at 60 fps minus overlap
    ) -> None:
        lo = int(np.searchsorted(freqs, band_hz[0], side="left"))
        hi = int(np.searchsorted(freqs, band_hz[1], side="right"))
        self._bass_slice = slice(lo, max(hi, lo + 1))
        self._beat_sensitivity = float(beat_sensitivity)
        self._drop_silence_frames = int(drop_silence_frames)
        self._drop_sensitivity = float(drop_sensitivity)

        self._energy_hist = np.zeros(history, dtype=np.float32)
        self._hist_pos = 0
        self._quiet_run = 0
        self._cooldown = 0  # frames to wait before another beat can fire

    def update(self, spectrum: np.ndarray) -> tuple[bool, bool]:
        """Feed a normalized FFT spectrum; return (beat, drop) flags."""
        energy = float(spectrum[self._bass_slice].mean())
        avg = float(self._energy_hist.mean()) or 1e-6

        beat = False
        drop = False

        if self._cooldown > 0:
            self._cooldown -= 1

        # Drop: we were quiet for a while, now energy explodes.
        if (
            self._quiet_run >= self._drop_silence_frames
            and energy > avg * self._drop_sensitivity
        ):
            drop = True
            beat = True
            self._cooldown = 6
            self._quiet_run = 0
        elif energy > avg * self._beat_sensitivity and self._cooldown == 0:
            beat = True
            self._cooldown = 6

        # Track quiet streak for drop priming.
        if energy < avg * 0.6:
            self._quiet_run += 1
        elif not drop:
            self._quiet_run = 0

        # Roll energy into the history ring.
        self._energy_hist[self._hist_pos] = energy
        self._hist_pos = (self._hist_pos + 1) % self._energy_hist.size

        return beat, drop
