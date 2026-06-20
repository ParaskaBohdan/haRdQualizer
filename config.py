"""Central configuration and constants for haRdQualizer.

Tunable defaults live here. Runtime-changeable settings (sensitivity, theme,
language) are persisted separately to a JSON file via the settings module.
"""
from __future__ import annotations

from dataclasses import dataclass, field

# --- Audio capture ---------------------------------------------------------
SAMPLE_RATE = 48000          # Hz; overridden by the device's native rate
CHANNELS = 2                 # stereo loopback, downmixed to mono for analysis
CHUNK_SIZE = 1024            # frames read per callback (latency vs. resolution)

# --- FFT -------------------------------------------------------------------
FFT_SIZE = 2048              # samples per FFT window (power of two)
WINDOW = "hann"             # hann | hamming | blackman | none
DB_FLOOR = -80.0            # dB level mapped to 0.0 in the normalized spectrum
DB_CEILING = 0.0            # dB level mapped to 1.0

# --- Spectrum / bands ------------------------------------------------------
NUM_BANDS = 64              # number of visualized frequency bars
FREQ_MIN = 30.0            # Hz; lowest band edge
FREQ_MAX = 16000.0        # Hz; highest band edge
SMOOTHING = 0.6           # 0..1 temporal smoothing (higher = smoother/slower)
PEAK_DECAY = 0.92         # per-frame multiplier for peak-hold markers

# --- Beat / drop detection -------------------------------------------------
BEAT_BAND_HZ = (30.0, 150.0)   # bass range watched for beats
BEAT_SENSITIVITY = 1.4         # energy must exceed this * running average
DROP_SILENCE_FRAMES = 12       # quiet frames that prime a "drop"
DROP_SENSITIVITY = 2.2         # jump factor that fires a drop event

# --- Rendering -------------------------------------------------------------
TARGET_FPS = 60
WINDOW_WIDTH = 1100
WINDOW_HEIGHT = 650

# --- Themes ----------------------------------------------------------------
THEMES = ("dark_physics", "cartoon", "alt_gothic", "retro")
DEFAULT_THEME = "dark_physics"

# --- i18n ------------------------------------------------------------------
LANGUAGES = ("en", "uk")
DEFAULT_LANGUAGE = "uk"


@dataclass
class AudioConfig:
    """Snapshot of audio-engine parameters, passed to engine components."""

    sample_rate: int = SAMPLE_RATE
    channels: int = CHANNELS
    chunk_size: int = CHUNK_SIZE
    fft_size: int = FFT_SIZE
    window: str = WINDOW
    db_floor: float = DB_FLOOR
    db_ceiling: float = DB_CEILING
    num_bands: int = NUM_BANDS
    freq_min: float = FREQ_MIN
    freq_max: float = FREQ_MAX
    smoothing: float = SMOOTHING
    peak_decay: float = PEAK_DECAY


@dataclass
class BeatConfig:
    """Snapshot of beat/drop detector parameters."""

    band_hz: tuple[float, float] = BEAT_BAND_HZ
    beat_sensitivity: float = BEAT_SENSITIVITY
    drop_silence_frames: int = DROP_SILENCE_FRAMES
    drop_sensitivity: float = DROP_SENSITIVITY
