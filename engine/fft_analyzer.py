"""FFT analysis: windowed real FFT of a sample frame into a dB magnitude spectrum."""
from __future__ import annotations

import numpy as np


def make_window(name: str, size: int) -> np.ndarray:
    """Build a window function array of the given size."""
    name = (name or "none").lower()
    if name == "hann":
        return np.hanning(size).astype(np.float32)
    if name == "hamming":
        return np.hamming(size).astype(np.float32)
    if name == "blackman":
        return np.blackman(size).astype(np.float32)
    return np.ones(size, dtype=np.float32)


class FFTAnalyzer:
    """Turns a block of time-domain samples into a normalized magnitude spectrum.

    Output is a float32 array of ``fft_size // 2 + 1`` bins, each in ``[0, 1]``
    where 0 maps to ``db_floor`` and 1 maps to ``db_ceiling``.
    """

    def __init__(
        self,
        fft_size: int,
        sample_rate: int,
        window: str = "hann",
        db_floor: float = -80.0,
        db_ceiling: float = 0.0,
    ) -> None:
        self.fft_size = int(fft_size)
        self.sample_rate = int(sample_rate)
        self.db_floor = float(db_floor)
        self.db_ceiling = float(db_ceiling)
        self._window = make_window(window, self.fft_size)
        # Coherent-gain normalization so window choice doesn't change levels.
        self._win_sum = float(self._window.sum()) or 1.0
        self.freqs = np.fft.rfftfreq(self.fft_size, d=1.0 / self.sample_rate)

    def analyze(self, samples: np.ndarray) -> np.ndarray:
        """Return the normalized magnitude spectrum for ``samples``.

        ``samples`` is expected to be at least ``fft_size`` long; the trailing
        ``fft_size`` samples are used.
        """
        frame = np.asarray(samples, dtype=np.float32)
        if frame.size < self.fft_size:
            frame = np.pad(frame, (self.fft_size - frame.size, 0))
        elif frame.size > self.fft_size:
            frame = frame[-self.fft_size:]

        windowed = frame * self._window
        spectrum = np.fft.rfft(windowed)
        # Normalize magnitude by window sum and account for one-sided spectrum.
        mag = np.abs(spectrum) * (2.0 / self._win_sum)
        mag = np.maximum(mag, 1e-10)

        db = 20.0 * np.log10(mag)
        norm = (db - self.db_floor) / (self.db_ceiling - self.db_floor)
        return np.clip(norm, 0.0, 1.0).astype(np.float32)
