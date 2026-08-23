"""Toggling every player's interface at once.

The "/" command differs from the per player Tab toggle in two ways: it drives the whole
wall from one shared state, so a mixed wall resolves to all hidden, and it keeps working
while the layout is locked, where the controls are shown for reference but must not be
usable.
"""

import dataclasses

from conftest import players_of, send_key
from PySide6.QtCore import Qt

from videowall import player, window


def interfaces_shown(items):
    """Return whether each of the given players is currently showing its controls."""
    return [item.movie_list.isVisible() for item in items]


def test_toggle_all_shows_every_interface_when_all_are_hidden(two_players, qapp):
    """With the whole wall dismissed the command brings every set of controls back."""
    for item in two_players:
        item.show_interface(False)
    qapp.processEvents()

    player.toggle_all()
    qapp.processEvents()

    assert interfaces_shown(two_players) == [True, True]


def test_toggle_all_hides_the_wall_when_only_one_interface_is_shown(two_players, qapp):
    """One visible interface is enough to make the command a hide rather than a show."""
    two_players[0].show_interface(False)
    two_players[1].show_interface(True)
    qapp.processEvents()

    player.toggle_all()
    qapp.processEvents()

    assert interfaces_shown(two_players) == [False, False]


def test_toggle_all_hides_a_fully_shown_wall(two_players, qapp):
    """The command is a straight toggle when every interface is already up."""
    player.toggle_all()
    qapp.processEvents()

    assert interfaces_shown(two_players) == [False, False]


def test_locked_toggle_all_shows_the_controls(two_players, main_window, qapp):
    """Locking hides the controls, and the command still puts them back on screen."""
    main_window.toggle_lock()
    qapp.processEvents()

    player.toggle_all()
    qapp.processEvents()

    assert interfaces_shown(two_players) == [True, True]


def test_controls_shown_while_locked_are_disabled(two_players, main_window, qapp):
    """A locked wall shows its controls for reference only, with nothing operable."""
    main_window.toggle_lock()
    player.toggle_all()
    qapp.processEvents()

    for item in two_players:
        assert not any(widget.isEnabled() for widget in item._interface_widgets())


def test_unlocking_makes_the_shown_controls_usable_again(two_players, main_window, qapp):
    """The controls left on screen by a locked toggle go live the moment the lock lifts."""
    main_window.toggle_lock()
    player.toggle_all()
    qapp.processEvents()

    main_window.toggle_lock()
    qapp.processEvents()

    for item in two_players:
        assert all(widget.isEnabled() for widget in item._interface_widgets())


def test_unlocking_leaves_the_volume_slider_off_when_audio_is_disabled(qapp, test_options, monkeypatch):
    """Re-enabling the interface must not hand back a control audio settings ruled out."""
    silent = dataclasses.replace(test_options, play_audio=False)
    for module in (player, window):
        monkeypatch.setattr(module, "OPTIONS", silent)
    win = window.MainWindow()
    win.show()
    qapp.processEvents()
    try:
        item = players_of(win)[0]
        win.toggle_lock()
        player.toggle_all()
        win.toggle_lock()
        qapp.processEvents()

        assert not item.volume_slider.isEnabled()
    finally:
        win.close()
        for item in list(player._runtime_data["all players"]):
            item.close()
        qapp.processEvents()


def test_the_slash_key_toggles_the_whole_wall(two_players, main_window, qapp):
    """The shortcut is wired to the command, not just the menu."""
    send_key(main_window, Qt.Key_Slash, "/")
    qapp.processEvents()

    assert interfaces_shown(two_players) == [False, False]


def test_the_slash_key_still_works_while_locked(two_players, main_window, qapp):
    """Locking disables the per player toggle, but never the whole wall command."""
    main_window.toggle_lock()
    qapp.processEvents()

    send_key(main_window, Qt.Key_Slash, "/")
    qapp.processEvents()

    assert interfaces_shown(two_players) == [True, True]


def test_a_closed_player_is_forgotten_by_the_command(two_players, qapp):
    """A shut player must not leave the wall looking as though an interface is up.

    A new Player shows its controls as it is built, so every closed cell used to leave an
    entry behind in the visible set and made the next command a hide of an empty wall.
    """
    two_players[0].close()
    two_players[1].show_interface(False)
    qapp.processEvents()

    player.toggle_all()
    qapp.processEvents()

    assert two_players[1].movie_list.isVisible()
