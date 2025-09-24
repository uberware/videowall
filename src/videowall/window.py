"""The main window."""

import base64
import json
import logging
import typing
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QCursor
from PySide6.QtWidgets import QMainWindow, QInputDialog

from browser import browse_for_spec
from options import DEMO_SPEC, OPTIONS
from player import act, jog, volume
from video_wall import VideoWall

logger = logging.getLogger("videowall")


class MainWindow(QMainWindow):
    """The main window class."""

    default_layout_file = OPTIONS.spec_folder / "last_layout.json"
    """The default layout spec file with the last played layout."""

    def __init__(self):
        """Initialize the main window."""
        super().__init__()
        if OPTIONS.always_on_top:
            self.setWindowFlags(Qt.WindowStaysOnTopHint)
        # Default layout
        self.open_layout = None
        self.resize(1280, 720)
        self.reset(self.read_spec() if OPTIONS.open_last_on_startup else None)

        # File Menu
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("File")
        new_action = QAction("New", self)
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self.reset)
        file_menu.addAction(new_action)
        default_action = QAction("Demo", self)
        default_action.setShortcut("Ctrl+D")
        default_action.triggered.connect(lambda: self.reset(DEMO_SPEC))
        file_menu.addAction(default_action)
        last_action = QAction("Last", self)
        last_action.setShortcut("Ctrl+Z")
        last_action.triggered.connect(lambda: self.reset(self.read_spec()))
        file_menu.addAction(last_action)
        file_menu.addSeparator()
        load_action = QAction("Open", self)
        load_action.setShortcut("Ctrl+O")
        load_action.triggered.connect(self.load)
        file_menu.addAction(load_action)
        save_action = QAction("Save", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self.save)
        file_menu.addAction(save_action)

        # Playback Menu
        play_menu = menu_bar.addMenu("Playback")
        self.mute_action = QAction("Mute", self)
        self.mute_action.setShortcut("Escape")
        self.mute_action.triggered.connect(self.mute)
        play_menu.addAction(self.mute_action)
        louder_action = QAction("Louder", self)
        louder_action.setShortcut("Up")
        louder_action.triggered.connect(lambda: volume(True))
        play_menu.addAction(louder_action)
        quieter_action = QAction("Quieter", self)
        quieter_action.setShortcut("Down")
        quieter_action.triggered.connect(lambda: volume(False))
        play_menu.addAction(quieter_action)
        play_menu.addSeparator()
        self.play_action = QAction("Pause", self)
        self.play_action.setShortcut("Space")
        self.play_action.triggered.connect(self.play)
        play_menu.addAction(self.play_action)
        jog_back_action = QAction("Jog Back", self)
        jog_back_action.setShortcut(",")
        jog_back_action.triggered.connect(lambda: jog(forward=False))
        play_menu.addAction(jog_back_action)
        jog_forward_action = QAction("Jog Forward", self)
        jog_forward_action.setShortcut(".")
        jog_forward_action.triggered.connect(lambda: jog(forward=True))
        play_menu.addAction(jog_forward_action)
        play_menu.addSeparator()
        prev_action = QAction("Up 1", self)
        prev_action.setShortcut("Left")
        prev_action.triggered.connect(lambda: act(-1))
        play_menu.addAction(prev_action)
        prev_action = QAction("Down 1", self)
        prev_action.setShortcut("Right")
        prev_action.triggered.connect(lambda: act(1))
        play_menu.addAction(prev_action)
        act_action = QAction("Act", self)
        act_action.setShortcut("Return")
        act_action.triggered.connect(lambda: act())
        play_menu.addAction(act_action)

    @property
    def root(self) -> VideoWall:
        """Return the current root VideoWall item."""
        return typing.cast(VideoWall, self.centralWidget())

    def play(self):
        """Toggle playback."""
        if self.play_action.text() == "Pause":
            logger.info("Pause all")
            self.play_action.setText("Play")
            self.root.pause()
            self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
        else:
            logger.info("Play all")
            self.play_action.setText("Pause")
            self.root.play()

    def mute(self):
        """Toggle all volume."""
        if self.mute_action.text() == "Mute":
            logger.info("Mute all")
            self.mute_action.setText("Unmute")
            self.root.mute()
        else:
            logger.info("Unmute all")
            self.mute_action.setText("Mute")
            self.root.unmute()

    def load(self):
        """Open the Load dialog box and load a selected layout."""
        spec_file = browse_for_spec(self)
        if spec_file:
            if OPTIONS.auto_update_layout and self.open_layout:
                self.write_spec(self.open_layout)
            self.reset(self.read_spec(spec_file))

    def save(self):
        """Request a name from the user and save the current layout."""
        text, ok = QInputDialog.getText(self, "Save", "Name of this layout:")
        if ok and text:
            text = text.replace("/", "_").replace("\\", "_")
            out_file = OPTIONS.spec_folder / f"{text}.json"
            self.open_layout = out_file
            self.write_spec(out_file)

    def reset(self, spec: typing.Optional[dict] = None):
        """Discard the current layout and set to a new one.

        Args:
            spec: Optionally provide a layout spec dictionary
        """
        logger.info(f"Loading layout spec: {spec}")
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
        if file:
            self.open_layout = file
        else:
            file = self.default_layout_file
            self.open_layout = None
        if file.exists():
            logger.info(f"Reading layout: {file}")
            data = json.loads(file.read_text())
            if OPTIONS.restore_window_state and "geometry" in data:
                self.restoreGeometry(base64.b64decode(data["geometry"]))
            if OPTIONS.restore_window_state and "state" in data:
                self.restoreState(base64.b64decode(data["state"]))
            if "spec" in data:
                if not self.open_layout and "file" in data:
                    self.open_layout = Path(data["file"])
                return data["spec"]
        return {}

    def write_spec(self, file: Path, include_open_layout: bool = False):
        """Write the current layout to a spec JSON file on disk.

        Args:
            file: A Path object with the destination file name
            include_open_layout: True includes the open layout filename
        """
        logger.info(f"Saving spec: {file}")
        file.parent.mkdir(exist_ok=True)
        data = {
            "geometry": base64.b64encode(self.saveGeometry()).decode(),
            "state": base64.b64encode(self.saveState()).decode(),
            "spec": self.root.spec,
        }
        if include_open_layout and self.open_layout:
            data["file"] = str(self.open_layout)
        file.write_text(json.dumps(data, indent=2))

    def closeEvent(self, event):
        """Override the close event to save the current layout to the default spec file."""
        self.write_spec(self.default_layout_file, include_open_layout=True)
        if OPTIONS.auto_update_layout and self.open_layout:
            self.write_spec(self.open_layout)
        super().closeEvent(event)
