"""Shared fixtures and helpers for the videowall test suite."""

import dataclasses
import os

# Qt needs an offscreen backend before PySide6 is imported, or the suite opens real windows.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QKeyEvent, QMouseEvent
from PySide6.QtWidgets import QApplication

from videowall import content, player, video_wall, window
from videowall.options import OPTIONS
from videowall.video_wall import each_item_in

MOVIES = ["Alpha Movie.mp4", "Beta Movie.mp4", "Gamma Movie.mp4"]
"""The movie list served to every test in place of a real folder scan."""


@pytest.fixture(scope="session")
def qapp():
    """Provide the single QApplication instance shared by the whole session."""
    return QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def test_options(tmp_path, monkeypatch):
    """Replace the OPTIONS singleton with fixed settings in every module holding a reference.

    Without this the tests would read ``~/videowall_settings.json`` and behave differently
    from one machine to the next, and would load and rewrite the real saved layouts.
    """
    options = dataclasses.replace(
        OPTIONS,
        always_on_top=False,
        auto_update_layout=False,
        default_volume=1.0,
        hide_mouse_delay=3.0,
        jog_interval=10000,
        layout_folder=tmp_path / "layouts",
        lock_titlebar=False,
        movie_folder=tmp_path / "movies",
        open_last_on_startup=False,
        play_audio=True,
        pre_roll=2000,
        remaining_time=True,
        restore_window_state=False,
        sparse_spec=True,
        splitter_handle_width=5,
    )
    for module in (content, player, video_wall, window):
        monkeypatch.setattr(module, "OPTIONS", options)
    monkeypatch.setattr(window.MainWindow, "default_layout_file", options.layout_folder / "last_layout.json")
    return options


@pytest.fixture(autouse=True)
def stub_content(monkeypatch):
    """Serve a fixed movie list so no test triggers a real folder scan.

    ``get_path`` returns None on purpose: the players then hold no media, which keeps
    QMediaPlayer inert while leaving every widget and signal in place.
    """
    monkeypatch.setattr(content, "get_files", lambda kind: list(MOVIES))
    monkeypatch.setattr(content, "get_path", lambda kind, label: None)
    monkeypatch.setattr(content, "get_label", lambda root, filename: str(filename))


@pytest.fixture(autouse=True)
def clean_runtime_data():
    """Reset the module level player registry so state cannot leak between tests."""
    yield
    player._runtime_data["all players"].clear()
    player._runtime_data["visible"].clear()
    player._runtime_data["control"] = None
    player._runtime_data["source"] = None
    player._runtime_data["locked"] = False


@pytest.fixture
def main_window(qapp):
    """Create a shown MainWindow holding a single empty player."""
    win = window.MainWindow()
    win.resize(1280, 720)
    win.show()
    qapp.processEvents()
    yield win
    # Close the window before its players: MainWindow.closeEvent serialises the layout,
    # which walks the live players, so tearing them down first would read dead widgets.
    win.close()
    for item in list(player._runtime_data["all players"]):
        item.close()
    qapp.processEvents()


@pytest.fixture
def single_player(main_window, qapp):
    """Return the only player of a fresh window, with its interface shown."""
    item = players_of(main_window)[0]
    item.show_interface(True)
    qapp.processEvents()
    return item


@pytest.fixture
def two_players(main_window, qapp):
    """Return two side by side players, both with their interface shown."""
    main_window.reset(
        {
            "type": "VideoWall",
            "orientation": "horizontal",
            "items": [{"type": "Player"}, {"type": "Player"}],
            "sizes": [640, 640],
        }
    )
    qapp.processEvents()
    items = players_of(main_window)
    for item in items:
        item.show_interface(True)
    qapp.processEvents()
    return items


@pytest.fixture
def transport_calls(monkeypatch):
    """Record the play/pause commands every Player receives.

    QMediaPlayer stays in StoppedState without real media loaded, so playbackState cannot
    say whether a layout was started or paused. The transport commands issued to each
    player are the signal available to us.
    """
    calls = []
    for name in ("play", "pause"):
        original = getattr(player.Player, name)

        def record(self, _name=name, _original=original):
            calls.append((_name, self))
            return _original(self)

        monkeypatch.setattr(player.Player, name, record)
    return calls


@pytest.fixture
def shortcut_fired(main_window):
    """Record each time the Space play/pause shortcut reaches the menu action."""
    seen = []
    main_window.play_action.triggered.connect(lambda: seen.append("play"))
    return seen


def players_of(main_window):
    """Return the Player widgets of a window in layout order."""
    return list(each_item_in(main_window.root))


def send_key(main_window, key, text=""):
    """Deliver a key press to the focus widget, falling back to the window.

    ``QApplication.sendEvent`` runs the same shortcut matching that real key input does,
    so a menu shortcut either fires or is swallowed here exactly as it would in the app.

    Returns:
        The widget the key was delivered to.
    """
    target = QApplication.focusWidget() or main_window
    QApplication.sendEvent(target, QKeyEvent(QEvent.KeyPress, key, Qt.NoModifier, text))
    QApplication.processEvents()
    return target


def click_video(item):
    """Send a left button press to a player's video area."""
    position = QPointF(5, 5)
    event = QMouseEvent(QEvent.MouseButtonPress, position, position, Qt.LeftButton, Qt.LeftButton, Qt.NoModifier)
    QApplication.sendEvent(item.video, event)
    QApplication.processEvents()


def focus_filter(item):
    """Give the movie filter of a player keyboard focus, as clicking into it would."""
    item.movie_filter.setFocus(Qt.MouseFocusReason)
    QApplication.processEvents()
