"""Lightweight runtime translation.

A full gettext .po/.mo pipeline is planned (see PLAN.md, Phase 8). For now we
keep an in-memory dictionary so the UI is multilingual from day one and strings
live in one place. ``tr(key)`` returns the active language's text, falling back
to English, then to the key itself.
"""
from __future__ import annotations

from config import DEFAULT_LANGUAGE

_TRANSLATIONS: dict[str, dict[str, str]] = {
    "en": {
        "app.title": "haRdQualizer",
        "theme.dark_physics": "Dark Physics",
        "theme.cartoon": "Cartoon",
        "theme.alt_gothic": "Alt / Gothic",
        "theme.retro": "Retro 80s",
        "toolbar.theme": "Theme",
        "toolbar.source": "Source",
        "toolbar.language": "Language",
        "source.loopback": "System audio",
        "status.device": "Device",
        "status.fps": "FPS",
        "status.no_audio": "No audio capture — showing silence",
    },
    "uk": {
        "app.title": "haRdQualizer",
        "theme.dark_physics": "Темна фізика",
        "theme.cartoon": "Мультяшний",
        "theme.alt_gothic": "Альт / Готика",
        "theme.retro": "Ретро 80-ті",
        "toolbar.theme": "Тема",
        "toolbar.source": "Джерело",
        "toolbar.language": "Мова",
        "source.loopback": "Системний звук",
        "status.device": "Пристрій",
        "status.fps": "Кадри/с",
        "status.no_audio": "Немає захоплення звуку — тиша",
    },
}


class Translator:
    """Holds the active language and resolves keys to strings."""

    def __init__(self, language: str = DEFAULT_LANGUAGE) -> None:
        self._language = language if language in _TRANSLATIONS else "en"

    @property
    def language(self) -> str:
        return self._language

    def set_language(self, language: str) -> None:
        if language in _TRANSLATIONS:
            self._language = language

    def tr(self, key: str) -> str:
        lang = _TRANSLATIONS.get(self._language, {})
        if key in lang:
            return lang[key]
        return _TRANSLATIONS["en"].get(key, key)


# Module-level singleton; the main window swaps the language on it.
translator = Translator()


def tr(key: str) -> str:
    return translator.tr(key)
