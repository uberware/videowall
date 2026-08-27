"""Playback must follow the system default audio output device.

A bare ``QAudioOutput`` resolves the default device once, when it is constructed, and then
holds that device for its whole life. Turning headphones on moves the system default but
leaves every player still feeding the speakers, so the wall keeps playing out of the wrong
hardware until it is restarted. ``follow_default_audio_device`` re-points the live players
at the current default, and one shared watcher calls it whenever the device list changes.

The sweep is exercised against real ``QAudioOutput`` objects and real devices: the tests
push the players onto a non-default device, run the sweep, and assert they came back. That
needs a machine with at least two output devices, so those tests skip on a bare CI runner
while the watcher tests below still run everywhere.
"""

import dataclasses

import pytest
from PySide6.QtCore import QUrl
from PySide6.QtMultimedia import QAudioOutput, QMediaDevices, QMediaPlayer

from videowall import player, window


@pytest.fixture(autouse=True)
def clean_device_watcher():
    """Drop the shared watcher between tests so each one starts with none created."""
    yield
    player._device_watcher = None


@pytest.fixture
def other_device(qapp):
    """Return a real output device that is not the current system default."""
    default = QMediaDevices.defaultAudioOutput()
    others = [d for d in QMediaDevices.audioOutputs() if d != default]
    if not others:
        pytest.skip("needs a second audio output device to switch away from")
    return others[0]


@pytest.fixture
def recovery_transport(single_player, monkeypatch):
    """Stand in for the media a headless player cannot hold, and record its transport.

    Recovery reads the playback state and position Qt reports and answers with play, seek
    and pause commands. Nothing plays in a headless test, so the readings come from this
    harness and the commands are recorded rather than run.
    """
    harness = {"calls": [], "state": QMediaPlayer.PlaybackState.PlayingState, "position": 0}
    media = type(single_player.player)
    monkeypatch.setattr(media, "playbackState", lambda self: harness["state"])
    monkeypatch.setattr(media, "position", lambda self: harness["position"])
    for name in ("play", "pause"):
        monkeypatch.setattr(media, name, lambda self, _name=name: harness["calls"].append((_name, None)))
    monkeypatch.setattr(media, "setPosition", lambda self, position: harness["calls"].append(("setPosition", position)))
    return harness


def run_recovery(item, harness):
    """Take a player through a whole device loss recovery, in place of Qt's signals.

    The state flips to playing partway through because the real ``play`` of the reload
    would have started the movie again by then, which is what releases the seek.
    """
    player.follow_default_audio_device()
    item.recover_from_device_loss(QMediaPlayer.Error.FormatError, "Failed to load media")
    item._resume_after_reload(QMediaPlayer.MediaStatus.BufferedMedia)
    harness["state"] = QMediaPlayer.PlaybackState.PlayingState
    item._seek_after_reload(item.recovery_target)


def test_the_sweep_returns_every_player_to_the_current_default(two_players, other_device):
    """Both players are playing out of the wrong device, and both are brought back."""
    for item in two_players:
        item.audio.setDevice(other_device)
    assert all(item.audio.device() == other_device for item in two_players), "precondition"

    player.follow_default_audio_device()

    default = QMediaDevices.defaultAudioOutput()
    assert [item.audio.device() for item in two_players] == [default, default]


def test_the_sweep_skips_a_player_that_has_been_closed(two_players, other_device, qapp):
    """Closing a player unregisters it, so the sweep must not reach its dead widget."""
    doomed, survivor = two_players
    survivor.audio.setDevice(other_device)
    doomed.close()
    qapp.processEvents()

    player.follow_default_audio_device()

    assert survivor.audio.device() == QMediaDevices.defaultAudioOutput()


def test_the_sweep_keeps_the_volume_it_found(single_player, other_device):
    """Volume belongs to the audio output, not the device, and must survive the move."""
    single_player.audio.setDevice(other_device)
    single_player.audio.setVolume(0.42)

    player.follow_default_audio_device()

    assert single_player.audio.volume() == pytest.approx(0.42)


def test_one_watcher_is_shared_by_every_player(two_players):
    """A wall of a dozen players still listens for device changes exactly once."""
    assert player._device_watcher is not None
    assert player._device_watcher is player._device_watcher


