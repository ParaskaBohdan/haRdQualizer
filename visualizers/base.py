"""BaseVisualizer — common contract for every theme.

A visualizer is a ``QWidget`` that:
  * receives an :class:`AnalysisFrame` each render tick via :meth:`update_frame`,
  * paints itself in :meth:`paintEvent` (subclasses override :meth:`render`),
  * receives normalized mouse interactions through hook methods.

Mouse handling is centralized here so subclasses only implement the hooks they
care about. Positions passed to hooks are in widget pixel coordinates; helpers
convert an x position to a band index.
"""
from __future__ import annotations

from PyQt6.QtCore import QPoint, Qt
from PyQt6.QtGui import QMouseEvent, QPainter
from PyQt6.QtWidgets import QWidget

from engine import AnalysisFrame


class BaseVisualizer(QWidget):
    """Abstract base for all theme visualizers."""

    #: Human-readable theme key, set by subclasses.
    theme_key: str = "base"

    def __init__(self, num_bands: int, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.num_bands = num_bands
        self.frame: AnalysisFrame | None = None
        self._drag_button: Qt.MouseButton | None = None
        self._drag_start: QPoint | None = None
        self.setMouseTracking(True)
        self.setAutoFillBackground(True)

    # --- data in -----------------------------------------------------------
    def update_frame(self, frame: AnalysisFrame) -> None:
        """Called once per render tick with the latest analysis."""
        self.frame = frame
        self.on_frame(frame)
        self.update()  # schedule a repaint

    def on_frame(self, frame: AnalysisFrame) -> None:
        """Optional hook: react to a new frame (e.g. spawn particles on drop)."""

    # --- geometry helpers --------------------------------------------------
    def band_at(self, x: float) -> int:
        """Map an x pixel coordinate to a band index."""
        if self.width() <= 0:
            return 0
        idx = int(x / self.width() * self.num_bands)
        return max(0, min(self.num_bands - 1, idx))

    # --- painting ----------------------------------------------------------
    def paintEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.render(painter)
        painter.end()

    def render(self, painter: QPainter) -> None:
        """Subclasses draw the visualization here."""
        raise NotImplementedError

    # --- mouse plumbing ----------------------------------------------------
    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        self._drag_button = event.button()
        self._drag_start = event.position().toPoint()
        self.on_press(event.button(), self._drag_start)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        pos = event.position().toPoint()
        if self._drag_button is not None and self._drag_start is not None:
            self.on_drag(self._drag_button, self._drag_start, pos)
        else:
            self.on_hover(pos)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        self.on_release(event.button(), event.position().toPoint())
        self._drag_button = None
        self._drag_start = None

    # --- interaction hooks (override as needed) ----------------------------
    def on_press(self, button: Qt.MouseButton, pos: QPoint) -> None: ...
    def on_release(self, button: Qt.MouseButton, pos: QPoint) -> None: ...
    def on_drag(self, button: Qt.MouseButton, start: QPoint, pos: QPoint) -> None: ...
    def on_hover(self, pos: QPoint) -> None: ...
