"""Global playback state must survive loading a new layout.

A new Player starts its own media in ``set_source``, so every freshly loaded layout comes
up playing. ``MainWindow.reset`` re-applies the muted and locked state to the new tree; the
paused state has to travel the same way or the Pause menu item ends up describing the
opposite of what the players are doing.
"""

import pytest

TWO_PLAYERS = {
    "type": "VideoWall",
    "orientation": "horizontal",
    "items": [{"type": "Player"}, {"type": "Player"}],
    "sizes": [640, 640],
}


@pytest.fixture
def paused_window(main_window, qapp):
    """Return a window whose playback the user has paused."""
    main_window.play()
    qapp.processEvents()
    assert main_window.play_action.text() == "Play", "precondition: window is paused"
    return main_window


def test_layout_opened_while_paused_keeps_the_menu_in_sync(paused_window, qapp):
    """The menu still offers Play, because playback is still paused."""
    paused_window.reset(TWO_PLAYERS)
    qapp.processEvents()

    assert paused_window.play_action.text() == "Play"
    assert paused_window.is_paused()


def test_layout_opened_while_paused_pauses_its_players(paused_window, qapp, transport_calls):
    """Every player in the new layout is told to pause."""
    paused_window.reset(TWO_PLAYERS)
    qapp.processEvents()

    paused = {item for kind, item in transport_calls if kind == "pause"}
    assert len(paused) == 2


def test_one_press_resumes_a_layout_opened_while_paused(paused_window, qapp, transport_calls):
    """A single press plays again, instead of the first press being swallowed."""
    paused_window.reset(TWO_PLAYERS)
    qapp.processEvents()
    transport_calls.clear()

    paused_window.play()
    qapp.processEvents()

    assert paused_window.play_action.text() == "Pause"
    assert {item for kind, item in transport_calls if kind == "play"}
    assert not [kind for kind, _ in transport_calls if kind == "pause"]


def test_mouse_timer_stays_stopped_for_a_layout_opened_while_paused(paused_window, qapp):
    """The mouse hiding timer is off while paused and must not restart itself."""
    paused_window.reset(TWO_PLAYERS)
    qapp.processEvents()

    assert not paused_window._mouse_timer.isActive()


def test_layout_opened_while_playing_is_left_playing(main_window, qapp, transport_calls):
    """Loading a layout during playback must not pause anything."""
    assert main_window.play_action.text() == "Pause", "precondition: window is playing"

    main_window.reset(TWO_PLAYERS)
    qapp.processEvents()

    assert main_window.play_action.text() == "Pause"
    assert not [kind for kind, _ in transport_calls if kind == "pause"]


def test_layout_opened_while_muted_is_muted(main_window, qapp):
    """The muted state already survives a reset; this is the pattern paused state follows."""
    main_window.mute()
    qapp.processEvents()

    main_window.reset(TWO_PLAYERS)
    qapp.processEvents()

    assert main_window.is_muted()
    assert main_window.root.muted
