"""Thread-safe ring buffer bridging the audio thread and the UI thread.

The capture callback runs on PortAudio's thread and pushes mono samples in;
the UI/analysis thread pulls the most recent ``window`` samples out for FFT.
A single lock guards the underlying numpy array — writes and reads are short,
so contention is negligible.
"""
from __future__ import annotations

import threading

import numpy as np


class RingBuffer:
    """Fixed-size circular buffer of float32 mono samples."""

    def __init__(self, capacity: int) -> None:
        self._capacity = int(capacity)
        self._data = np.zeros(self._capacity, dtype=np.float32)
        self._write_pos = 0
        self._filled = 0
        self._lock = threading.Lock()

    @property
    def capacity(self) -> int:
        return self._capacity

    def write(self, samples: np.ndarray) -> None:
        """Append samples, overwriting the oldest data when full."""
        samples = np.asarray(samples, dtype=np.float32).ravel()
        n = samples.size
        if n == 0:
            return
        if n >= self._capacity:
            # Only the tail matters; copy the last `capacity` samples.
            samples = samples[-self._capacity:]
            n = self._capacity

        with self._lock:
            end = self._write_pos + n
            if end <= self._capacity:
                self._data[self._write_pos:end] = samples
            else:
                first = self._capacity - self._write_pos
                self._data[self._write_pos:] = samples[:first]
                self._data[: n - first] = samples[first:]
            self._write_pos = end % self._capacity
            self._filled = min(self._filled + n, self._capacity)

    def latest(self, count: int) -> np.ndarray:
        """Return the most recent ``count`` samples (oldest first).

        If fewer samples have been written, the result is left-padded with
        zeros so the caller always gets a fixed-length window.
        """
        count = int(count)
        out = np.zeros(count, dtype=np.float32)
        with self._lock:
            available = min(count, self._filled)
            if available == 0:
                return out
            start = (self._write_pos - available) % self._capacity
            end = start + available
            if end <= self._capacity:
                chunk = self._data[start:end]
            else:
                first = self._capacity - start
                chunk = np.concatenate(
                    (self._data[start:], self._data[: available - first])
                )
        out[-available:] = chunk
        return out

    def clear(self) -> None:
        with self._lock:
            self._data.fill(0.0)
            self._write_pos = 0
            self._filled = 0
