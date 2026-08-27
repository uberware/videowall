"""The window titlebar carries the name of the layout that is currently open.

The name comes from the layout file, so a layout that has never been saved — a new wall,
the demo, or the auto saved last layout — leaves the titlebar empty rather than showing a
name the user cannot go back to.
"""

from PySide6.QtWidgets import QInputDialog

from videowall.options import DEMO_SPEC


def test_the_titlebar_is_empty_with_no_layout_open(main_window):
    """A wall built from nothing has no name to show."""
    assert main_window.windowTitle() == ""


def test_opening_a_layout_names_the_titlebar(main_window, qapp):
    """Stepping onto a saved layout puts its name up where the user can read it."""
    main_window.step_layout(1)
    qapp.processEvents()

    assert main_window.windowTitle() == "Alpha Layout"


def test_stepping_on_renames_the_titlebar(main_window, qapp):
    """The name follows the wall, so it is never left describing the previous layout."""
    main_window.step_layout(1)
    main_window.step_layout(1)
    qapp.processEvents()

    assert main_window.windowTitle() == "Beta Layout"


def test_saving_a_layout_names_the_titlebar(main_window, qapp, monkeypatch):
    """Saving is the other way a wall acquires a name, without going through a reset."""
    monkeypatch.setattr(QInputDialog, "getText", lambda *args, **kwargs: ("My Wall", True))

    main_window.save()
    qapp.processEvents()

    assert main_window.windowTitle() == "My Wall"


def test_the_demo_layout_clears_the_titlebar(main_window, qapp):
    """Leaving a saved layout for an unsaved one must not keep the old name on screen."""
    main_window.step_layout(1)
    qapp.processEvents()

    main_window.reset(DEMO_SPEC, clear_open_layout=True)
    qapp.processEvents()

    assert main_window.windowTitle() == ""
