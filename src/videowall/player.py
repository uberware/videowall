"""The Player panel and controls."""

import logging
import math
import random
import typing
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QEvent, QSignalBlocker, Qt, QUrl
from PySide6.QtGui import QFontDatabase
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QSlider,
    QSplitter,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from videowall import content
from videowall.options import DEFAULT_QSS, OPTIONS
from videowall.searchable_list import SearchableListBox

logger = logging.getLogger("videowall")

# internal data
_runtime_data: dict = {
    "source": None,
    "all players": [],
    "control": None,
    "visible": set(),
}


@dataclass(frozen=True)
class PlayerSpec:
    """Player settings class."""

    # constants for the loop mode options
    LOOP = 0
    NEXT = 1
    RANDOM = 2

    # Player data
    filename: Path
    volume: float
    speed: float
    position: int
    mode: int
    control: bool
    history: typing.List[Path]
    at_history: typing.Optional[int]

    @classmethod
    def get(cls, spec: typing.Optional[dict]):
        """Extract spec data from a dictionary."""
        filename = spec.get("filename")
        filename = Path(filename) if filename else None
        volume = spec.get("volume", OPTIONS.default_volume)
        speed = spec.get("speed", 1.0)
        position = max(0, spec.get("position", 0) - OPTIONS.pre_roll)
        mode = {"loop": cls.LOOP, "next": cls.NEXT, "random": cls.RANDOM}.get(spec.get("mode", "loop"), cls.LOOP)
        control = spec.get("control", False)
        history = [Path(x) for x in spec.get("history", [])]
        at_history = spec.get("at_history", None)
        return cls(filename, volume, speed, position, mode, control, history, at_history)


