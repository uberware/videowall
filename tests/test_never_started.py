"""A movie that was told to play and never did is told again.

Deferring the source change takes the wall's commands out of the middle of Qt's own end of
stream handling, which is where the race was found, but nothing in the wall would notice if
a movie still failed to start. The evidence of that failure is precise: a loaded, healthy
movie of known length, parked at position 0, stopped, with no error. A player left like
that is given one more instruction to play, once per movie, and the log says so. A second
failure is left alone rather than retried forever, where the stall watcher reports it.
"""

import pytest
from PySide6.QtCore import QUrl
from PySide6.QtMultimedia import QMediaPlayer

from videowall import player as player_module

MOVIE = "/movies/something.mp4"
"""The movie a headless player pretends to hold."""


@pytest.fixture
def backend(single_player, monkeypatch):
    """Drive what the backend reports and record the transport commands it is given."""
    harness = {
        "calls": [],
        "state": QMediaPlayer.PlaybackState.StoppedState,
        "position": 0,
        "status": QMediaPlayer.MediaStatus.LoadedMedia,
    }
    media = type(single_player.player)
    monkeypatch.setattr(media, "playbackState", lambda self: harness["state"])
    monkeypatch.setattr(media, "position", lambda self: harness["position"])
    monkeypatch.setattr(media, "mediaStatus", lambda self: harness["status"])
    for name in ("play", "pause"):
        monkeypatch.setattr(media, name, lambda self, _name=name: harness["calls"].append(_name))
    return harness


def test_a_movie_that_never_started_is_told_to_play_again(single_player, backend):
    """The whole point: a loaded movie stopped at its start is not a movie anyone chose."""
    single_player.wants_playing = True

    single_player._check_started(single_player.player.source())

    assert backend["calls"] == ["play"]


def test_a_movie_that_is_playing_is_left_alone(single_player, backend):
    """The check runs after every source change, so the ordinary case must be silent."""
    single_player.wants_playing = True
    backend["state"] = QMediaPlayer.PlaybackState.PlayingState

    single_player._check_started(single_player.player.source())

    assert backend["calls"] == []


def test_a_movie_stopped_partway_through_is_left_alone(single_player, backend):
    """Only a movie that never started is answered here; one that stopped later is not."""
    single_player.wants_playing = True
    backend["position"] = 60000

    single_player._check_started(single_player.player.source())

    assert backend["calls"] == []


def test_a_paused_wall_is_not_started_again(single_player, backend):
    """Pausing is the user's instruction, and no safety net may talk over it."""
    single_player.pause()
    backend["calls"].clear()

    single_player._check_started(single_player.player.source())

    assert backend["calls"] == []


def test_a_player_that_moved_on_is_not_started_again(single_player, backend):
    """The check belongs to the movie that was set, not to whatever is loaded when it runs."""
    single_player.wants_playing = True

    single_player._check_started(QUrl.fromLocalFile("/movies/a different movie.mp4"))

    assert backend["calls"] == []


def test_setting_a_source_schedules_the_check(single_player, backend, qapp, monkeypatch):
    """The net is only worth having if every movie is actually watched onto the screen."""
    monkeypatch.setattr(player_module, "START_TIMEOUT", 0)

    single_player.set_source(MOVIE)
    qapp.processEvents()

    assert backend["calls"] == ["play", "play"], "played when set, then told again"


def test_a_movie_that_fails_twice_is_not_retried_forever(single_player, backend, qapp, monkeypatch):
    """One instruction per movie. A second failure is a fault to report, not to fight."""
    monkeypatch.setattr(player_module, "START_TIMEOUT", 0)
    single_player.set_source(MOVIE)
    qapp.processEvents()
    backend["calls"].clear()

    qapp.processEvents()
    qapp.processEvents()

    assert backend["calls"] == []
