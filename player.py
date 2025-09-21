"""The Player panel and controls."""

import math
import random
import typing
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtCore import QUrl, Qt, QEvent, QSignalBlocker
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import (
    QLabel,
    QVBoxLayout,
    QSlider,
    QWidget,
    QHBoxLayout,
    QToolButton,
    QSplitter,
)

import content
from content import get_files, get_label, get_path
from movie_list import MovieListWidget

# internal data for handling position swapping between two Players current positions in the layout
_transferring: dict = {
    "player": None,
    "all players": [],
    "control": None,
}

# default QSS data
DEFAULT_QSS = (Path(__file__).parent / "style.qss").read_text()


@dataclass(frozen=True)
class PlayerSpec:
    LOOP = 0
    NEXT = 1
    RANDOM = 2

    filename: Path
    volume: float
    speed: float
    mode: int
    control: bool

    @classmethod
    def get(cls, spec: typing.Optional[dict]):
        """Extract spec data from a dictionary"""
        filename = spec.get("filename")
        filename = Path(filename) if filename else None
        volume = spec.get("volume", 0.0)
        speed = spec.get("speed", 1.0)
        mode = {"loop": cls.LOOP, "next": cls.NEXT, "random": cls.RANDOM}.get(spec.get("mode", "loop"), cls.LOOP)
        control = bool(spec.get("control", False))
        return cls(filename, volume, speed, mode, control)