class Player(QWidget):
    """The Player widget class."""

    def __init__(self, spec: typing.Optional[dict] = None):
        """Initialize a new Player object.

        Args:
            spec: a Player spec dictionary or None for a blank player
        """
        super().__init__()
        _runtime_data["all players"].append(self)

        if spec and not isinstance(spec, dict):
            raise TypeError(f"Not a spec: {spec}")
        if "type" not in spec or spec["type"] != "Player":
            raise TypeError(f"Wrong spec: {spec}")

        spec = PlayerSpec.get(spec)
        logger.debug(f"{self} Initializing Player: [{spec.speed}|{spec.volume}|{spec.mode}] {spec.filename}")
        self.split_horizontal = self.split_vertical = None
        self.filename = None
        self.mode = 0

        self.main_column = QVBoxLayout()
        self.main_column.setContentsMargins(0, 0, 0, 0)
        self.main_column.setSpacing(0)
        self.video_row = QHBoxLayout()
        self.video_row.setContentsMargins(0, 0, 0, 0)
        self.video_row.setSpacing(10)
        self.player = QMediaPlayer()
        self.video = QVideoWidget(parent=self)
        self.audio = QAudioOutput()
        self.player.setAudioOutput(self.audio)
        self.player.setVideoOutput(self.video)
        self.player.durationChanged.connect(self._update_timeline_duration)
        self.video_row.addWidget(self.video, stretch=1)

        self.movie_list = SearchableListBox(parent=self)
        self.movie_list.addItems(content.get_files("content"))
        self.movie_list.currentTextChanged.connect(lambda val: self.set_source(content.get_path("content", val)))
        self.top_row = QHBoxLayout()
        self.top_row.addSpacing(30)
        self.top_row.addWidget(self.movie_list)
        self.top_row.addSpacing(32)

        self.settings = QVBoxLayout()
        self.settings.setContentsMargins(0, 0, 0, 0)
        self.settings.setSpacing(10)
        self.speed_slider = QSlider(Qt.Vertical, parent=self)
        self.speed_slider.setRange(0, 200)
        self.speed_slider.valueChanged.connect(lambda val: self.set_speed(val / 100))
        self.speed_slider.mouseDoubleClickEvent = lambda event: self.speed_slider.setSliderPosition(100)
        self.settings.addWidget(self.speed_slider)
        self.volume_slider = QSlider(Qt.Vertical, parent=self)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.valueChanged.connect(lambda val: self.set_volume(slider_to_volume(val)))
        self.volume_slider.mouseDoubleClickEvent = lambda event: self.volume_slider.setSliderPosition(0)
        self.settings.addWidget(self.volume_slider)

        def make_button(label):
            """Make a tool button with the given label."""
            button = QToolButton(parent=self)
            button.setText(label)
            button.setMinimumWidth(26)
            font = button.font()
            font.setPointSize(13)
            button.setFont(font)
            return button

        self.buttons = QVBoxLayout()
        self.buttons.setSpacing(10)
        close_button = make_button("⨉")
        close_button.clicked.connect(lambda: self.close())
        self.buttons.addWidget(close_button)
        h_split_button = make_button("|")
        h_split_button.clicked.connect(lambda: self.split_horizontal and self.split_horizontal())
        self.buttons.addWidget(h_split_button)
        v_split_button = make_button("—")
        v_split_button.clicked.connect(lambda: self.split_vertical and self.split_vertical())
        self.buttons.addWidget(v_split_button)
        self.transfer_button = make_button("➘")
        self.transfer_button.clicked.connect(self._process_transfer)
        self.buttons.addWidget(self.transfer_button)
        self.buttons.addStretch(1)
        self.loop_movie_button = make_button("↻")
        self.loop_movie_button.clicked.connect(lambda: self.set_mode(PlayerSpec.LOOP))
        self.buttons.addWidget(self.loop_movie_button)
        self.next_movie_button = make_button("⇥")
        self.next_movie_button.clicked.connect(lambda: self.set_mode(PlayerSpec.NEXT))
        self.buttons.addWidget(self.next_movie_button)
        self.random_movie_button = make_button("?")
        self.random_movie_button.clicked.connect(lambda: self.set_mode(PlayerSpec.RANDOM))
        self.buttons.addWidget(self.random_movie_button)
        self.buttons.addStretch(1)
        self.main_column.addLayout(self.video_row, stretch=1)

        self.current_time = QLabel("-:--:--", parent=self)
        self.current_time.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont))
        self.total_time = QLabel("-:--:--", parent=self)
        self.total_time.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont))
        self.timeline = QSlider(Qt.Horizontal, parent=self)
        self.timeline.valueChanged.connect(self.player.setPosition)
        self.player.positionChanged.connect(self._update_timeline_position)
        self.bottom_row = QHBoxLayout()
        self.control_button = make_button("⚐")
        self.control_button.clicked.connect(self._toggle_control)
        self.bottom_row.addWidget(self.control_button)
        job_button = make_button("<<")
        job_button.clicked.connect(lambda: self.jog(forward=False))
        self.bottom_row.addWidget(job_button)
        self.bottom_row.addWidget(self.current_time)
        self.bottom_row.addWidget(self.timeline)
        self.bottom_row.addWidget(self.total_time)
        job_button = make_button(">>")
        job_button.clicked.connect(lambda: self.jog(forward=True))
        self.bottom_row.addWidget(job_button)
        end_play_button = make_button("⭐︎")
        end_play_button.clicked.connect(self.end_action)
        self.bottom_row.addWidget(end_play_button)

        self.setLayout(self.main_column)
        self.show_interface(False)
        self.unmute_volume = spec.volume
        self.set_mode(spec.mode)
        self.set_speed(spec.speed)
        self.set_volume(self.unmute_volume)
        self.pending_position = spec.position
        self.history = spec.history
        self.at_history = spec.at_history
        self.set_source(spec.filename)
        if spec.control or not _runtime_data["control"]:
            self._toggle_control()

        # Install event filter on video widget
        self.video.installEventFilter(self)

    @property
    def spec(self) -> dict:
        """Get the current player spec dictionary for this object."""
        return {
            "type": "Player",
            "filename": str(self.filename) or None,
            "speed": self.player.playbackRate(),
            "volume": self.audio.volume() or self.unmute_volume,
            "position": self.player.position(),
            "mode": ["loop", "next", "random"][self.mode],
            "control": _runtime_data["control"] == self,
            "history": [str(it) for it in self.history],
            "at_history": self.at_history,
        }

    def jog(self, forward: bool):
        """Move a little forward or backward in the timeline.

        Args:
            forward: True to jog forward, False to jog backward.
        """
        if forward:
            pos = min(self.player.duration(), self.player.position() + OPTIONS.jog_interval)
        else:
            pos = max(0, self.player.position() - OPTIONS.jog_interval)
        logger.debug(f"{self} Jog to: {pos}")
        self.player.setPosition(pos)

    def skip(self, direction: typing.Optional[int]):
        """Change the playing movie.

        Args:
            direction: -1 to go back 1, 1 to go forward 1, None move randomly
        """
        index = self.movie_list.currentIndex()
        count = self.movie_list.count()
        if direction is None:
            direction = random.randint(1, count - 1)
        logger.debug(f"{self} Skip: {direction}")
        self.movie_list.setCurrentIndex((index + direction + count) % count)

    def play(self):
        """Start playback."""
        self.player.play()

    def pause(self):
        """Pause playback."""
        self.player.pause()

    def set_mode(self, mode):
        """Set the mode."""
        self.mode = mode
        update_colors()

    def set_volume(self, volume: float, set_unmute: bool = True):
        """Set the volume.

        Args:
            volume: float between 0.0 (mute) and 1.0 (full volume)
            set_unmute: True also updates the unmute volume
        """
        with QSignalBlocker(self.volume_slider):
            self.audio.setVolume(volume)
            self.volume_slider.setSliderPosition(volume_to_slider(volume))
            if set_unmute:
                self.unmute_volume = volume

    def mute(self):
        """Mute the volume, but remember last volume to unmute back to."""
        self.set_volume(0.0, set_unmute=False)

    def unmute(self):
        """Unmute the volume back to the last remembered volume."""
        self.set_volume(self.unmute_volume, set_unmute=False)

    def nudge_volume_slider(self, louder: bool):
        """Bump the volume slider.

        Args:
            louder: True to bump the volume slider up instead of down
        """
        if louder:
            pos = min(self.volume_slider.maximum(), self.volume_slider.sliderPosition() + 5)
        else:
            pos = max(0, self.volume_slider.sliderPosition() - 5)
        logger.info(f"{self} Nudge volume slider to: {pos}")
        self.volume_slider.setSliderPosition(pos)

    def set_speed(self, speed: float):
        """Set the playback speed.

        Args:
            speed: float between 0.1 and 2.0 multiplier on playback frame rate
        """
        with QSignalBlocker(self.speed_slider):
            self.player.setPlaybackRate(speed)
            self.speed_slider.setSliderPosition(int(speed * 100))

    def set_source(self, filename: typing.Optional[Path]):
        """Set the path to the movie to play."""
        logger.info(f"{self} Setting source: {filename}")
        if filename and self.filename != filename:
            self.filename = filename
            if self.at_history is None and (not self.history or self.history[-1] != filename):
                logger.info(f"{self} Adding history: {filename}")
                self.history.append(filename)
            self.player.setSource(QUrl.fromLocalFile(filename))
            self.player.play()
            with QSignalBlocker(self.movie_list):
                try:
                    self.movie_list.on_completer_activated(content.get_label(OPTIONS.movie_folder, filename))
                except ValueError:
                    logger.warning(f"source not in movie list folder: {OPTIONS.movie_folder}")

    def end_action(self):
        """What happens when we hit the end of the movie."""
        if self.mode == PlayerSpec.LOOP:
            logger.info(f"{self} Looping")
            self.player.setPosition(0)
            self.player.play()
        elif self.at_history is not None:
            self.move_in_history(True)
        elif self.mode == PlayerSpec.NEXT:
            logger.info(f"{self} Next movie")
            self.skip(1)
        else:
            logger.info(f"{self} Random movie")
            self.skip(None)

    def move_in_history(self, forward: bool):
        """Move through the history of this player."""
        if forward:
            logger.info(f"{self} Moving forward in history")
            if self.at_history is not None and self.at_history < len(self.history) - 2:
                self.at_history += 1
            else:
                self.at_history = None
        else:
            logger.info(f"{self} Moving backward in history")
            if self.at_history is None:
                self.at_history = len(self.history) - 2
            else:
                self.at_history = max(0, self.at_history - 1)
        index = len(self.history) - 1 if self.at_history is None else self.at_history
        self.set_source(self.history[index])

    def _update_timeline_position(self, position):
        """Callback to update the timeline slider position during playback."""
        if self.pending_position:
            logger.debug(f"{self} Pending timeline position: {self.pending_position}")
            position = self.pending_position
            self.pending_position = None
            self.player.setPosition(position)
        else:
            with QSignalBlocker(self.timeline):
                self.timeline.setSliderPosition(position)
                update_time_widget(self.current_time, position)
                if OPTIONS.remaining_time:
                    update_time_widget(self.total_time, self.player.duration() - position)
            if position == self.player.duration():
                self.end_action()
            if not _runtime_data["visible"]:
                self._set_cursor(Qt.CursorShape.BlankCursor)

    def _set_cursor(self, shape: Qt.CursorShape):
        """Set the cursor."""
        parent = self.parent()
        while parent.parent():
            parent = parent.parent()
        parent.setCursor(shape)

    def _update_timeline_duration(self):
        """Update the UI when the timeline duration is set."""
        duration = self.player.duration()
        with QSignalBlocker(self.timeline):
            self.timeline.setRange(0, duration)
            update_time_widget(self.total_time, duration)

    def show_interface(self, show: typing.Optional[bool] = None):
        """Hide or show widgets as needed.

        Args:
            show: True shows, False hides, None toggles
        """
        if show is None:
            show = not self.movie_list.isVisible()
        if show:
            _runtime_data["visible"].add(self)
            self.main_column.setContentsMargins(10, 10, 10, 10)
            self.main_column.setSpacing(10)
            self.movie_list.show()
            self.main_column.insertLayout(0, self.top_row)
            self.video_row.insertLayout(0, self.settings)
            self.video_row.addLayout(self.buttons)
            self.main_column.addLayout(self.bottom_row)
            self._set_cursor(Qt.CursorShape.ArrowCursor)
        else:
            _runtime_data["visible"].discard(self)
            self.main_column.setContentsMargins(0, 0, 0, 0)
            self.main_column.setSpacing(0)
            self.movie_list.clearFocus()
            self.movie_list.hide()
            if self.main_column.count() > 1:
                self.main_column.removeItem(self.main_column.itemAt(0))
            if self.video_row.count() > 1:
                self.video_row.removeItem(self.video_row.itemAt(0))
            if self.video_row.count() > 1:
                self.video_row.removeItem(self.video_row.itemAt(1))
            if self.main_column.count() > 1:
                self.main_column.removeItem(self.main_column.itemAt(1))
        self.layout()

    def _process_transfer(self):
        """Handle the transfer button clicks."""
        if _runtime_data["source"] is None:
            logger.debug(f"{self} Starting transfer")
            _runtime_data["source"] = self
            self.transfer_button.setStyleSheet("background-color: red")
        else:
            if _runtime_data["source"] != self:
                logger.debug(f"{self} Swapping with: {_runtime_data['source']}")
                my_splitter, my_index = find_splitter_and_index(self)
                my_sizes = my_splitter.sizes()
                other_splitter, other_index = find_splitter_and_index(_runtime_data["source"])
                other_sizes = other_splitter.sizes()
                if not my_splitter or not other_splitter:
                    raise RuntimeError(f"Invalid player parents: {my_splitter} {other_splitter}")
                self.setParent(None)
                _runtime_data["source"].setParent(None)
                my_splitter.insertWidget(my_index, _runtime_data["source"])
                my_splitter.setSizes(my_sizes)
                other_splitter.insertWidget(other_index, self)
                other_splitter.setSizes(other_sizes)
            _runtime_data["source"] = None
            logger.debug(f"{self} Finished transfer")
        update_colors()

    def _toggle_control(self):
        """Handle the control button clicks."""
        _runtime_data["control"] = None if _runtime_data["control"] == self else self
        update_colors()

    def closeEvent(self, event):
        """Override the close event to remove this Player from the transfer list."""
        logger.debug(f"{self} Closing")
        _runtime_data["all players"].remove(self)
        if _runtime_data["control"] == self:
            _runtime_data["control"] = None
        super().closeEvent(event)
        self.player = None
        self.deleteLater()

    def eventFilter(self, obj, event):
        """Event filter for the video widget to handle clicks to adjust Panel state."""
        if obj == self.video and event.type() == QEvent.MouseButtonPress:
            if event.button() == Qt.LeftButton:
                # Toggle palette visibility
                self.show_interface()
            return True  # consume the click
        return super().eventFilter(obj, event)


