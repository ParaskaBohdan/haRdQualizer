"""Spectrum post-processing: FFT bins -> log-spaced bands with smoothing & peaks.

Human pitch perception is roughly logarithmic, so we group the linear FFT bins
into ``num_bands`` log-spaced bands. Each band is temporally smoothed (so bars
fall gently rather than flicker) and tracked with a slowly-decaying peak marker.
"""
from __future__ import annotations

import numpy as np


class SpectrumProcessor:
    """Maps a normalized FFT spectrum to display-ready band/peak arrays."""

    def __init__(
        self,
        freqs: np.ndarray,
        num_bands: int,
        freq_min: float,
        freq_max: float,
        smoothing: float = 0.6,
        peak_decay: float = 0.92,
    ) -> None:
        self.num_bands = int(num_bands)
        self.smoothing = float(np.clip(smoothing, 0.0, 0.99))
        self.peak_decay = float(np.clip(peak_decay, 0.0, 1.0))

        self._bands = np.zeros(self.num_bands, dtype=np.float32)
        self._peaks = np.zeros(self.num_bands, dtype=np.float32)
        self._band_slices = self._build_band_slices(
            freqs, freq_min, freq_max, self.num_bands
        )
        # Centre frequency of each band, handy for visualizers/labels.
        self.band_freqs = self._band_centre_freqs(freqs, self._band_slices)

    @staticmethod
    def _build_band_slices(
        freqs: np.ndarray, fmin: float, fmax: float, n: int
    ) -> list[tuple[int, int]]:
        fmin = max(fmin, float(freqs[1]) if freqs.size > 1 else 1.0)
        fmax = min(fmax, float(freqs[-1]))
        edges = np.logspace(np.log10(fmin), np.log10(fmax), n + 1)
        slices: list[tuple[int, int]] = []
        for i in range(n):
            lo = int(np.searchsorted(freqs, edges[i], side="left"))
            hi = int(np.searchsorted(freqs, edges[i + 1], side="right"))
            hi = max(hi, lo + 1)  # ensure every band owns at least one bin
            slices.append((lo, hi))
        return slices

    @staticmethod
    def _band_centre_freqs(
        freqs: np.ndarray, slices: list[tuple[int, int]]
    ) -> np.ndarray:
        return np.array(
            [float(freqs[lo:hi].mean()) for lo, hi in slices], dtype=np.float32
        )

    def process(self, spectrum: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Update internal state from a new spectrum; return (bands, peaks)."""
        raw = np.empty(self.num_bands, dtype=np.float32)
        for i, (lo, hi) in enumerate(self._band_slices):
            # Peak within the band reads more lively than the mean.
            raw[i] = spectrum[lo:hi].max()

        # Exponential smoothing: rise quickly, fall by the smoothing factor.
        a = self.smoothing
        rising = raw > self._bands
        self._bands = np.where(
            rising, raw, a * self._bands + (1.0 - a) * raw
        ).astype(np.float32)

        # Peak-hold with slow decay.
        self._peaks *= self.peak_decay
        self._peaks = np.maximum(self._peaks, self._bands)

        return self._bands.copy(), self._peaks.copy()

    def reset(self) -> None:
        self._bands.fill(0.0)
        self._peaks.fill(0.0)