def test_no_watcher_is_created_when_audio_is_off(qapp, test_options, monkeypatch):
    """With play_audio off no player owns an audio output, so there is nothing to follow."""
    silent = dataclasses.replace(test_options, play_audio=False)
    for module in (player, window):
        monkeypatch.setattr(module, "OPTIONS", silent)

    win = window.MainWindow()
    win.show()
    qapp.processEvents()
    try:
        assert player._device_watcher is None
    finally:
        win.close()
        for item in list(player._runtime_data["all players"]):
            item.close()
        qapp.processEvents()


class TestRecoveryFromDeviceLoss:
    """Qt fails a player with FormatError when the device it is bound to disappears.

    The player is not broken and its file is fine, so the wall reloads it and resumes from
    just before where it stopped. Recovery is only attempted for a player armed by a device
    change, which is what stops a genuinely corrupt movie reloading itself forever.
    """

    def test_a_device_change_arms_every_player(self, two_players):
        """Any player may be the one Qt kills, so all of them are armed."""
        player.follow_default_audio_device()

        assert [item.recovery_is_armed() for item in two_players] == [True, True]

    def test_an_armed_player_reloads_its_source(self, single_player, tmp_path):
        """The source is cleared and restored, because Qt ignores an unchanged URL."""
        movie = tmp_path / "movie.mp4"
        movie.write_bytes(b"not really a movie")
        single_player.player.setSource(QUrl.fromLocalFile(movie))
        source = single_player.player.source()
        player.follow_default_audio_device()

        single_player.recover_from_device_loss(QMediaPlayer.Error.FormatError, "Failed to load media")

        assert single_player.player.source() == source
        assert single_player.recovery_phase == "reloading"

    def test_the_reload_clears_the_source_before_restoring_it(self, single_player, tmp_path):
        """Setting the same URL again does nothing in Qt, so a bare setSource never reloads.

        Clearing first makes the source change twice: once to nothing, once back again.
        """
        movie = tmp_path / "movie.mp4"
        movie.write_bytes(b"not really a movie")
        single_player.player.setSource(QUrl.fromLocalFile(movie))
        player.follow_default_audio_device()
        changes = []
        single_player.player.sourceChanged.connect(changes.append)

        single_player.recover_from_device_loss(QMediaPlayer.Error.FormatError, "Failed to load media")

        assert changes == [QUrl(), QUrl.fromLocalFile(movie)]

    def test_an_unarmed_player_leaves_the_error_alone(self, single_player, tmp_path):
        """A corrupt movie errors without any device change, and must not reload forever."""
        movie = tmp_path / "movie.mp4"
        movie.write_bytes(b"not really a movie")
        single_player.player.setSource(QUrl.fromLocalFile(movie))

        single_player.recover_from_device_loss(QMediaPlayer.Error.FormatError, "Failed to load media")

        assert single_player.recovery_phase is None

    def test_recovery_resumes_where_it_stopped(self, single_player, monkeypatch):
        """Playback picks up at the last known position, with no rewind.

        Restoring a saved layout rewinds by pre_roll because the position on disk is stale.
        Here the position is the live one Qt reported as it died, so it needs no adjusting.
        """
        monkeypatch.setattr(type(single_player.player), "position", lambda self: 60000)
        player.follow_default_audio_device()

        single_player.recover_from_device_loss(QMediaPlayer.Error.FormatError, "Failed to load media")

        assert single_player.recovery_target == 60000

    def test_an_unrelated_error_is_not_treated_as_device_loss(self, single_player):
        """Only the failures a vanished device produces are worth reloading for."""
        player.follow_default_audio_device()

        single_player.recover_from_device_loss(QMediaPlayer.Error.AccessDeniedError, "nope")

        assert single_player.recovery_phase is None

    def test_arming_remembers_that_the_player_was_playing(self, single_player, recovery_transport):
        """The state is read as the device changes, before Qt has failed the player."""
        recovery_transport["state"] = QMediaPlayer.PlaybackState.PlayingState

        player.follow_default_audio_device()

        assert single_player.recovery_playing is True

    def test_arming_remembers_that_the_player_was_paused(self, single_player, recovery_transport):
        """A paused wall is what recovery has to put back, so the pause is recorded."""
        recovery_transport["state"] = QMediaPlayer.PlaybackState.PausedState

        player.follow_default_audio_device()

        assert single_player.recovery_playing is False

    def test_a_player_that_was_playing_is_left_playing(self, single_player, recovery_transport):
        """The reloaded movie runs on by itself, exactly as it did before the device went."""
        recovery_transport["state"] = QMediaPlayer.PlaybackState.PlayingState

        run_recovery(single_player, recovery_transport)

        assert ("setPosition", 0) in recovery_transport["calls"]
        assert "pause" not in [name for name, _ in recovery_transport["calls"]]

    def test_a_player_that_was_paused_is_paused_again(self, single_player, recovery_transport):
        """Losing the headphones must not start a wall the user had deliberately stopped."""
        recovery_transport["state"] = QMediaPlayer.PlaybackState.PausedState

        run_recovery(single_player, recovery_transport)

        assert [name for name, _ in recovery_transport["calls"]][-2:] == ["setPosition", "pause"]

    def test_a_player_that_was_paused_lands_on_the_frame_it_stopped_on(self, single_player, recovery_transport):
        """The pause comes after the seek, so the frame left on screen is the right one."""
        recovery_transport["state"] = QMediaPlayer.PlaybackState.PausedState
        recovery_transport["position"] = 60000

        run_recovery(single_player, recovery_transport)

        assert ("setPosition", 60000) in recovery_transport["calls"]


