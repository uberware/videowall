"""Access to the content."""

import logging
import typing
from pathlib import Path

from PySide6.QtCore import QObject, QThread, Signal
from PySide6.QtWidgets import QDialog, QLabel, QProgressBar, QVBoxLayout

from .options import OPTIONS

logger = logging.getLogger("videowall")

# Map a layout name to the Path object with the full file path
_files = {}


class MovieScanner(QObject):
    """Thread object to scan for movie files in the background."""

    done = Signal()
    """Signal that the scan has completed."""

    def __init__(self, folder: Path):
        """Initialize a new MovieScanner object."""
        super().__init__()
        self.folder = folder
        self.stop = False

    def run(self):
        """Run the scan."""
        for ext in ["mp4", "mov", "avi", "mkv", "wmv"]:
            for file in self.folder.rglob(f"*.{ext}"):
                if self.stop:
                    break
                if not file.name.startswith("."):
                    logger.debug(file)
                    _files[get_label(file)] = file
        self.done.emit()


class ScanDialog(QDialog):
    """A progress window to show while the movie folder is scanned."""

    def __init__(self, folder: Path):
        """Initialize a new ScanDialog object."""
        super().__init__()
        self.setWindowTitle("Scanning for movies…")
        self.setMinimumWidth(300)
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel(str(folder)))
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)  # indeterminate
        lay.addWidget(self.progress)
        self.movies = []

        self.thread = QThread()
        self.worker = MovieScanner(folder)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.done.connect(self.finish)
        self.thread.start()

    def finish(self):
        """Callback when the scan thread completes."""
        logger.debug("Scan completed")
        self.thread.quit()
        self.thread.wait()
        self.accept()


def _search():
    """Populate the layout file map."""
    movie_folder = OPTIONS.movie_folder
    logger.info(f"Populating file list: {movie_folder}")
    dlg = ScanDialog(movie_folder)
    dlg.exec()


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
