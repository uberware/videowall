"""Stepping through the saved layouts from the Layout menu.

The list is the same one the Open dialog shows, so the autosave the app writes on exit is
not part of it — stepping into your own last session is not a layout you chose to keep.
"""

import dataclasses

import pytest
from conftest import LAYOUTS, REAL_GET_FILES, send_key
from PySide6.QtCore import Qt

from videowall import content, window


@pytest.fixture
def layouts(main_window, stub_content):
    """Return the layout names in the order stepping walks them."""
    return sorted(LAYOUTS)


def open_layout_named(main_window, name):
    """Load a named layout, as the Open dialog would."""
    main_window.reset(main_window.read_spec(content.get_path("layout", name)))
    assert main_window.open_layout == content.get_path("layout", name)


def current_layout_name(main_window):
    """Return the name of the layout the window currently has open."""
    for name in content.get_files("layout"):
        if content.get_path("layout", name) == main_window.open_layout:
            return name
    return None


def test_next_moves_forward_through_the_list(main_window, layouts):
    """Next steps to the following entry."""
    open_layout_named(main_window, layouts[0])

    main_window.step_layout(1)

    assert current_layout_name(main_window) == layouts[1]


def test_previous_moves_backward_through_the_list(main_window, layouts):
    """Previous steps to the preceding entry."""
    open_layout_named(main_window, layouts[1])

    main_window.step_layout(-1)

    assert current_layout_name(main_window) == layouts[0]


def test_next_wraps_at_the_end(main_window, layouts):
    """Next from the last entry loops back to the first."""
    open_layout_named(main_window, layouts[-1])

    main_window.step_layout(1)

    assert current_layout_name(main_window) == layouts[0]


def test_previous_wraps_at_the_start(main_window, layouts):
    """Previous from the first entry loops round to the last."""
    open_layout_named(main_window, layouts[0])

    main_window.step_layout(-1)

    assert current_layout_name(main_window) == layouts[-1]


def test_next_with_no_layout_open_enters_at_the_first(main_window, layouts):
    """With nothing open there is no position, so Next enters the list at the top."""
    assert main_window.open_layout is None

    main_window.step_layout(1)

    assert current_layout_name(main_window) == layouts[0]


def test_previous_with_no_layout_open_enters_at_the_last(main_window, layouts):
    """With nothing open, Previous enters the list from the other end."""
    assert main_window.open_layout is None

    main_window.step_layout(-1)

    assert current_layout_name(main_window) == layouts[-1]


def test_random_always_moves_to_a_different_layout(main_window, layouts):
    """A random pick that lands on the current layout would look like nothing happened."""
    open_layout_named(main_window, layouts[0])

    for _ in range(20):
        previous = current_layout_name(main_window)
        main_window.step_layout(None)
        assert current_layout_name(main_window) != previous


def test_random_with_no_layout_open_picks_one(main_window, layouts):
    """Random still works as an entry point into the list."""
    assert main_window.open_layout is None

    main_window.step_layout(None)

    assert current_layout_name(main_window) in layouts


def test_stepping_with_no_layouts_does_nothing(main_window, monkeypatch):
    """An empty layout folder must not raise."""
    monkeypatch.setattr(content, "get_files", lambda kind: [] if kind == "layout" else ["A.mp4"])

    for direction in (1, -1, None):
        main_window.step_layout(direction)

    assert main_window.open_layout is None


def test_stepping_saves_the_layout_being_left(main_window, layouts, test_options, monkeypatch):
    """Paging away from a layout must not silently discard edits to it."""
    monkeypatch.setattr(window, "OPTIONS", dataclasses.replace(test_options, auto_update_layout=True))
    written = []
    monkeypatch.setattr(type(main_window), "write_spec", lambda self, file, **kw: written.append(file))
    open_layout_named(main_window, layouts[0])

    main_window.step_layout(1)

    assert written == [content.get_path("layout", layouts[0])]


def test_stepping_does_not_save_when_auto_update_is_off(main_window, layouts, test_options, monkeypatch):
    """With auto_update_layout disabled nothing is rewritten."""
    assert not test_options.auto_update_layout, "precondition: the test options disable auto update"
    written = []
    monkeypatch.setattr(type(main_window), "write_spec", lambda self, file, **kw: written.append(file))
    open_layout_named(main_window, layouts[0])

    main_window.step_layout(1)

    assert written == []


def test_layout_list_excludes_the_autosave(monkeypatch, tmp_path):
    """The autosave is not offered by the Open dialog or the stepping commands."""
    monkeypatch.setattr(
        content,
        "_files",
        {
            "content": {},
            "layout": {
                "last_layout": tmp_path / "last_layout.json",
                "Alpha": tmp_path / "Alpha.json",
                "Beta": tmp_path / "Beta.json",
            },
        },
    )

    assert REAL_GET_FILES("layout") == ["Alpha", "Beta"]


def test_movie_list_is_not_filtered(monkeypatch, tmp_path):
    """The autosave name is only special for layouts."""
    monkeypatch.setattr(
        content,
        "_files",
        {"content": {"last_layout": tmp_path / "last_layout.mp4"}, "layout": {}},
    )

    assert REAL_GET_FILES("content") == ["last_layout"]


@pytest.mark.parametrize(
    "key, text, offset",
    [(Qt.Key_Minus, "-", -1), (Qt.Key_Equal, "=", 1)],
    ids=["previous", "next"],
)
def test_shortcut_steps_the_layout(main_window, layouts, key, text, offset):
    """The - and = keys step the layout without going through the menu."""
    open_layout_named(main_window, layouts[1])

    send_key(main_window, key, text)

    assert current_layout_name(main_window) == layouts[1 + offset]


def test_shortcut_picks_a_random_layout(main_window, layouts):
    """The 1 key jumps to a different layout."""
    open_layout_named(main_window, layouts[0])

    send_key(main_window, Qt.Key_1, "1")

    assert current_layout_name(main_window) != layouts[0]
    assert current_layout_name(main_window) in layouts


def test_the_layout_menu_offers_the_three_commands(main_window):
    """The commands are reachable from the Layout menu, with their shortcuts shown."""
    # Keep the QAction referenced: PySide6 invalidates the QMenu wrapper it returns once
    # the action wrapper it came from is collected.
    layout_action = next(a for a in main_window.menuBar().actions() if a.text() == "Layout")
    shortcuts = {a.text(): a.shortcut().toString() for a in layout_action.menu().actions()}

    assert shortcuts["Previous Layout"] == "-"
    assert shortcuts["Next Layout"] == "="
    assert shortcuts["Random Layout"] == "1"
