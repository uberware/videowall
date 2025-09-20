"""The main window."""

import base64
import json
import typing
from pathlib import Path

from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMainWindow, QInputDialog

from video_wall import VideoWall

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


class MainWindow(QMainWindow):
    """The main window class."""

    spec_folder = Path("/Volumes/x/Videowalls")
    """Layout spec files are saved in this folder."""
    spec_file = spec_folder / "spec.json"
    """The default layout spec file with the last played layout."""

    def __init__(self):
        """Initialize the main window."""
        super().__init__()
        # Default layout
        self.resize(1280, 720)
        self.reset()
        # Menu
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("File")
        self.play_action = QAction("Pause", self)
        self.play_action.setShortcut("Space")
        self.play_action.triggered.connect(self.play)
        file_menu.addAction(self.play_action)
        self.mute_action = QAction("Mute", self)
        self.mute_action.setShortcut("Escape")
        self.mute_action.triggered.connect(self.mute)
        file_menu.addAction(self.mute_action)
        file_menu.addSeparator()
        new_action = QAction("New", self)
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self.reset)
        file_menu.addAction(new_action)
        default_action = QAction("Default", self)
        default_action.setShortcut("Ctrl+D")
        default_action.triggered.connect(lambda: self.reset(DEFAULT_SPEC))
        file_menu.addAction(default_action)
        last_action = QAction("Last", self)
        last_action.setShortcut("Ctrl+Z")
        last_action.triggered.connect(lambda: self.reset(self.read_spec()))
        file_menu.addAction(last_action)
        file_menu.addSeparator()
        load_action = QAction("Load", self)
        load_action.setShortcut("Ctrl+L")
        load_action.triggered.connect(self.load)
        file_menu.addAction(load_action)
        save_action = QAction("Save", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self.save)
        file_menu.addAction(save_action)

    @property
    def root(self) -> VideoWall:
        return typing.cast(VideoWall, self.centralWidget())

    def play(self):
        """Toggle playback."""
        if self.play_action.text() == "Pause":
            print("pause")
            self.play_action.setText("Play")
            self.root.pause()
        else:
            print("play")
            self.play_action.setText("Pause")
            self.root.play()

    def mute(self):
        """Toggle all volume."""
        if self.mute_action.text() == "Mute":
            print("mute")
            self.mute_action.setText("Unmute")
            self.root.mute()
        else:
            print("unmute")
            self.mute_action.setText("Mute")
            self.root.unmute()

    def load(self):
        """Open the Load dialog box and load a selected layout."""
        items = {it.stem: it for it in self.spec_folder.glob("*.json") if not it.name.startswith(".")}
        text, ok = QInputDialog.getItem(self, "Load", "Pick a layout to load", items)
        if ok and text:
            self.reset(self.read_spec(items[text]))

    def save(self):
        """Request a name from the user and save the current layout."""
        text, ok = QInputDialog.getText(self, "Save", "Name of this layout:")
        if ok and text:
            out_file = self.spec_folder / f"{text}.json"
            self.write_spec(out_file)

    def reset(self, spec: typing.Optional[dict] = None):
        """Discard the current layout and set to a new one.

        Args:
            spec: Optionally provide a layout spec dictionary
        """
        print("reset", spec)
        old = self.root
        self.setCentralWidget(VideoWall(spec or {}))
        if old:
            old.close()

    def read_spec(self, file: typing.Optional[Path] = None) -> dict:
        """Read a spec file and restore the window state (if available).

        Args:
            file: the Path object with the file to read. None will use the default spec file.

        Returns:
            The loaded spec data dictionary or an empty dictionary
        """
        if not file:
            file = self.spec_file
        if file.exists():
            data = json.loads(file.read_text())
            # if "geometry" in data:
            #     self.restoreGeometry(base64.b64decode(data["geometry"]))
            # if "state" in data:
            #     self.restoreState(base64.b64decode(data["state"]))
            if "spec" in data:
                return data["spec"]
        return {}

    def write_spec(self, file: Path):
        """Write the current layout to a spec JSON file on disk.

        Args:
            file: A Path object with the destination file name
        """
        file.parent.mkdir(exist_ok=True)
        data = {
            "geometry": base64.b64encode(self.saveGeometry()).decode(),
            "state": base64.b64encode(self.saveState()).decode(),
            "spec": self.root.spec,
        }
        file.write_text(json.dumps(data, indent=2))

    def closeEvent(self, event):
        """Override the close event to save the current layout to the default spec file."""
        self.write_spec(self.spec_file)
        super().closeEvent(event)
