"""Visualizer themes. Each theme is a BaseVisualizer subclass.

``REGISTRY`` maps theme keys (see config.THEMES) to their classes; the main
window uses it to build and switch visualizers. Themes are imported lazily in
:func:`get_visualizer` so a broken/optional theme never blocks app startup.
"""
from __future__ import annotations

from .base import BaseVisualizer


def get_visualizer(theme: str) -> type[BaseVisualizer]:
    """Return the visualizer class for a theme key."""
    if theme == "dark_physics":
        from .dark_physics.renderer import DarkPhysicsVisualizer
        return DarkPhysicsVisualizer
    if theme == "cartoon":
        from .cartoon.renderer import CartoonVisualizer
        return CartoonVisualizer
    if theme == "alt_gothic":
        from .alt_gothic.renderer import AltGothicVisualizer
        return AltGothicVisualizer
    if theme == "retro":
        from .retro.renderer import RetroVisualizer
        return RetroVisualizer
    raise KeyError(f"Unknown theme: {theme}")


__all__ = ["BaseVisualizer", "get_visualizer"]