class Player(QWidget):
    """The Player widget class."""

    def __init__(self, spec: typing.Optional[dict] = None):
        """Initialize a new Player object.

        Args:
            spec: a Player spec dictionary or None for a blank player
        """
        super().__init__()
        _transferring["all players"].append(self)

        if spec and not isinstance(spec, dict):
            raise TypeError(f"Not a spec: {spec}")
        if "type" not in spec or spec["type"] != "Player":
            raise TypeError(f"Wrong spec: {spec}")

        spec = PlayerSpec.get(spec)
        print(f"Initializing Player: [{spec.speed}|{spec.volume}|{spec.mode}] {spec.filename}", self)
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

        self.movie_list = MovieListWidget(parent=self)
        self.movie_list.addItems(get_files())
        self.movie_list.currentTextChanged.connect(lambda val: self.set_source(get_path(val)))
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
            font.setPointSize(12)
            font.setBold(True)
            button.setFont(font)
            return button

        self.buttons = QVBoxLayout()
        self.buttons.setSpacing(10)
        self.loop_movie_button = make_button("↺")
        self.loop_movie_button.clicked.connect(lambda: self.set_mode(PlayerSpec.LOOP))
        self.buttons.addWidget(self.loop_movie_button)
        self.next_movie_button = make_button("⇥")
        self.next_movie_button.clicked.connect(lambda: self.set_mode(PlayerSpec.NEXT))
        self.buttons.addWidget(self.next_movie_button)
        self.random_movie_button = make_button("?")
        self.random_movie_button.clicked.connect(lambda: self.set_mode(PlayerSpec.RANDOM))
        self.buttons.addWidget(self.random_movie_button)
        self.buttons.addStretch(1)
        close_button = make_button("⨉")
        close_button.clicked.connect(lambda: self.close())
        self.buttons.addWidget(close_button)
        h_split_button = make_button("|")
        h_split_button.clicked.connect(lambda: self.split_horizontal and self.split_horizontal())
        self.buttons.addWidget(h_split_button)
        v_split_button = make_button("—")
        v_split_button.clicked.connect(lambda: self.split_vertical and self.split_vertical())
        self.buttons.addWidget(v_split_button)
        self.transfer_button = make_button("↯")
        self.transfer_button.clicked.connect(self._process_transfer)
        self.buttons.addWidget(self.transfer_button)
        self.buttons.addStretch(1)
        end_play_button = make_button("⭐︎")
        end_play_button.clicked.connect(self.end_action)
        self.buttons.addWidget(end_play_button)
        self.control_button = make_button("⚐")
        self.control_button.clicked.connect(self._toggle_control)
        self.buttons.addWidget(self.control_button)
        self.main_column.addLayout(self.video_row, stretch=1)

        self.current_time = QLabel("-:--:--", parent=self)
        self.current_time.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont))
        self.total_time = QLabel("-:--:--", parent=self)
        self.total_time.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont))
        self.timeline = QSlider(Qt.Horizontal, parent=self)
        self.timeline.valueChanged.connect(self.player.setPosition)
        self.player.positionChanged.connect(self._update_timeline_position)
        self.bottom_row = QHBoxLayout()
        self.bottom_row.addSpacing(30)
        self.bottom_row.addWidget(self.current_time)
        self.bottom_row.addWidget(self.timeline)
        self.bottom_row.addWidget(self.total_time)
        self.bottom_row.addSpacing(32)

        self.setLayout(self.main_column)
        self._show_interface(False)
        self.unmute_volume = spec.volume
        self.set_mode(spec.mode)
        self.set_speed(spec.speed)
        self.set_volume(self.unmute_volume)
        self.set_source(spec.filename)
        if spec.control:
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
            "mode": self.mode,
            "control": _transferring["control"] == self,
        }

    def skip(self, direction: typing.Optional[int]):
        """Change the playing movie.

        Args:
            direction: -1 to go back 1, 1 to go forward 1, None move randomly
        """
        index = self.movie_list.currentIndex()
        count = self.movie_list.count()
        if direction is None:
            direction = random.randint(1, count - 1)
        print("skip", direction)
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
        print(f"Setting source: {filename}")
        if filename and self.filename != filename:
            self.filename = filename
            self.player.setSource(QUrl.fromLocalFile(filename))
            self.player.play()
            with QSignalBlocker(self.movie_list):
                try:
                    self.movie_list.on_completer_activated(content.get_label(filename))
                except:
                    print(f"warning: source not in movie list folder: {content.MOVIE_FOLDER}")

    def end_action(self):
        """What happens when we hit the end of the movie."""
        if self.mode == PlayerSpec.LOOP:
            print("player looping", self)
            self.player.setPosition(0)
            self.player.play()
        elif self.mode == PlayerSpec.NEXT:
            print("player next movie", self)
            self.skip(1)
        else:
            print("player random movie", self)
            self.skip(None)

    def _update_timeline_position(self, position):
        """Callback to update the timeline slider position during playback."""
        with QSignalBlocker(self.timeline):
            self.timeline.setSliderPosition(position)
            update_time_widget(self.current_time, position)
        if position == self.player.duration():
            self.end_action()

    def _update_timeline_duration(self):
        """Update the UI when the timeline duration is set."""
        duration = self.player.duration()
        self.timeline.setRange(0, duration)
        update_time_widget(self.total_time, duration)

    def _show_interface(self, show: bool):
        """Hide or show widgets as needed."""
        if show:
            self.main_column.setContentsMargins(10, 10, 10, 10)
            self.main_column.setSpacing(10)
            self.movie_list.show()
            self.main_column.insertLayout(0, self.top_row)
            self.video_row.insertLayout(0, self.settings)
            self.video_row.addLayout(self.buttons)
            self.main_column.addLayout(self.bottom_row)
        else:
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
        if _transferring["player"] is None:
            print("starting transfer")
            _transferring["player"] = self
            self.transfer_button.setStyleSheet("background-color: red")
        else:
            if _transferring["player"] != self:
                print(f"swapping {self} with {_transferring['player']}")
                my_splitter, my_index = find_splitter_and_index(self)
                my_sizes = my_splitter.sizes()
                other_splitter, other_index = find_splitter_and_index(_transferring["player"])
                other_sizes = other_splitter.sizes()
                if not my_splitter or not other_splitter:
                    raise RuntimeError(f"Invalid player parents: {my_splitter} {other_splitter}")
                self.setParent(None)
                _transferring["player"].setParent(None)
                my_splitter.insertWidget(my_index, _transferring["player"])
                my_splitter.setSizes(my_sizes)
                other_splitter.insertWidget(other_index, self)
                other_splitter.setSizes(other_sizes)
            _transferring["player"] = None
            print("finished transfer")
        update_colors()

    def _toggle_control(self):
        """Handle the control button clicks."""
        _transferring["control"] = None if _transferring["control"] == self else self
        update_colors()

    def closeEvent(self, event):
        """Override the close event to remove this Player from the transfer list."""
        print("Player Closing", self)
        _transferring["all players"].remove(self)
        super().closeEvent(event)
        self.player = None
        self.deleteLater()

    def eventFilter(self, obj, event):
        """Event filter for the video widget to handle clicks to adjust Panel state."""
        if obj == self.video and event.type() == QEvent.MouseButtonPress:
            if event.button() == Qt.LeftButton:
                # Toggle palette visibility
                if self.movie_list.isVisible():
                    self._show_interface(False)
                else:
                    self._show_interface(True)
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
    transferring_player = _transferring["player"]
    control_player = _transferring["control"]
    for player in _transferring["all players"]:
        if transferring_player is player:
            print("set transferring: ", player)
            player.transfer_button.setStyleSheet("background-color: DarkRed")
        elif transferring_player:
            print("set available: ", player)
            player.transfer_button.setStyleSheet("background-color: DodgerBlue")
        else:
            print("set none: ", player)
            player.transfer_button.setStyleSheet(DEFAULT_QSS)

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
    player = _transferring["control"]
    if player:
        if direction is None:
            player.end_action()
        else:
            player.skip(direction)
