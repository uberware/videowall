"""A player that quietly stops advancing has to be noticed.

Loop mode wraps inside the backend through ``setLoops``, so nothing in this package runs
when a loop comes round and nothing runs when one fails. A player that does not wrap just
sits there as a still frame, and the log for that stretch is empty. ``StallWatcher`` polls
what the backend reports instead: a player that claims to be playing while its position
stands still has stalled, and one standing still at the very end of its movie is a loop
that never came back round.

The clock is passed in rather than read, so a six second stall does not need six seconds.
"""

import pytest
from PySide6.QtMultimedia import QMediaPlayer

from videowall import diagnostics


@pytest.fixture
def transport(monkeypatch):
    """Drive what the backend reports, since a headless player never really plays."""
    harness = {
        "position": 0,
        "duration": 100000,
        "state": QMediaPlayer.PlaybackState.PlayingState,
        "status": QMediaPlayer.MediaStatus.BufferedMedia,
    }
    media = QMediaPlayer
    monkeypatch.setattr(media, "position", lambda self: harness["position"])
    monkeypatch.setattr(media, "duration", lambda self: harness["duration"])
    monkeypatch.setattr(media, "playbackState", lambda self: harness["state"])
    monkeypatch.setattr(media, "mediaStatus", lambda self: harness["status"])
    return harness


@pytest.fixture
def watcher(tmp_path, single_player, transport):
    """A watcher over one player, primed with a first reading."""
    watch = diagnostics.StallWatcher(tmp_path)
    watch.check(now=0.0)
    return watch


def test_a_player_that_keeps_moving_is_never_reported(watcher, transport):
    """The ordinary case: position climbs, nothing is wrong, nothing is said."""
    for tick, position in enumerate([1000, 2000, 3000, 4000, 5000], start=1):
        transport["position"] = position
        assert watcher.check(now=tick * 2.0) == []


def test_a_playing_player_stuck_in_place_is_reported(watcher, transport):
    """Playing but frozen is a stall, wherever in the movie it happens."""
    transport["position"] = 50000

    watcher.check(now=2.0)
    early = watcher.check(now=4.0)
    late = watcher.check(now=20.0)

    assert early == [], "must not fire before the stall threshold"
    assert len(late) == 1
    assert "STALLED" in late[0]


def test_a_player_stuck_at_the_end_is_reported_as_a_failed_loop(watcher, transport):
    """Stuck on the last frame is the exact shape of a loop that did not wrap."""
    transport["position"] = transport["duration"]

    watcher.check(now=2.0)
    stalled = watcher.check(now=20.0)

    assert len(stalled) == 1
    assert "LOOP DID NOT WRAP" in stalled[0]


def test_a_paused_player_is_not_a_stall(watcher, transport):
    """A wall the user stopped is standing still on purpose."""
    transport["state"] = QMediaPlayer.PlaybackState.PausedState
    transport["position"] = 50000

    watcher.check(now=2.0)

    assert watcher.check(now=20.0) == []


def test_a_stall_is_reported_once_rather_than_every_poll(watcher, transport):
    """A player stuck for an hour is one line in the log, not eighteen hundred."""
    transport["position"] = 50000
    watcher.check(now=2.0)

    first = watcher.check(now=20.0)
    again = watcher.check(now=40.0)

    assert len(first) == 1
    assert again == []


def test_a_player_that_comes_back_can_stall_again(watcher, transport):
    """Recovery re-arms the report, so a second stall is not swallowed by the first."""
    transport["position"] = 50000
    watcher.check(now=2.0)
    assert len(watcher.check(now=20.0)) == 1

    transport["position"] = 60000
    assert watcher.check(now=22.0) == [], "moving again clears the stall"

    assert watcher.check(now=24.0) == [], "the second stall is timed from the last move"
    assert len(watcher.check(now=40.0)) == 1


def test_a_stall_leaves_a_marker_for_the_watchdog(watcher, transport, tmp_path):
    """The marker is what gets the process sampled while the stall is still there."""
    transport["position"] = 50000
    watcher.check(now=2.0)

    watcher.check(now=20.0)

    assert (tmp_path / "stall").exists()
    assert "STALLED" in (tmp_path / "stall").read_text()


def test_a_closed_player_is_forgotten(watcher, transport, single_player, qapp):
    """Closing a player must not leave its reading behind to be compared against."""
    assert watcher.seen
    single_player.close()
    qapp.processEvents()

    watcher.check(now=2.0)

    assert watcher.seen == {}


def test_a_stall_records_the_output_device_it_happened_on(watcher, transport):
    """Whether these faults follow the headphones is an open question the log has to answer.

    Nobody should have to remember which output was live an hour ago, so the device is
    written down every time, and the correlation builds itself over a few sessions.
    """
    transport["position"] = 50000
    watcher.check(now=2.0)

    stalled = watcher.check(now=20.0)

    assert "out of " in stalled[0]


def test_a_player_with_no_audio_output_is_described_rather_than_breaking():
    """With play_audio off a player owns no audio output, and the report must survive it.

    This asks the naming function directly. Taking the audio output away from a live player
    would drop the last reference to an object the backend is still holding, which brings
    the interpreter down rather than exercising anything.
    """

    class Silent:
        """A player from a wall running with play_audio off."""

    assert diagnostics.output_device(Silent()) == "no audio output"


def test_a_stopped_player_holding_a_movie_is_reported(watcher, transport, single_player):
    """A player that stopped rather than wrapping or moving on is the quietest failure.

    Not playing is not the same as stopped on purpose. A player with a movie in it and the
    wall running around it has failed, whether it never started or gave up at the end.
    """
    single_player.filename = "/movies/something.mp4"
    transport["state"] = QMediaPlayer.PlaybackState.StoppedState

    early = watcher.check(now=4.0)
    late = watcher.check(now=20.0)

    assert early == [], "must not fire before the stall threshold"
    assert len(late) == 1
    assert "NOT PLAYING" in late[0]


def test_a_player_holding_no_movie_is_never_reported(watcher, transport, single_player):
    """An empty cell is stopped because there is nothing in it, which is not a fault."""
    assert single_player.filename is None
    transport["state"] = QMediaPlayer.PlaybackState.StoppedState

    watcher.check(now=2.0)

    assert watcher.check(now=20.0) == []


def test_a_stopped_player_that_starts_playing_is_forgiven(transport, watcher, single_player):
    """A slow movie that arrives late must not leave a report standing against it."""
    single_player.filename = "/movies/something.mp4"
    transport["state"] = QMediaPlayer.PlaybackState.StoppedState
    watcher.check(now=2.0)
    assert len(watcher.check(now=20.0)) == 1

    transport["state"] = QMediaPlayer.PlaybackState.PlayingState
    transport["position"] = 1000

    assert watcher.check(now=22.0) == []


def test_the_report_says_what_the_backend_claimed(watcher, transport, single_player):
    """The next occurrence has to explain itself, so the report carries state and status."""
    single_player.filename = "/movies/something.mp4"
    transport["state"] = QMediaPlayer.PlaybackState.StoppedState
    transport["status"] = QMediaPlayer.MediaStatus.LoadingMedia

    watcher.check(now=2.0)
    report = watcher.check(now=20.0)[0]

    assert "StoppedState" in report
    assert "LoadingMedia" in report
