# Changes
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.3.0] - 2026-08-19

### Added
* Menu command to lock/unlock the layout
* `lock_titlebar` option
* [CLAUDE.md](CLAUDE.md) Claude code integration document
* Menu commands to step to the next, previous, or a random layout
* Automated test suite run with `pytest`
* GitHub workflow to publish to PyPI
* GitHub workflow running the test suite, `ruff` and `bandit` on every push and pull request

### Fixed
* Publishing to PyPI is triggered by a version bump reaching `main`, and no longer by a merged pull request
* Player filter is not case-sensitive
* Audio device switches to 16 kHz mono on macOS
* Keyboard shortcuts stop working when the movie filter keeps focus
* Opening a new layout while paused starts playback and leaves the menu out of sync

## [1.2.0] - 2025-12-18

### Added
* Players have a persistent filter for the movie list
* Option to save sparse spec files without default values
* Option not to play audio at all
* Command line parsing to adjust verbosity

### Changed
* New players show the full interface by default
* Mouse hiding now works on a timer
* Auto complete separates words

### Fixed
* Possible crash trying to hide the mouse pointer

## [1.1.0] - 2025-11-21

### Added
* Option to have player fill vs pad the content

## [1.0.0] - 2025-08-24

Initial public release
