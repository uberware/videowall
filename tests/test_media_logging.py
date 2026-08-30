"""A media fault has to say so.

``errorOccurred`` was wired only to the audio device recovery, which returns without a word
when the player is not armed for one, so a movie that failed to open left the log empty and
the wall simply had a dead cell in it. The backend is the only witness to what happened to
a player, so what it reports is written down whether or not anything acts on it.
"""

import dataclasses
import logging

from conftest import players_of
from PySide6.QtMultimedia import QMediaPlayer

from videowall import player, window


def test_a_media_error_is_logged(single_player, caplog):
    """An error nothing recovers from is exactly the one that has to reach the log."""
    with caplog.at_level(logging.WARNING, logger="videowall"):
        single_player.player.errorOccurred.emit(QMediaPlayer.Error.ResourceError, "no such file")

    assert "ResourceError" in caplog.text
    assert "no such file" in caplog.text


def test_a_media_error_is_logged_with_audio_disabled(qapp, test_options, monkeypatch, caplog):
    """The logging must not be hidden behind the audio setup the recovery needs."""
    silent = dataclasses.replace(test_options, play_audio=False)
    for module in (player, window):
        monkeypatch.setattr(module, "OPTIONS", silent)
    win = window.MainWindow()
    qapp.processEvents()
    try:
        item = players_of(win)[0]
        with caplog.at_level(logging.WARNING, logger="videowall"):
            item.player.errorOccurred.emit(QMediaPlayer.Error.FormatError, "bad format")

        assert "FormatError" in caplog.text
    finally:
        win.close()
        for item in list(player._runtime_data["all players"]):
            item.close()
        qapp.processEvents()


def test_a_playback_state_change_is_logged(single_player, caplog):
    """A player that stops says nothing of its own, so the transition is the record."""
    with caplog.at_level(logging.DEBUG, logger="videowall"):
        single_player.player.playbackStateChanged.emit(QMediaPlayer.PlaybackState.StoppedState)

    assert "StoppedState" in caplog.text


def test_a_media_status_change_is_logged(single_player, caplog):
    """Which of loading, buffering or end of media it reached is the whole diagnosis."""
    with caplog.at_level(logging.DEBUG, logger="videowall"):
        single_player.player.mediaStatusChanged.emit(QMediaPlayer.MediaStatus.EndOfMedia)

    assert "EndOfMedia" in caplog.text
