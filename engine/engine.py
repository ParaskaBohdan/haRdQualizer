"""AudioEngine — wires capture, FFT, spectrum and beat detection together.

Threading model:
    * The capture backend calls ``_on_samples`` on the audio thread; it only
      appends to the ring buffer (cheap, lock-guarded).
    * The UI thread calls :meth:`poll` once per render frame to run the FFT and
      produce a fresh :class:`AnalysisFrame`. Keeping the FFT on the UI cadence
      avoids analyzing faster than we draw.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from config import AudioConfig, BeatConfig
from .audio_buffer import RingBuffer
from .beat_detector import BeatDetector
from .capture import make_capture
from .fft_analyzer import FFTAnalyzer
from .spectrum import SpectrumProcessor


@dataclass
class AnalysisFrame:
    """A single analyzed snapshot handed to the active visualizer."""

    bands: np.ndarray          # (num_bands,) smoothed magnitudes in [0, 1]
    peaks: np.ndarray          # (num_bands,) peak-hold markers in [0, 1]
    beat: bool                 # a beat fired this frame
    drop: bool                 # a drop fired this frame
    level: float               # overall RMS-ish loudness in [0, 1]
    band_freqs: np.ndarray     # (num_bands,) centre frequency per band


class AudioEngine:
    """Owns the capture backend and the DSP chain."""

    def __init__(
        self,
        audio_cfg: AudioConfig | None = None,
        beat_cfg: BeatConfig | None = None,
    ) -> None:
        self.audio_cfg = audio_cfg or AudioConfig()
        self.beat_cfg = beat_cfg or BeatConfig()

        # Ring buffer holds a few FFT windows worth of audio.
        self._buffer = RingBuffer(self.audio_cfg.fft_size * 4)
        self._capture = make_capture(
            self._on_samples, self.audio_cfg.chunk_size
        )

        # These are (re)built in start() once the real sample rate is known.
        self._fft: FFTAnalyzer | None = None
        self._spectrum: SpectrumProcessor | None = None
        self._beat: BeatDetector | None = None

    @property
    def device_name(self) -> str:
        return getattr(self._capture, "device_name", "n/a")

    @property
    def running(self) -> bool:
        return getattr(self._capture, "running", False)

    def _on_samples(self, samples: np.ndarray) -> None:
        self._buffer.write(samples)

    def _build_chain(self, sample_rate: int) -> None:
        self._fft = FFTAnalyzer(
            self.audio_cfg.fft_size,
            sample_rate,
            window=self.audio_cfg.window,
            db_floor=self.audio_cfg.db_floor,
            db_ceiling=self.audio_cfg.db_ceiling,
        )
        self._spectrum = SpectrumProcessor(
            self._fft.freqs,
            self.audio_cfg.num_bands,
            self.audio_cfg.freq_min,
            self.audio_cfg.freq_max,
            smoothing=self.audio_cfg.smoothing,
            peak_decay=self.audio_cfg.peak_decay,
        )
        self._beat = BeatDetector(
            self._fft.freqs,
            band_hz=self.beat_cfg.band_hz,
            beat_sensitivity=self.beat_cfg.beat_sensitivity,
            drop_silence_frames=self.beat_cfg.drop_silence_frames,
            drop_sensitivity=self.beat_cfg.drop_sensitivity,
        )

    def start(self) -> bool:
        """Start capturing and build the DSP chain. Returns True on success."""
        ok = self._capture.start()
        sample_rate = getattr(self._capture, "sample_rate", self.audio_cfg.sample_rate)
        self._build_chain(sample_rate)
        return ok

    def stop(self) -> None:
        self._capture.stop()

    def poll(self) -> AnalysisFrame:
        """Run one analysis cycle on the most recent audio. UI-thread only."""
        assert self._fft is not None and self._spectrum is not None
        assert self._beat is not None

        frame = self._buffer.latest(self.audio_cfg.fft_size)
        spectrum = self._fft.analyze(frame)
        bands, peaks = self._spectrum.process(spectrum)
        beat, drop = self._beat.update(spectrum)
        level = float(np.sqrt(np.mean(frame.astype(np.float64) ** 2)) * 4.0)
        level = min(level, 1.0)

        return AnalysisFrame(
            bands=bands,
            peaks=peaks,
            beat=beat,
            drop=drop,
            level=level,
            band_freqs=self._spectrum.band_freqs,
        )
