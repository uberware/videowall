"""Configuration."""

import json
from dataclasses import dataclass
from pathlib import Path

OPTIONS_FILE = Path.home() / "videowall_settings.json"
"""The path to where the settings file lives with all other settings."""

DEFAULT_QSS = (Path(__file__).parent / "style.qss").read_text()
"""Default QSS content string."""

DEFAULT_SPEC = {
    "type": "VideoWall",
    "orientation": "horizontal",
    "items": [
        {
            "type": "Player",
            "filename": "/Volumes/Movies-4/Groundhog.Day.1993.REMASTERED.1080p.BluRay.6CH.ShAaNiG.mp4",
            "speed": 1.0,
            "volume": 0.0,
        },
        {
            "type": "Player",
            "filename": "/Volumes/Movies-4/Godzilla.vs.Kong.2021.1080p.x264.ac3-nibo.mp4",
            "speed": 1.0,
            "volume": 0.0,
        },
    ],
    "sizes": [637, 636],
}
"""Default layout."""


@dataclass(frozen=True)
class _Options:
    """A class with the various settings for how things work."""

    movie_folder: Path
    spec_folder: Path
    always_on_top: bool
    restore_window_state: bool


def _load_options() -> _Options:
    """Loads the options and returns them as an Options object."""
    data = json.loads(OPTIONS_FILE.read_text() if OPTIONS_FILE.exists() else "{}")
    movie = Path(data.get("movie_folder", "/Volumes/x/Good"))
    spec = Path(data.get("spec_folder", "/Volumes/x/Videowalls"))
    top = bool(data.get("always_on_top", True))
    restore = bool(data.get("restore_window_state", False))
    return _Options(movie, spec, top, restore)


OPTIONS = _load_options()
"""The global options."""
