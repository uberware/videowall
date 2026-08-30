"""Nothing commands the player from inside one of the player's own signals.

A diagnostics run caught what that costs. A random mode cell reached the end of its movie,
the next source was set from inside ``positionChanged``, and the end of stream that was
still in flight arrived one millisecond later, against the new media:

    .044 Playback state PlayingState at 0
    .045 Media status EndOfMedia
    .045 Playback state StoppedState at 0

The cell sat dead on a movie that was loaded, healthy and 465 seconds long. Every command
the backend receives from inside one of its own notifications is handed to the event loop
instead, so the transition it is in the middle of finishes first.
"""

import time

import pytest
from PySide6.QtMultimedia import QMediaPlayer

from videowall.player import PlayerSpec

DURATION = 100000
"""Length of the movie the headless players pretend to hold."""


@pytest.fixture
def backend(single_player, monkeypatch):
    """Record the commands the backend is given, and stand in for the media it holds."""
    calls = []
    media = type(single_player.player)
    monkeypatch.setattr(media, "duration", lambda self: DURATION)
    monkeypatch.setattr(media, "setSource", lambda self, source: calls.append(("setSource", source)))
    monkeypatch.setattr(media, "setPosition", lambda self, position: calls.append(("setPosition", position)))
    for name in ("play", "pause"):
        monkeypatch.setattr(media, name, lambda self, _name=name: calls.append((_name, None)))
    return calls


def names(calls):
    """Return just the command names that were recorded."""
    return [name for name, _ in calls]


def test_the_end_of_a_movie_is_handled_after_the_signal_returns(single_player, backend, qapp, monkeypatch):
    """This is the race itself: the next source must not be set inside positionChanged."""
    ended = []
    monkeypatch.setattr(type(single_player), "end_action", lambda self: ended.append(self))
    single_player.mode = PlayerSpec.NEXT

    single_player._update_timeline_position(DURATION)

    assert ended == [], "the end action must not run inside the player's own signal"
    qapp.processEvents()
    assert ended == [single_player]


def test_a_movie_sitting_at_its_end_runs_the_end_action_once(single_player, backend, qapp, monkeypatch):
    """Position callbacks keep arriving at the end, and each must not queue another skip."""
    ended = []
    monkeypatch.setattr(type(single_player), "end_action", lambda self: ended.append(self))
    single_player.mode = PlayerSpec.NEXT

    single_player._update_timeline_position(DURATION)
    single_player._update_timeline_position(DURATION)
    single_player._update_timeline_position(DURATION)
    qapp.processEvents()

    assert ended == [single_player]


def test_a_loop_still_never_runs_the_end_action(single_player, backend, qapp, monkeypatch):
    """Loop mode wraps inside the backend, and deferring must not hand it a second wrap."""
    ended = []
    monkeypatch.setattr(type(single_player), "end_action", lambda self: ended.append(self))
    single_player.mode = PlayerSpec.LOOP

    single_player._update_timeline_position(DURATION)
    qapp.processEvents()

    assert ended == []


def test_a_restored_position_is_seeked_after_the_signal_returns(single_player, backend, qapp):
    """Restoring a layout seeks from the first position callback, which is the same hazard."""
    single_player.pending_position = 45000

    single_player._update_timeline_position(0)

    assert backend == [], "the seek must not run inside the player's own signal"
    qapp.processEvents()
    assert backend == [("setPosition", 45000)]


def test_the_device_reload_happens_after_the_error_returns(single_player, backend, qapp):
    """The reload answers errorOccurred, so it must not set a source inside it."""
    single_player.recovery_armed_at = time.monotonic()

    single_player.recover_from_device_loss(QMediaPlayer.Error.FormatError, "device went")

    assert "setSource" not in names(backend), "the reload must not run inside the error signal"
    qapp.processEvents()
    assert names(backend) == ["setSource", "setSource"], "cleared, then set again"


def test_the_resumed_play_happens_after_the_status_returns(single_player, backend, qapp):
    """Resuming answers mediaStatusChanged, so the play waits for it to return."""
    single_player.recovery_phase = "reloading"

    single_player._resume_after_reload(QMediaPlayer.MediaStatus.BufferedMedia)

    assert backend == [], "the play must not run inside the status signal"
    qapp.processEvents()
    assert names(backend) == ["play"]


def test_the_seek_back_happens_after_the_position_returns(single_player, backend, qapp, monkeypatch):
    """Seeking back answers positionChanged, which is where the race was found."""
    monkeypatch.setattr(
        type(single_player.player),
        "playbackState",
        lambda self: QMediaPlayer.PlaybackState.PlayingState,
    )
    single_player.recovery_phase = "seeking"
    single_player.recovery_target = 60000

    single_player._seek_after_reload(0)

    assert backend == [], "the seek must not run inside the player's own signal"
    qapp.processEvents()
    assert backend == [("setPosition", 60000)]


def test_a_player_closed_before_its_pending_work_runs_is_left_alone(single_player, backend, qapp, monkeypatch):
    """Deferred work outlives the signal, so a cell closed in between must not be driven."""
    ended = []
    monkeypatch.setattr(type(single_player), "end_action", lambda self: ended.append(self))
    single_player.mode = PlayerSpec.NEXT
    single_player._update_timeline_position(DURATION)

    single_player.close()
    qapp.processEvents()

    assert ended == []
