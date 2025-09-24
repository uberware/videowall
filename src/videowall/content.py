"""Access to the content."""

import logging
import typing
from pathlib import Path

from options import OPTIONS

logger = logging.getLogger("videowall")


# Map a layout name to the Path object with the full file path
_files = {}


def _search():
    """Populate the layout file map."""
    movie_folder = OPTIONS.movie_folder
    logger.info(f"Populating file list: {movie_folder}")

    for ext in ["mp4", "mov", "avi", "mkv", "wmv"]:
        for file in movie_folder.rglob(f"*.{ext}"):
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
    return f"{filepath.parent.relative_to(OPTIONS.movie_folder)}/{filepath.stem}"
