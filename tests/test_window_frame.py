"""Locking the layout swaps the window frame, which must not cost the videos any space.

The offscreen platform used for testing draws no titlebar, so these tests stand in a
frame of their own to exercise the geometry arithmetic that ``_keep_frame`` does.
"""

from PySide6.QtCore import QRect

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
    frameless = TITLEBAR - margin

    monkeypatch.setattr(main_window, "geometry", lambda: QRect(state["content"]))
    monkeypatch.setattr(
        main_window,
        "frameGeometry",
        lambda: state["content"].adjusted(0, -state["margin"], 0, 0),
    )
    monkeypatch.setattr(main_window, "setGeometry", lambda rect: state.update(content=QRect(rect)))
    # Showing the window rebuilds the native frame, so the titlebar comes or goes there.
    monkeypatch.setattr(main_window, "show", lambda: state.update(margin=frameless))
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