def find_splitter_and_index(widget: QWidget) -> typing.Tuple[typing.Optional[QSplitter], int]:
    """Find the QSplitter parent and index for the given Player widget.

    Returns:
        Tuple of the QSplitter and the index if found, or (None, -1) if not found
    """
    parent = widget.parent()
    while parent is not None and not isinstance(parent, QSplitter):
        parent = parent.parent()
    if isinstance(parent, QSplitter):
        return parent, parent.indexOf(widget)
    return None, -1


def update_time_widget(widget, duration):
    """Update the display of a time in ms to a human-readable time in the given widget."""
    s = duration // 1000
    m = s // 60
    h = m // 60
    m = m % 60
    s = s % 60
    widget.setText(f"{h}:{m:02d}:{s:02d}")


def update_colors():
    """Update the transfer button colors."""
    transferring_player = _runtime_data["source"]
    control_player = _runtime_data["control"]
    for player in _runtime_data["all players"]:
        if transferring_player is player:
            button_qss = "\nQToolButton{ background: DarkRed; }\n"
        elif transferring_player:
            button_qss = "\nQToolButton{ background: DodgerBlue; }\n"
        else:
            button_qss = ""
        player.transfer_button.setStyleSheet(DEFAULT_QSS + button_qss)

        def status_color(check):
            return "background-color: Chocolate" if check else DEFAULT_QSS

        player.loop_movie_button.setStyleSheet(status_color(player.mode == PlayerSpec.LOOP))
        player.next_movie_button.setStyleSheet(status_color(player.mode == PlayerSpec.NEXT))
        player.random_movie_button.setStyleSheet(status_color(player.mode == PlayerSpec.RANDOM))

        player.control_button.setStyleSheet(status_color(player == control_player))