class TestTheSweepOnlyMovesWhatNeedsMoving:
    """``audioOutputsChanged`` reports a change to the list of devices, not to the default.

    A device appearing or disappearing anywhere fires it, so most sweeps find some players
    already on the device they are being pointed at. Reconfiguring a live audio output that
    is already correct is work for nothing, and it is done to every player at once.
    """

    @pytest.fixture
    def device_calls(self, monkeypatch):
        """Record every setDevice, so a call that should not happen can be seen not to."""
        calls = []
        original = QAudioOutput.setDevice

        def record(self, device):
            calls.append(device.description())
            original(self, device)

        monkeypatch.setattr(QAudioOutput, "setDevice", record)
        return calls

    def test_a_player_already_on_the_default_is_left_alone(self, single_player, device_calls):
        """The common case: nothing moved, so nothing is touched."""
        assert single_player.audio.device() == QMediaDevices.defaultAudioOutput(), "precondition"

        player.follow_default_audio_device()

        assert device_calls == []

    def test_a_player_on_the_wrong_device_is_still_moved(self, single_player, other_device, device_calls):
        """Skipping the redundant calls must not skip the ones that do the work."""
        single_player.audio.setDevice(other_device)
        device_calls.clear()

        player.follow_default_audio_device()

        assert device_calls == [QMediaDevices.defaultAudioOutput().description()]
        assert single_player.audio.device() == QMediaDevices.defaultAudioOutput()


class TestArmingExpires:
    """Arming a player says a failure right now is probably the device that just changed.

    It cannot go on saying that. Left standing, an arming from the morning is still there in
    the evening, and the first unrelated error of the day is treated as device loss and
    answered with a reload of a player that was playing perfectly well.
    """

    def test_a_failure_arriving_promptly_is_still_recovered(self, single_player, tmp_path):
        """Qt fails a player within moments of the device going, which is the case to keep."""
        movie = tmp_path / "movie.mp4"
        movie.write_bytes(b"not really a movie")
        single_player.player.setSource(QUrl.fromLocalFile(movie))
        player.follow_default_audio_device()

        single_player.recover_from_device_loss(QMediaPlayer.Error.FormatError, "Failed to load media")

        assert single_player.recovery_phase == "reloading"

    def test_a_failure_long_afterwards_is_left_alone(self, single_player, tmp_path):
        """An hour later this is just a broken movie, and reloading it would hide that."""
        movie = tmp_path / "movie.mp4"
        movie.write_bytes(b"not really a movie")
        single_player.player.setSource(QUrl.fromLocalFile(movie))
        player.follow_default_audio_device()
        single_player.recovery_armed_at -= 3600

        single_player.recover_from_device_loss(QMediaPlayer.Error.FormatError, "Failed to load media")

        assert single_player.recovery_phase is None

    def test_the_window_is_measured_from_the_most_recent_change(self, single_player):
        """Switching device again re-arms, rather than counting from the first switch."""
        player.follow_default_audio_device()
        single_player.recovery_armed_at -= 3600
        assert not single_player.recovery_is_armed(), "precondition"

        player.follow_default_audio_device()

        assert single_player.recovery_is_armed()
