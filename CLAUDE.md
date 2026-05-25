# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Run the app (activate venv first)
source venv-build/bin/activate
python -m videowall          # or: videowall (after pip install -e .)

# Lint
ruff check src/
ruff format src/

# Security scan
bandit -r src/
```

There are no automated tests in this project.

## Release / CI

Merging a PR to `main` automatically publishes to PyPI via `.github/workflows/release.yml`. Before merging, bump the version in `pyproject.toml`.

## Architecture

This is a PySide6 (Qt) desktop app that plays multiple videos simultaneously in a user-configurable grid layout.

### Module overview

| Module | Role |
|--------|------|
| `main.py` | Entry point — creates `QApplication`, applies stylesheet, launches `MainWindow` |
| `window.py` | `MainWindow` — top-level window, menus, keyboard shortcuts, layout save/load, mouse-hiding timer |
| `video_wall.py` | `VideoWall(QWidget)` — recursive splitter container that holds `Player` or nested `VideoWall` children |
| `player.py` | `Player(QWidget)` — individual video cell with full playback controls; also contains module-level functions (`act`, `jog`, `volume`, `toggle`, `history`) that operate on the currently-controlled player |
| `content.py` | Background folder scanner (`FolderScanner`/`ScanDialog`) that indexes movie and layout files on first access |
| `options.py` | Loads `~/videowall_settings.json` into a frozen `_Options` dataclass; `OPTIONS` is a module-level singleton. See [Options reference](#options-reference) below for all available settings. |
| `browser.py` | Dialog for browsing and selecting saved layouts |
| `searchable_list.py` | `SearchableListBox(QComboBox)` — multi-word filtered combobox used for movie and layout selection |

### Key design patterns

**Recursive layout tree**: `VideoWall` wraps a `QSplitter` and can contain `Player` widgets or nested `VideoWall` widgets. Splitting a player in the same direction as the parent adds a sibling; splitting in the opposite direction replaces the player with a new nested `VideoWall`.

**`spec` round-trip serialization**: Both `VideoWall` and `Player` expose a `.spec` property that returns a plain dict, and accept a `spec` dict in `__init__`. Layout files are JSON with `geometry`, `state` (base64-encoded Qt window state), `spec` (the recursive tree), and `locked` (boolean). When `sparse_spec` is enabled, `Player.spec` omits keys whose values match the defaults.

**Module-level shared state in `player.py`**: `_runtime_data` dict tracks which `Player` has keyboard/menu control (`"control"`), which is the source of an in-progress swap (`"source"`), all live players (`"all players"`), which have visible UI (`"visible"`), and whether the layout is locked (`"locked"`). The module-level `act()`, `jog()`, `volume()`, etc. functions forward to `_runtime_data["control"]`. `set_locked()` and `is_locked()` manage the locked flag.

**`OPTIONS` singleton**: Loaded once at import from `~/videowall_settings.json`. All modules read from this; it is never mutated at runtime.

**Content lazy-loading**: `content.get_files()` triggers a background QThread scan the first time it's called (on first player open), showing a progress dialog. Results are cached in `_files`.

### Layout spec format

```json
{
  "geometry": "<base64>",
  "state": "<base64>",
  "locked": false,
  "spec": {
    "type": "VideoWall",
    "orientation": "horizontal",
    "items": [
      {
        "type": "Player",
        "filename": "/path/to/movie.mp4",
        "speed": 1.0,
        "volume": 0.5,
        "position": 12000,
        "mode": "loop",
        "control": true,
        "history": [],
        "at_history": null,
        "fit": true,
        "filter": ""
      }
    ],
    "sizes": [1280]
  }
}
```

`mode` is one of `"loop"`, `"next"`, `"random"`. Layout files are stored in `OPTIONS.layout_folder`; `last_layout.json` is auto-saved on exit.

## Options reference

All options live in `~/videowall_settings.json` and are loaded once at startup into the frozen `OPTIONS` singleton. The dataclass fields are declared in alphabetical order in `options.py`; keep that order when adding new options.

| Option                  | Type    | Default | Description                                                                                                                                     |
|-------------------------|---------|---------|-------------------------------------------------------------------------------------------------------------------------------------------------|
| `always_on_top`         | `bool`  | `True`  | The player window floats above normal windows even when the app is not active.                                                                  |
| `auto_update_layout`    | `bool`  | `True`  | When enabled, the open layout file is rewritten with any changes when the layout changes or the window closes.                                  |
| `default_volume`        | `float` | `1.0`   | Range `0.0`–`1.0`. Volume applied when creating a new player.                                                                                   |
| `hide_mouse_delay`      | `float` | `3.0`   | Seconds of inactivity before the mouse pointer is hidden during playback.                                                                       |
| `jog_interval`          | `int`   | `10000` | Milliseconds to seek per jog operation.                                                                                                         |
| `layout_folder`         | `Path`  |         | Directory where layout JSON files are stored.                                                                                                   |
| `lock_titlebar`         | `bool`  | `False` | When `False`, locking the layout hides the window titlebar. When `True`, the titlebar stays visible while locked. Unlocking always restores it. |
| `movie_folder`          | `Path`  |         | Root directory scanned for movie files.                                                                                                         |
| `open_last_on_startup`  | `bool`  | `True`  | When enabled, the last saved layout is loaded automatically on startup.                                                                         |
| `play_audio`            | `bool`  | `True`  | Set to `False` to disable all audio playback and hide audio controls.                                                                           |
| `pre_roll`              | `int`   | `2000`  | Milliseconds to rewind when restoring a layout, so playback starts slightly before the saved position.                                          |
| `remaining_time`        | `bool`  | `True`  | When enabled, the time display shows remaining time; otherwise shows total duration.                                                            |
| `restore_window_state`  | `bool`  | `True`  | When enabled, window geometry and state are restored from the layout file.                                                                      |
| `sparse_spec`           | `bool`  | `True`  | When enabled, `Player.spec` omits keys whose values match defaults, keeping layout files compact.                                               |
| `splitter_handle_width` | `int`   | `5`     | Width in pixels of the dividers between players. Overridden to `0` automatically when the layout is locked.                                     |
