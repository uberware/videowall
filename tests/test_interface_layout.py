"""Showing and hiding the player interface must leave the layout intact.

Hiding the controls is what frees the cell for the video, so these tests guard the
geometry that the focus handling in ``show_interface`` sits on top of.
"""


def test_video_fills_the_cell_when_the_interface_is_hidden(single_player, qapp):
    """With the controls dismissed the video gets the whole player cell."""
    single_player.show_interface(False)
    qapp.processEvents()

    assert single_player.video.size() == single_player.size()


def test_video_makes_room_when_the_interface_is_shown(single_player, qapp):
    """The controls take space from the video rather than overlapping it."""
    single_player.show_interface(True)
    qapp.processEvents()

    video = single_player.video.geometry()
    assert video.width() < single_player.width()
    assert video.height() < single_player.height()


def test_controls_sit_around_the_video(single_player, qapp):
    """The filter row sits above the video and the timeline row below it."""
    single_player.show_interface(True)
    qapp.processEvents()

    video = single_player.video.geometry()
    assert single_player.movie_filter.geometry().bottom() <= video.top()
    assert single_player.timeline.geometry().top() >= video.bottom()


def test_every_control_has_a_real_size_when_shown(single_player, qapp):
    """No control is laid out at zero size once the interface is shown."""
    single_player.show_interface(True)
    qapp.processEvents()

    assert all(w.width() > 0 and w.height() > 0 for w in single_player._interface_widgets())


def test_the_layout_survives_a_hide_show_hide_round_trip(single_player, qapp):
    """Toggling the interface returns the cell to exactly its previous geometry."""
    single_player.show_interface(False)
    qapp.processEvents()
    hidden = single_player.video.geometry()

    single_player.show_interface(True)
    qapp.processEvents()
    single_player.show_interface(False)
    qapp.processEvents()

    assert single_player.video.geometry() == hidden
