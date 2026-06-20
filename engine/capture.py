"""System-audio capture via WASAPI loopback (PyAudioWPatch).

Loopback recording captures whatever is playing on the default output device —
the same audio you hear — without routing through a microphone. On non-Windows
platforms, or if PyAudioWPatch is unavailable, the capture falls back to a
silent stub so the rest of the app still runs.
"""
from __future__ import annotations

import threading
from typing import Callable, Optional

import numpy as np

try:
    import pyaudiowpatch as pyaudio  # type: ignore
    _HAS_PYAUDIO = True
except ImportError:  # pragma: no cover - depends on platform/install
    pyaudio = None  # type: ignore
    _HAS_PYAUDIO = False


# Callback receives a mono float32 numpy array of captured frames.
SampleCallback = Callable[[np.ndarray], None]


class LoopbackCapture:
    """Captures the default output device's audio on a background thread."""

    def __init__(self, on_samples: SampleCallback, chunk_size: int = 1024) -> None:
        self._on_samples = on_samples
        self._chunk_size = int(chunk_size)
        self._pa: Optional["pyaudio.PyAudio"] = None
        self._stream = None
        self._running = False
        self._channels = 2
        self.sample_rate = 48000
        self.device_name = "n/a"

    @property
    def available(self) -> bool:
        return _HAS_PYAUDIO

    @property
    def running(self) -> bool:
        return self._running

    def _find_loopback_device(self) -> Optional[dict]:
        """Locate the loopback device matching the default output."""
        assert self._pa is not None
        try:
            wasapi = self._pa.get_host_api_info_by_type(pyaudio.paWASAPI)
        except OSError:
            return None
        default_out = self._pa.get_device_info_by_index(
            wasapi["defaultOutputDevice"]
        )
        # PyAudioWPatch exposes loopback variants flagged with isLoopbackDevice.
        for info in self._pa.get_loopback_device_info_generator():
            if default_out["name"] in info["name"]:
                return info
        # Fall back to the first available loopback device.
        for info in self._pa.get_loopback_device_info_generator():
            return info
        return None

    def start(self) -> bool:
        """Open and start the loopback stream. Returns True on success."""
        if self._running:
            return True
        if not _HAS_PYAUDIO:
            return False

        self._pa = pyaudio.PyAudio()
        device = self._find_loopback_device()
        if device is None:
            self._pa.terminate()
            self._pa = None
            return False

        self._channels = int(device["maxInputChannels"]) or 2
        self.sample_rate = int(device["defaultSampleRate"])
        self.device_name = str(device["name"])

        self._stream = self._pa.open(
            format=pyaudio.paFloat32,
            channels=self._channels,
            rate=self.sample_rate,
            frames_per_buffer=self._chunk_size,
            input=True,
            input_device_index=device["index"],
            stream_callback=self._pa_callback,
        )
        self._running = True
        self._stream.start_stream()
        return True

    def _pa_callback(self, in_data, frame_count, time_info, status):  # noqa: ANN001
        """PortAudio callback — runs on the audio thread."""
        samples = np.frombuffer(in_data, dtype=np.float32)
        if self._channels > 1:
            # Downmix interleaved channels to mono by averaging.
            samples = samples.reshape(-1, self._channels).mean(axis=1)
        try:
            self._on_samples(samples)
        except Exception:  # pragma: no cover - never kill the audio thread
            pass
        return (None, pyaudio.paContinue)

    def stop(self) -> None:
        self._running = False
        if self._stream is not None:
            try:
                self._stream.stop_stream()
                self._stream.close()
            except Exception:  # pragma: no cover
                pass
            self._stream = None
        if self._pa is not None:
            self._pa.terminate()
            self._pa = None


class SilentCapture:
    """No-op fallback used when loopback capture is unavailable.

    Emits zero-filled buffers on a timer so the pipeline keeps ticking and the
    UI stays responsive (showing a flat spectrum) instead of crashing.
    """

    def __init__(self, on_samples: SampleCallback, chunk_size: int = 1024) -> None:
        self._on_samples = on_samples
        self._chunk_size = int(chunk_size)
        self.sample_rate = 48000
        self.device_name = "silent (no loopback)"
        self._running = False
        self._thread: Optional[threading.Thread] = None

    @property
    def available(self) -> bool:
        return True

    @property
    def running(self) -> bool:
        return self._running

    def start(self) -> bool:
        if self._running:
            return True
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        return True

    def _loop(self) -> None:
        import time

        silence = np.zeros(self._chunk_size, dtype=np.float32)
        interval = self._chunk_size / self.sample_rate
        while self._running:
            self._on_samples(silence)
            time.sleep(interval)

    def stop(self) -> None:
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=1.0)
            self._thread = None


def make_capture(on_samples: SampleCallback, chunk_size: int = 1024):
    """Return a working capture backend, preferring real loopback."""
    if _HAS_PYAUDIO:
        return LoopbackCapture(on_samples, chunk_size)
    return SilentCapture(on_samples, chunk_size)
