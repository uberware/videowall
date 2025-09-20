"""Access to the content."""

import typing
from pathlib import Path

# Map a layout name to the Path object with the full file path
_files = {}

# TODO: make this configurable
MOVIE_FOLDER = Path("/Volumes/x/Good")


def _search():
    """Populate the layout file map."""
    for ext in ["mp4", "mov", "avi"]:
        for file in MOVIE_FOLDER.rglob(f"*.{ext}"):
            if not file.name.startswith("."):
                _files[get_label(file)] = file


def get_files() -> typing.List[str]:
    """Get a sorted list with the names of all files available."""
    if not _files:
        _search()
    return sorted(_files.keys())


def get_path(name: str) -> Path:
    """Get the full path to a layout file given a name."""
    if name in _files:
        return _files[name]


def get_label(filepath: Path) -> str:
    """Get the relative label for a path based on the search folder."""
    return f"{filepath.parent.relative_to(MOVIE_FOLDER)}/{filepath.stem}"
