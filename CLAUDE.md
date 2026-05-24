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
| `options.py` | Loads `~/videowall_settings.json` into a frozen `_Options` dataclass; `OPTIONS` is a module-level singleton. Includes `splitter_handle_width` (default `5` px) — the divider width used between players when unlocked. |
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
