"""Main application window: toolbar, render loop, theme/language switching."""
from __future__ import annotations

import time

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QAction, QActionGroup
from PyQt6.QtWidgets import QMainWindow, QToolBar, QWidget

import config
from engine import AudioEngine
from visualizers import BaseVisualizer, get_visualizer

from .i18n import tr, translator


class MainWindow(QMainWindow):
    """Hosts the active visualizer and drives it from the audio engine."""

    def __init__(self) -> None:
        super().__init__()
        self.engine = AudioEngine()
        self.engine.start()

        self._theme = config.DEFAULT_THEME
        self._visualizer: BaseVisualizer | None = None
        self._fps = 0.0
        self._last_fps_t = time.perf_counter()
        self._frames = 0

        self.setWindowTitle(tr("app.title"))
        self.resize(config.WINDOW_WIDTH, config.WINDOW_HEIGHT)

        self._build_toolbar()
        self._set_theme(self._theme)
        self._build_statusbar()

        # Render loop.
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(int(1000 / config.TARGET_FPS))

    # --- UI construction ---------------------------------------------------
    def _build_toolbar(self) -> None:
        self._toolbar = QToolBar()
        self._toolbar.setMovable(False)
        self.addToolBar(self._toolbar)

        # Theme actions (exclusive group), keys 1-4.
        self._theme_group = QActionGroup(self)
        self._theme_group.setExclusive(True)
        for n, key in enumerate(config.THEMES, start=1):
            act = QAction(tr(f"theme.{key}"), self)
            act.setCheckable(True)
            act.setChecked(key == self._theme)
            act.setShortcut(str(n))
            act.triggered.connect(lambda _checked, k=key: self._set_theme(k))
            self._theme_group.addAction(act)
            self._toolbar.addAction(act)

        self._toolbar.addSeparator()

        # Language toggle.
        self._lang_group = QActionGroup(self)
        self._lang_group.setExclusive(True)
        for lang in config.LANGUAGES:
            act = QAction(lang.upper(), self)
            act.setCheckable(True)
            act.setChecked(lang == translator.language)
            act.triggered.connect(lambda _checked, ln=lang: self._set_language(ln))
            self._lang_group.addAction(act)
            self._toolbar.addAction(act)

    def _build_statusbar(self) -> None:
        self.statusBar()  # ensure it exists
        self._refresh_status("")

    # --- theme / language --------------------------------------------------
    def _set_theme(self, key: str) -> None:
        self._theme = key
        cls = get_visualizer(key)
        new_vis = cls(config.NUM_BANDS, self)
        self.setCentralWidget(new_vis)
        self._visualizer = new_vis

    def _set_language(self, lang: str) -> None:
        translator.set_language(lang)
        # Rebuild toolbar labels by recreating it.
        self.removeToolBar(self._toolbar)
        self._build_toolbar()
        self.setWindowTitle(tr("app.title"))

    # --- render loop -------------------------------------------------------
    def _tick(self) -> None:
        frame = self.engine.poll()
        if self._visualizer is not None:
            self._visualizer.update_frame(frame)

        self._frames += 1
        now = time.perf_counter()
        if now - self._last_fps_t >= 0.5:
            self._fps = self._frames / (now - self._last_fps_t)
            self._frames = 0
            self._last_fps_t = now
            self._refresh_status(self.engine.device_name)

    def _refresh_status(self, device: str) -> None:
        running = self.engine.running
        dev_label = device or tr("source.loopback")
        msg = f"{tr('status.device')}: {dev_label}   |   {tr('status.fps')}: {self._fps:.0f}"
        if not running:
            msg = f"{tr('status.no_audio')}   |   {msg}"
        self.statusBar().showMessage(msg)

    # --- shutdown ----------------------------------------------------------
    def closeEvent(self, event) -> None:  # noqa: N802
        self._timer.stop()
        self.engine.stop()
        super().closeEvent(event)
