"""A silent player runs no audio pipeline at all.

Every player carries a ``QAudioOutput``, and on macOS that costs far more than the gain it
applies. AVFoundation builds a full AudioQueue for the movie's audio track and pushes it
through an out-of-process XPC bridge, whatever the volume is set to. A wall opened with
``default_volume`` at 0.0 was therefore decoding AAC and enqueueing buffers for every one
of its cells and playing none of it, and one such session died in AudioToolbox:

    BUG IN CLIENT OF LIBDISPATCH: dispatch_sync called on queue already owned by current
    thread   (AudioQueueXPC_Bridge::EnqueueBuffer)

Five audio queue threads were live at the time and four were blocked or trapping inside
AudioToolbox's own locking. Nothing in this package appeared anywhere in the crash, and
nothing here can fix Apple's reentrancy fault, so the wall stops feeding it: a player at
zero volume deselects its audio track and the queue behind it goes away entirely.

Detaching the ``QAudioOutput`` instead does not work. Qt answers that by muting the
AVPlayer, which leaves every queue running; only dropping the track removes them. So the
audio output stays exactly where it was, holding the volume and the device, and the track
is what comes and goes.

Qt refuses ``setActiveAudioTrack`` until a source is open, and a headless player holds no
real media, so these tests record the selection the player is given rather than reading it
back off the backend.
"""

import dataclasses

import pytest
from PySide6.QtMultimedia import QMediaPlayer

NO_TRACK = -1
"""The selection that deselects a player's audio, and with it the whole audio pipeline."""

FIRST_TRACK = 0
"""The selection a player comes back to when its volume is raised."""


@pytest.fixture
def selections(single_player, monkeypatch):
    """Record every audio track selection the backend is given.

    The real call is refused without an open source, so what a headless test can observe
    is the instruction, not the resulting state.
    """
    calls = []
    media = type(single_player.player)
    monkeypatch.setattr(media, "setActiveAudioTrack", lambda self, index: calls.append(index))
    return calls


def test_muting_a_player_drops_its_audio_track(single_player, selections):
    """A player turned down to silence deselects its audio, taking the AudioQueue with it."""
    single_player.set_volume(0.0)
    assert selections[-1] == NO_TRACK


def test_raising_the_volume_restores_the_audio_track(single_player, selections):
    """A player asked for sound gets its audio track back."""
    single_player.set_volume(0.0)
    single_player.set_volume(0.5)
    assert selections[-1] == FIRST_TRACK


def test_unmuting_restores_the_audio_track(single_player, selections):
    """The mute and unmute pair moves the track as well as the volume."""
    single_player.set_volume(0.4)
    single_player.mute()
    assert selections[-1] == NO_TRACK
    single_player.unmute()
    assert selections[-1] == FIRST_TRACK


@pytest.mark.parametrize("status", [QMediaPlayer.MediaStatus.LoadedMedia, QMediaPlayer.MediaStatus.BufferedMedia])
def test_a_loaded_movie_honours_a_silent_player(single_player, selections, status):
    """A selection does not survive a new source, so opening one applies it again.

    Qt drops the track selection with the media it belonged to. Without this a muted cell
    handed its next movie would quietly start up an audio queue for it.

    Both statuses count. A diagnostics log of six cells opening a saved layout went
    ``LoadingMedia`` straight to ``BufferedMedia`` without ever reporting ``LoadedMedia``,
    so answering only the one Qt documents would leave the real wall untouched.
    """
    single_player.set_volume(0.0)
    selections.clear()
    single_player.player.mediaStatusChanged.emit(status)
    assert selections == [NO_TRACK]


def test_a_wall_without_audio_never_touches_its_tracks(main_window, qapp, test_options, monkeypatch):
    """``play_audio`` off means no audio output to read, and nothing to select against."""
    from videowall import player as player_module

    silent = dataclasses.replace(test_options, play_audio=False)
    monkeypatch.setattr(player_module, "OPTIONS", silent)
    main_window.reset({"type": "VideoWall", "orientation": "horizontal", "items": [{"type": "Player"}]})
    qapp.processEvents()
    item = player_module._runtime_data["all players"][0]

    calls = []
    monkeypatch.setattr(type(item.player), "setActiveAudioTrack", lambda self, index: calls.append(index))
    item.set_volume(0.0)
    assert calls == []
