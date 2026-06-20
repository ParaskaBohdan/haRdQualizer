"""haRdQualizer audio engine.

A self-contained DSP pipeline:

    capture -> audio_buffer -> fft_analyzer -> spectrum -> beat_detector

The public entry point is :class:`AudioEngine`, which wires the pieces together
and exposes the latest analysis frame to the UI thread.
"""
from .engine import AudioEngine, AnalysisFrame

__all__ = ["AudioEngine", "AnalysisFrame"]
