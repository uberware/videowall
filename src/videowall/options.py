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

    always_on_top: bool
    auto_update_layout: bool
    default_volume: float
    jog_interval: int
    movie_folder: Path
    open_last_on_startup: bool
    remaining_time: bool
    restore_window_state: bool
    spec_folder: Path
    pre_roll: int


def _load_options() -> _Options:
    """Loads the options and returns them as an Options object."""
    data = json.loads(OPTIONS_FILE.read_text() if OPTIONS_FILE.exists() else "{}")
    return _Options(
        bool(data.get("always_on_top", True)),
        bool(data.get("auto_update_layout", True)),
        float(data.get("default_volume", 1.0)),
        int(data.get("jog_interval", 10000)),
        Path(data.get("movie_folder", "/Volumes/Movies-4")),
        bool(data.get("open_last_on_startup", True)),
        bool(data.get("remaining_time", True)),
        bool(data.get("restore_window_state", False)),
        Path(data.get("spec_folder", "/Volumes/Dev/Projects/Video Wall/Layouts/")),
        int(data.get("pre_roll", 2000))
    )


OPTIONS = _load_options()
"""The global options."""
