"""Access to the content."""

import logging
import typing
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QObject, QThread, Signal
from PySide6.QtWidgets import QDialog, QLabel, QProgressBar, QVBoxLayout

from videowall.options import OPTIONS

logger = logging.getLogger("videowall")

# Data storage for content files
_files = {}


@dataclass(frozen=True)
class _FolderInfo:
    """One search entry."""

    file_type: str
    """The type of files, 'content' or 'layout'."""
    folder: Path
    """The path to search."""
    ext_list: typing.List[str]
    """A list of extensions, including the period."""


class FolderScanner(QObject):
    """Thread object to scan for movie files in the background."""

    folder_change = Signal(Path)
    """Signal that the folder being scanned has changed."""
    done = Signal()
    """Signal that the scan has completed."""

    def __init__(self, scan_list: typing.List[_FolderInfo]):
        """Initialize a new MovieScanner object."""
        super().__init__()
        self.scan_list = scan_list
        self.stop = False

    def run(self):
        """Run the scan."""
        for scan_info in self.scan_list:
            logger.info(f"{scan_info.file_type}: {scan_info.folder}")
            self.folder_change.emit(scan_info.folder)
            for file in scan_info.folder.rglob("*"):
                if self.stop:
                    break
                if not file.name.startswith(".") and file.suffix in scan_info.ext_list:
                    logger.debug(file)
                    _files[scan_info.file_type][get_label(scan_info.folder, file)] = file
        self.done.emit()


class ScanDialog(QDialog):
    """A progress window to show while the movie folder is scanned."""

    def __init__(self):
        """Initialize a new ScanDialog object."""
        super().__init__()
        self.setWindowTitle("Scanning…")
        self.setMinimumWidth(300)
        lay = QVBoxLayout(self)
        self.folder_label = QLabel()
        lay.addWidget(self.folder_label)
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)  # indeterminate
        lay.addWidget(self.progress)
        self.movies = []

        self.thread = QThread()
        scan_list = [
            _FolderInfo("content", OPTIONS.movie_folder, [".mp4", ".mov", ".avi", ".mkv", ".wmv"]),
            _FolderInfo("layout", OPTIONS.spec_folder, [".json"]),
        ]
        self.worker = FolderScanner(scan_list)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.folder_change.connect(self.folder_changed)
        self.worker.done.connect(self.finish)
        self.thread.start()

    def folder_changed(self, folder: Path):
        """Callback when the folder changes."""
        self.folder_label.setText(str(folder))

    def finish(self):
        """Callback when the scan thread completes."""
        logger.debug("Scan completed")
        self.thread.quit()
        self.thread.wait()
        self.accept()


def _search():
    """Populate the layout file map."""
    logger.info("Populating file lists")
    _files["content"] = {}
    _files["layout"] = {}
    dlg = ScanDialog()
    dlg.exec()


def get_files(file_type: str) -> typing.List[str]:
    """Get a sorted list with the names of all files available."""
    if not _files:
        _search()
    return sorted(_files[file_type].keys(), key=_sort_key)


def get_path(file_type: str, name: str) -> Path:
    """Get the full path to a layout file given a name."""
    return _files.get(file_type, {}).get(name)


def get_label(folder: Path, filepath: Path) -> str:
    """Get the relative label for a path based on the search folder."""
    folder = str(filepath.parent.relative_to(folder))
    if folder == ".":
        return filepath.stem
    else:
        return f"{folder}/{filepath.stem}"


def _sort_key(filepath: str) -> typing.Tuple[str, str]:
    """Custom sort by folder and filename."""
    parts = filepath.rsplit("/", 1)
    if len(parts) == 2:
        return parts[0], parts[1]
    else:
        return "", filepath
