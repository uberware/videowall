"""The main entry point."""

import argparse
import logging
import os
import sys
import time
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtMultimedia import QMediaDevices
from PySide6.QtWidgets import QApplication

from videowall.diagnostics import StallWatcher
from videowall.options import DEFAULT_QSS
from videowall.window import MainWindow

HEARTBEAT_INTERVAL = 1000
"""Milliseconds between heartbeats. The watchdog calls the wall frozen after several misses."""


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group()
    group.add_argument("-v", "--verbose", action="store_true", help="More logging.")
    group.add_argument("-q", "--quiet", action="store_true", help="Less logging.")
    parser.add_argument(
        "--diagnostics",
        metavar="DIR",
        help="Record a debug log, a pid and a heartbeat in DIR, for scripts/hang_watchdog.py to read.",
    )
    return parser.parse_args()


def start_diagnostics(folder: Path) -> tuple:
    """Record what the wall is doing, so an unattended freeze still leaves evidence.

    The freeze is random and rare enough that it cannot be reproduced on demand, so it has
    to be caught passively instead. Three things go into the folder. The log says what the
    wall was doing beforehand, on disk rather than in a console that dies with the process.
    The pid saves the watchdog guessing which interpreter is the wall. The heartbeat is a
    timestamp rewritten from the Qt event loop, which is precisely what a frozen window
    stops doing, so a watchdog outside the process can time the freeze to the second and
    sample the deadlock while it is still there to sample.

    Args:
        folder: directory to write the log, pid and heartbeat into. Created if missing.

    Returns:
        The heartbeat timer and the stall watcher. The caller has to keep both alive or Qt
        will collect them.
    """
    folder.mkdir(parents=True, exist_ok=True)
    heartbeat = folder / "heartbeat"

    handler = logging.FileHandler(folder / "videowall.log")
    handler.setFormatter(logging.Formatter("%(asctime)s.%(msecs)03d %(levelname)s %(message)s", "%H:%M:%S"))
    root = logging.getLogger()
    root.addHandler(handler)
    root.setLevel(logging.DEBUG)

    (folder / "pid").write_text(str(os.getpid()))

    def beat():
        """Stamp the heartbeat, atomically so the watchdog never reads a half-written one."""
        pending = heartbeat.with_suffix(".pending")
        pending.write_text(str(time.time()))
        os.replace(pending, heartbeat)

    timer = QTimer()
    timer.timeout.connect(beat)
    timer.start(HEARTBEAT_INTERVAL)
    beat()

    # A frozen window stops the heartbeat, but a single player that quietly stops advancing
    # leaves the rest of the wall running and the heartbeat ticking. The stall watcher is
    # what notices that one.
    watcher = StallWatcher(folder)

    # Which output the session started on, so a run that went wrong can be told apart from
    # one that did not without anyone having to remember what was plugged in at the time.
    log = logging.getLogger("videowall")
    log.info(f"Diagnostics recording to {folder}")
    log.info(f"Audio output at startup: {QMediaDevices.defaultAudioOutput().description()}")
    return timer, watcher


def main():
    """Main function to run the GUI."""
    # Get the command line overrides
    parsed_args = parse_args()

    # Set up the logger
    logger = logging.getLogger("videowall")
    if parsed_args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    elif not parsed_args.quiet:
        logging.basicConfig(level=logging.INFO)

    # Get the Qt Application
    app = QApplication(sys.argv)
    # Set the stylesheet
    app.setStyleSheet(DEFAULT_QSS)
    # Set a smaller point size
    app_font = app.font()
    app_font.setPointSize(10)
    app.setFont(app_font)

    # The heartbeat needs the event loop it is measuring, so diagnostics start once there is
    # an application to attach to. The timer is held here because Qt collects an unheld one.
    diagnostics = None
    if parsed_args.diagnostics:
        diagnostics = start_diagnostics(Path(parsed_args.diagnostics))

    # Show the window and run the app loop
    window = MainWindow()
    window.show()
    logger.info("Running main loop")
    result = app.exec()
    if diagnostics:
        diagnostics[0].stop()
    return result


if __name__ == "__main__":
    sys.exit(main())
