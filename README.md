# haRdQualizer

Interactive audio equalizer & visualizer for the desktop. Pick one of four hand-crafted
themes, point it at whatever is playing on your PC, and **play with the bars** — break them,
toss them around, freeze them, squeeze the waveform.

> **Status:** early development. Audio engine + UI shell + first visualizer.

## Features (planned)

- **Own audio engine** — system audio capture (WASAPI loopback), FFT, log-scaled bands,
  smoothing, peak-hold, beat/drop detection. No black-box visualizer library.
- **4 themes**, each interactive:
  1. **Dark Physics** — neon bars on black. Left-click shatters a bar into particles;
     left-drag tosses bars with gravity; right-click freezes one; right-drag squeezes /
     stretches the spectrum like an accordion.
  2. **Cartoon** — jelly bars with eyes and personalities; bubbles, stars and notes;
     bars pull faces on click and morph into objects on right-click.
  3. **Alt / Gothic** — goth-girl characters that change poses, throw their hands up on
     the drop, with bats, rose petals and a pulsing purple backdrop.
  4. **Retro 80s** — classic stereo LED equalizer: green→yellow→red segments, peak-hold,
     VU needle, CRT scanlines and glow.
- **Multilingual UI** — Ukrainian + English (gettext).
- Future: streaming integrations (Spotify / YouTube Music / SoundCloud) and a browser port.

## Architecture

```
engine/        own DSP pipeline: capture → buffer → FFT → spectrum → beat detection
ui/            PyQt6 window, theme switcher, settings, audio-source picker
visualizers/   one package per theme, all subclassing BaseVisualizer
```

See [the full plan](docs/PLAN.md) for phases and details.

## Tech stack

| Layer            | Library         |
|------------------|-----------------|
| Audio capture    | PyAudioWPatch (WASAPI loopback) |
| DSP / FFT        | numpy + scipy   |
| UI               | PyQt6           |
| Rendering        | pyqtgraph + QPainter |
| i18n             | gettext         |

## Quick start

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
python main.py
```

Play any audio on your PC and the bars react to it. Switch themes with the toolbar
or keys `1`–`4`.

## License

MIT (see [LICENSE](LICENSE)).
