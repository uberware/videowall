"""Locking the layout swaps the window frame, which must not cost the videos any space.

A locked wall hides the titlebar along with the player controls, so the "/" command moves
the frame as well as the widgets, and the same arithmetic has to hold there.

The offscreen platform used for testing draws no titlebar, so these tests stand in a
frame of their own to exercise the geometry arithmetic that ``_keep_frame`` does.
"""

import dataclasses

from conftest import send_key
from PySide6.QtCore import QRect, Qt

from videowall import player, window

TITLEBAR = 28
"""Height of the pretend titlebar, in pixels."""


def fake_frame(main_window, monkeypatch, margin):
    """Give the window a titlebar of ``margin`` pixels that ``show`` drops when frameless.

    Args:
        main_window: the window to wrap
        monkeypatch: the pytest monkeypatch fixture
        margin: the starting titlebar height, in pixels

    Returns:
        A dict whose "content" key tracks the content rectangle of the window.
    """
    state = {"content": QRect(100, 100 + margin, 1280, 720), "margin": margin}

    monkeypatch.setattr(main_window, "geometry", lambda: QRect(state["content"]))
    monkeypatch.setattr(
        main_window,
        "frameGeometry",
        lambda: state["content"].adjusted(0, -state["margin"], 0, 0),
    )
    monkeypatch.setattr(main_window, "setGeometry", lambda rect: state.update(content=QRect(rect)))
    # Showing the window rebuilds the native frame, so the titlebar comes or goes there,
    # following whichever flags were set before the show.
    monkeypatch.setattr(
        main_window,
        "show",
        lambda: state.update(margin=0 if main_window.windowFlags() & Qt.FramelessWindowHint else TITLEBAR),
    )
    return state


def test_locking_gives_the_titlebar_space_to_the_content(main_window, monkeypatch):
    """The window keeps its place on screen, so the players gain the titlebar height."""
    state = fake_frame(main_window, monkeypatch, TITLEBAR)

    main_window.toggle_lock()

    assert state["content"] == QRect(100, 100, 1280, 720 + TITLEBAR)


def test_unlocking_takes_the_space_back_for_the_titlebar(main_window, monkeypatch):
    """Restoring the frame must not push the window outward: the content pays for it."""
    main_window._apply_lock(True)
    state = fake_frame(main_window, monkeypatch, 0)

    main_window.toggle_lock()

    assert state["content"] == QRect(100, 100 + TITLEBAR, 1280, 720 - TITLEBAR)


def test_showing_the_controls_while_locked_brings_the_titlebar_back(main_window, monkeypatch):
    """The layout name is part of the interface, so it returns when the controls do."""
    main_window._apply_lock(True)
    state = fake_frame(main_window, monkeypatch, 0)

    main_window.toggle_all_ui()

    assert state["content"] == QRect(100, 100 + TITLEBAR, 1280, 720 - TITLEBAR)


def test_hiding_the_controls_while_locked_takes_the_titlebar_away(main_window, monkeypatch):
    """Dismissing the interface of a locked wall leaves nothing but the videos again."""
    main_window._apply_lock(True)
    main_window.toggle_all_ui()
    state = fake_frame(main_window, monkeypatch, TITLEBAR)

    main_window.toggle_all_ui()

    assert state["content"] == QRect(100, 100, 1280, 720 + TITLEBAR)


def test_the_slash_key_moves_the_frame_while_locked(main_window, monkeypatch):
    """The frame follows the shortcut, not only the method behind the menu entry."""
    main_window._apply_lock(True)
    state = fake_frame(main_window, monkeypatch, 0)

    send_key(main_window, Qt.Key_Slash, "/")

    assert state["content"] == QRect(100, 100 + TITLEBAR, 1280, 720 - TITLEBAR)


def test_the_controls_leave_the_frame_alone_when_unlocked(main_window, monkeypatch):
    """An unlocked wall always keeps its titlebar, so the command is widgets only."""
    state = fake_frame(main_window, monkeypatch, TITLEBAR)

    main_window.toggle_all_ui()

    assert state["content"] == QRect(100, 100 + TITLEBAR, 1280, 720)


def test_lock_titlebar_keeps_the_frame_across_the_toggle(qapp, test_options, monkeypatch):
    """The option holds the titlebar for the whole lock, so "/" cannot take it away."""
    kept = dataclasses.replace(test_options, lock_titlebar=True)
    for module in (player, window):
        monkeypatch.setattr(module, "OPTIONS", kept)
    win = window.MainWindow()
    win.resize(1280, 720)
    win.show()
    qapp.processEvents()
    try:
        win._apply_lock(True)
        state = fake_frame(win, monkeypatch, TITLEBAR)

        win.toggle_all_ui()

        assert state["content"] == QRect(100, 100 + TITLEBAR, 1280, 720)
    finally:
        win.close()
        for item in list(player._runtime_data["all players"]):
            item.close()
        qapp.processEvents()
