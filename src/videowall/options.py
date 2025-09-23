"""Configuration."""

import json
from dataclasses import dataclass
from pathlib import Path

OPTIONS_FILE = Path.home() / "videowall_settings.json"
"""The path to where the settings file lives with all other settings."""

DEFAULT_QSS = (Path(__file__).parent / "style.qss").read_text()
"""Default QSS content string."""

DEMO_SPEC = {
    "type": "VideoWall",
    "orientation": "horizontal",
    "items": [
        {
            "type": "Player",
            "filename": "/Volumes/Movies-4/Groundhog.Day.1993.REMASTERED.1080p.BluRay.6CH.ShAaNiG.mp4",
            "speed": 1.0,
            "volume": 0.0,
            "position": 300000,
        },
        {
            "type": "Player",
            "filename": "/Volumes/Movies-4/Godzilla.vs.Kong.2021.1080p.x264.ac3-nibo.mp4",
            "speed": 1.0,
            "volume": 0.0,
            "position": 600000,
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
    default_volume: float
    remaining_time: bool
    jog_interval: int
    open_last_on_startup: bool
    auto_update_layout: bool


def _load_options() -> _Options:
    """Loads the options and returns them as an Options object."""
    data = json.loads(OPTIONS_FILE.read_text() if OPTIONS_FILE.exists() else "{}")
    return _Options(
        Path(data.get("movie_folder", "/Volumes/Movies-4")),
        Path(data.get("spec_folder", "/Volumes/Dev/Projects/Video Wall/Layouts/")),
        bool(data.get("always_on_top", True)),
        bool(data.get("restore_window_state", False)),
        float(data.get("default_volume", 1.0)),
        bool(data.get("remaining_time", True)),
        int(data.get("jog_interval", 10000)),
        bool(data.get("open_last_on_startup", True)),
        bool(data.get("auto_update_layout", True)),
    )


OPTIONS = _load_options()
"""The global options."""
