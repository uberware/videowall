"""Keyboard shortcuts must survive the movie filter taking focus.

The text entry widgets accept ShortcutOverride, so while one of them holds focus an
unmodified key such as Space is typed into the field instead of reaching the menu action.
That is correct while the user is typing, but the controls used to keep focus after they
were dismissed, which left Space and the other single key shortcuts dead.
"""

from conftest import click_video, focus_filter, send_key
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication


def test_space_types_into_a_focused_filter(single_player, main_window, shortcut_fired):
    """Typing in the filter inserts a space rather than toggling playback."""
    focus_filter(single_player)

    send_key(main_window, Qt.Key_Space, " ")

    assert single_player.movie_filter.text() == " "
    assert not shortcut_fired


def test_hiding_the_interface_releases_filter_focus(single_player, main_window, shortcut_fired):
    """Space controls playback again once the controls are dismissed."""
    focus_filter(single_player)
    single_player.movie_filter.setText("")

    single_player.show_interface(False)
    send_key(main_window, Qt.Key_Space, " ")

    assert shortcut_fired
    assert single_player.movie_filter.text() == ""


def test_hiding_the_interface_hides_every_control(single_player, qapp):
    """Dismissing the controls really hides them, keeping them out of the focus chain."""
    single_player.show_interface(False)
    qapp.processEvents()

    assert [widget for widget in single_player._interface_widgets() if widget.isVisible()] == []


def test_showing_the_interface_restores_every_control(single_player, qapp):
    """Every control comes back parented, so none of them appears as a stray window."""
    single_player.show_interface(False)
    single_player.show_interface(True)
    qapp.processEvents()

    widgets = list(single_player._interface_widgets())
    assert widgets
    assert all(widget.isVisible() for widget in widgets)
    assert all(widget.parent() is not None for widget in widgets)


def test_a_player_that_starts_with_a_movie_hides_its_controls(main_window, qapp):
    """A player restored with a movie starts hidden without leaking a top level widget."""
    from videowall.player import Player

    item = Player({"type": "Player", "filename": "/nowhere/movie.mp4"})
    qapp.processEvents()
    assert [widget for widget in item._interface_widgets() if widget.isVisible()] == []

    item.show_interface(True)
    qapp.processEvents()
    assert all(widget.parent() is not None for widget in item._interface_widgets())
    item.close()


def test_clicking_the_video_releases_filter_focus(single_player, main_window, shortcut_fired):
    """Clicking the video means the user is done with the controls, so shortcuts resume."""
    focus_filter(single_player)
    single_player.movie_filter.setText("")

    click_video(single_player)
    send_key(main_window, Qt.Key_Space, " ")

    assert shortcut_fired
    assert single_player.movie_filter.text() == ""
    assert not single_player.movie_list.isVisible()


def test_clicking_the_video_releases_focus_while_locked(single_player, main_window, shortcut_fired, qapp):
    """A locked layout ignores the click for toggling but still hands back the keyboard."""
    focus_filter(single_player)
    single_player.movie_filter.setText("")
    main_window.toggle_lock()
    qapp.processEvents()

    click_video(single_player)
    send_key(main_window, Qt.Key_Space, " ")

    assert shortcut_fired
    assert single_player.movie_filter.text() == ""


def test_locking_the_layout_releases_filter_focus(single_player, main_window, shortcut_fired, qapp):
    """Locking closes the interfaces, which must drop focus with them."""
    focus_filter(single_player)
    single_player.movie_filter.setText("")

    main_window.toggle_lock()
    qapp.processEvents()
    send_key(main_window, Qt.Key_Space, " ")

    assert shortcut_fired
    assert single_player.movie_filter.text() == ""


def test_keypad_enter_commits_the_filter_and_releases_focus(single_player, main_window, shortcut_fired):
    """Keypad Enter reaches the line edit, so it can act as the commit key."""
    focus_filter(single_player)

    send_key(main_window, Qt.Key_Enter)
    text_after_enter = single_player.movie_filter.text()
    send_key(main_window, Qt.Key_Space, " ")

    assert shortcut_fired
    assert single_player.movie_filter.text() == text_after_enter


def test_return_and_escape_outrank_the_filter(single_player, main_window):
    """Return and Escape fire their shortcuts before the line edit ever sees them.

    This is pre-existing behaviour, recorded here because it is why the filter has no
    Escape handler: such a handler could never run.
    """
    focus_filter(single_player)

    send_key(main_window, Qt.Key_Return, "\r")
    assert single_player.movie_filter.text() == ""

    assert not main_window.is_muted()
    send_key(main_window, Qt.Key_Escape)
    assert single_player.movie_filter.text() == ""
    assert main_window.is_muted()


def test_movie_list_holds_focus_through_its_combobox(single_player):
    """The combobox is the focus proxy of its line edit, and belongs to the player."""
    single_player.movie_list.lineEdit().setFocus(Qt.MouseFocusReason)
    QApplication.processEvents()

    focused = QApplication.focusWidget()
    assert focused is single_player.movie_list
    assert single_player.isAncestorOf(focused)


def test_hiding_the_interface_releases_movie_list_focus(single_player, main_window, shortcut_fired):
    """The movie list swallows keys the same way the filter does, and is released the same way."""
    single_player.movie_list.lineEdit().setFocus(Qt.MouseFocusReason)
    QApplication.processEvents()
    send_key(main_window, Qt.Key_Space, " ")
    assert not shortcut_fired

    single_player.show_interface(False)
    send_key(main_window, Qt.Key_Space, " ")

    assert shortcut_fired


def test_selecting_a_movie_releases_focus(single_player, qapp):
    """Choosing a movie ends the interaction, so the keyboard goes back to playback."""
    single_player.movie_list.setFocus(Qt.MouseFocusReason)
    qapp.processEvents()

    single_player.movie_list.activated.emit(1)
    qapp.processEvents()

    assert not single_player.movie_list.hasFocus()


def test_hiding_one_player_leaves_another_players_focus_alone(two_players, qapp):
    """A player only ever releases focus that belongs to itself."""
    first, second = two_players
    focus_filter(second)

    first.show_interface(False)
    qapp.processEvents()

    assert QApplication.focusWidget() is second.movie_filter