SLIDER_MIN = 0
SLIDER_MAX = 100
VOLUME_MIN = 0.01
VOLUME_MAX = 1.0


def slider_to_volume(slider_value: int) -> float:
    """Map slider 0–100 to volume 0.0–1.0 logarithmically.

    Slider 0 is 0.0 exactly (mute).
    Slider 1–slider_max maps log between vol_min–vol_max.
    """
    if slider_value <= SLIDER_MIN:
        return 0.0  # mute exactly

    # Normalise slider range from 1–max
    t = (slider_value - 1) / (SLIDER_MAX - 1)

    log_min = math.log(VOLUME_MIN)
    log_max = math.log(VOLUME_MAX)
    log_val = log_min + t * (log_max - log_min)
    return math.exp(log_val)


def volume_to_slider(volume: float) -> int:
    """Inverse mapping from volume float back to slider position."""
    if volume <= 0.0:
        return SLIDER_MIN

    log_min = math.log(VOLUME_MIN)
    log_max = math.log(VOLUME_MAX)
    t = (math.log(volume) - log_min) / (log_max - log_min)
    return int(round(1 + t * (SLIDER_MAX - 1)))


def act(direction: typing.Optional[int] = None):
    """Tell the Player with control to run the end_action.

    Args:
        direction: -1 to go back 1, 1 to go forward 1, None to do end-of-movie action
    """
    player = _runtime_data["control"]
    if player:
        if direction is None:
            player.end_action()
        else:
            player.skip(direction)


def jog(forward: bool):
    """Tell the Player with control to jog.

    Args:
        forward: True to jog forward, Back go jog backward
    """
    player = _runtime_data["control"]
    if player:
        player.jog(forward)


def volume(louder: bool):
    """Tell the Player with control to change volume.

    Args:
        louder: True to increase the volume instead of decrease
    """
    player = _runtime_data["control"]
    if player:
        player.nudge_volume_slider(louder)


def toggle():
    """Toggle the interface for the Player with control."""
    player = _runtime_data["control"]
    if player:
        logger.info("Toggle active player")
        player.show_interface()


def history(forward: bool = True):
    """Move through the history of the Player with control.

    Args:
        forward: True to move forward in history, False to move backward.
    """
    player = _runtime_data["control"]
    if player:
        player.move_in_history(forward)
