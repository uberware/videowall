# Videowall

This is a Qt based video wall player. It can play an arbitrary number of movies at the same time in a user customizable configuration.

Playback features include:
* Select loop, step forward, or random videos from a library
* Customize volume and playback speed for each video
* Play, Pause, Mute the whole wall
* Keyboard control for a primary video
* Save wall layouts and automatic recovery of last layout
* Lots of options for customizing operation

## Requirements

* Python 3.9+
* PySide6

## Use

Click a player to show the control UI.

Along the top is the list of movies found in the movie folder.

Buttons:
* `⨉` Close the player
* `|` Split the player row horizontally
* `—` Split the player column vertically
* `➘` Swap two players
* `↻` At the end, loop the current video
* `⇥` At the end, play the next video in the list
* `?` At the end, play a random video from the list
* `⚐` This player is controlled by the keyboard/menu playback options
* `◀︎` Jog this player backward
* `▶︎` Jog this player forward
* `★` Perform the end operation immediately

The top left slider controls playback speed (0% - 200%).

The bottom left slider controls the volume (0% - 100%).

The bottom slider will keep up with your position in the movie and allow you to scrub to any other position. The time on the left is the elapsed time, and the on the right is the remaining or total time (see below for option to configure which).

## Configuration

Currently, you must create a configuration file manually. That file must be called `videowall_settings.json` in your home folder. The file content is a JSON object with zero or more of the following values:

| Option                 | Type    | Default | Use                                                                                                                                            |
|------------------------|---------|---------|------------------------------------------------------------------------------------------------------------------------------------------------|
| `always_on_top`        | `bool`  | `True`  | The player window will always float above normal windows, even if the application is not active.                                               |
| `auto_update_layout`   | `bool`  | `True`  | When enabled, the open layout will be updated with any changes during the playback session when the layout is changed or the window is closed. |
| `default_volume`       | `float` | `1.0`   | (Range `0.0` - `1.0`) The volume to use when making a new player.                                                                              |
| `jog_interval`         | `int`   | `10000` | The number of milliseconds to move with the "jog" operation.                                                                                   |
| `layout_folder`        | `Path`  |         | The path where the layouts are stored                                                                                                          |
| `movie_folder`         | `Path`  |         | The path where the movies are stored                                                                                                           |
| `open_last_on_startup` | `bool`  | `True`  | When enabled, the last layout is loaded at startup                                                                                             |
| `pre_roll`             | `int`   | `2000`  | The number of milliseconds to rewind when loading a layout                                                                                     |
| `remaining_time`       | `bool`  | `True`  | When enabled, show remaining time instead of total time                                                                                        |
| `restore_window_state` | `bool`  | `True`  | When enabled, the window state is restored when loading a layout                                                                               |
