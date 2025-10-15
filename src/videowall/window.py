"""The main window."""

import base64
import json
import logging
import typing
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QCursor, QKeySequence
from PySide6.QtWidgets import QInputDialog, QMainWindow

from videowall import player
from videowall.browser import browse_for_spec
from videowall.options import DEMO_SPEC, OPTIONS
from videowall.video_wall import VideoWall

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
        layout_menu = menu_bar.addMenu("Layout")
        new_action = QAction("New", self)
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self.reset)
        layout_menu.addAction(new_action)
        default_action = QAction("Demo", self)
        default_action.setShortcut("Ctrl+D")
        default_action.triggered.connect(lambda: self.reset(DEMO_SPEC, clear_open_layout=True))
        layout_menu.addAction(default_action)
        last_action = QAction("Last", self)
        last_action.setShortcut("Ctrl+Z")
        last_action.triggered.connect(lambda: self.reset(self.read_spec()))
        layout_menu.addAction(last_action)
        layout_menu.addSeparator()
        load_action = QAction("Open", self)
        load_action.setShortcut("Ctrl+O")
        load_action.triggered.connect(self.load)
        layout_menu.addAction(load_action)
        save_action = QAction("Save", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self.save)
        layout_menu.addAction(save_action)

        # Playback Menu
        play_menu = menu_bar.addMenu("Playback")
        toggle_action = QAction("Toggle UI", self)
        toggle_action.setShortcut("Tab")
        toggle_action.triggered.connect(lambda: player.toggle())
        play_menu.addAction(toggle_action)
        full_screen_action = QAction("Full Screen", self)
        full_screen_action.setShortcut("F")
        full_screen_action.triggered.connect(
            lambda: self.showNormal() if self.isFullScreen() else self.showFullScreen()
        )
        play_menu.addAction(full_screen_action)
        play_menu.addSeparator()
        self.mute_action = QAction("Mute", self)
        self.mute_action.setShortcut("Escape")
        self.mute_action.triggered.connect(self.mute)
        play_menu.addAction(self.mute_action)
        louder_action = QAction("Louder", self)
        louder_action.setShortcut("Up")
        louder_action.triggered.connect(lambda: player.volume(True))
        play_menu.addAction(louder_action)
        quieter_action = QAction("Quieter", self)
        quieter_action.setShortcut("Down")
        quieter_action.triggered.connect(lambda: player.volume(False))
        play_menu.addAction(quieter_action)
        play_menu.addSeparator()
        self.play_action = QAction("Pause", self)
        self.play_action.setShortcut("Space")
        self.play_action.triggered.connect(self.play)
        play_menu.addAction(self.play_action)
        jog_back_action = QAction("Jog Back", self)
        jog_back_action.setShortcut(",")
        jog_back_action.triggered.connect(lambda: player.jog(forward=False))
        play_menu.addAction(jog_back_action)
        jog_forward_action = QAction("Jog Forward", self)
        jog_forward_action.setShortcut(".")
        jog_forward_action.triggered.connect(lambda: player.jog(forward=True))
        play_menu.addAction(jog_forward_action)
        play_menu.addSeparator()
        back_action = QAction("Back", self)
        back_action.setShortcut(QKeySequence.StandardKey.MoveToPreviousPage)
        back_action.triggered.connect(lambda: player.history(False))
        play_menu.addAction(back_action)
        forward_action = QAction("Forward", self)
        forward_action.setShortcut(QKeySequence.StandardKey.MoveToNextPage)
        forward_action.triggered.connect(lambda: player.history(True))
        play_menu.addAction(forward_action)
        prev_action = QAction("Up 1", self)
        prev_action.setShortcut("Left")
        prev_action.triggered.connect(lambda: player.act(-1))
        play_menu.addAction(prev_action)
        prev_action = QAction("Down 1", self)
        prev_action.setShortcut("Right")
        prev_action.triggered.connect(lambda: player.act(1))
        play_menu.addAction(prev_action)
        act_action = QAction("Act", self)
        act_action.setShortcut("Return")
        act_action.triggered.connect(lambda: player.act())
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

    def reset(self, spec: typing.Optional[dict] = None, clear_open_layout: bool = False):
        """Discard the current layout and set to a new one.

        Args:
            spec: Optionally provide a layout spec dictionary
            clear_open_layout: True will also clear the open_layout
        """
        logger.info(f"Loading layout spec: {spec}")
        old = self.root
        self.setCentralWidget(VideoWall(spec or {}))
        if old:
            old.close()
        if clear_open_layout:
            self.open_layout = None

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
