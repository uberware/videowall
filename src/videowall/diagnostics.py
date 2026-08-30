"""Watch the wall for players that quietly stop advancing.

A player that fails to wrap at the end of its movie leaves no trace of its own. Loop mode
is handled inside the backend by ``setLoops``, not by ``end_action``, so nothing in this
package runs when a loop succeeds and nothing runs when one fails either. The wall simply
has a still frame in it, and the log for that stretch is empty.

This closes that gap by polling what the backend reports. A player that says it is playing
while its position stands still has stalled, whatever the cause, and a player standing
still at the very end of its movie is a loop that did not come back round. A player that is
not playing at all while it holds a movie has failed too: it either never started or gave
up, and reading that as "stopped on purpose" is what let one go unrecorded. All three are
logged, and all three drop a marker for ``scripts/hang_watchdog.py`` to find, so the process
is sampled while the stall is still there rather than after it has cleared.

Only ``--diagnostics`` builds any of this. Nothing here runs in a normal session.
"""

import logging
import time
import typing
from pathlib import Path

from PySide6.QtCore import QObject, QTimer
from PySide6.QtMultimedia import QMediaPlayer

from videowall.player import _runtime_data

logger = logging.getLogger("videowall")

POLL_INTERVAL = 2000
"""Milliseconds between polls. Slow enough to cost nothing, fast enough to catch a stall."""

STALL_SECONDS = 6.0
"""How long a playing position may stand still before it counts as stalled.

Well past any ordinary buffering hiccup off an external volume, and well short of the
minutes a stalled player would otherwise sit there unnoticed.
"""

END_TOLERANCE = 1500
"""Milliseconds from the end within which a stall is read as a loop that failed to wrap."""


def output_device(item) -> str:
    """Name the output a player is feeding, or say it has none.

    Whether these faults follow the Bluetooth headphones around is an open question and not
    one anybody should have to answer from memory, so every stall records the device it
    happened on and the answer accumulates on its own.

    Args:
        item: the Player to describe.

    Returns:
        The device description, or a note that this player has no audio output.
    """
    audio = getattr(item, "audio", None)
    return audio.device().description() if audio else "no audio output"


class StallWatcher(QObject):
    """Poll every player and report the ones that have stopped advancing."""

    def __init__(self, folder: Path, parent: typing.Optional[QObject] = None):
        """Start polling.

        Args:
            folder: the diagnostics directory, where stall markers are written.
            parent: optional Qt parent.
        """
        super().__init__(parent)
        self.folder = folder
        self.seen: dict[int, tuple] = {}
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.check)
        self.timer.start(POLL_INTERVAL)

    def check(self, now: typing.Optional[float] = None) -> list:
        """Compare every player against where it was, and report the ones that have not moved.

        Args:
            now: the current time in seconds, for tests that need to control the clock.

        Returns:
            A list of one description per player found stalled on this pass. A player is
            reported once per stall, not once per poll, so a long stall stays one line.
        """
        now = time.monotonic() if now is None else now
        stalled = []
        live = set()

        for item in list(_runtime_data["all players"]):
            key = id(item)
            live.add(key)
            state = item.player.playbackState()
            playing = state == QMediaPlayer.PlaybackState.PlayingState
            # Not playing is only a fault when there is a movie to play. An empty cell is
            # stopped because it holds nothing, and a paused wall is standing still because
            # the user said so, which is why only StoppedState counts here.
            stopped = state == QMediaPlayer.PlaybackState.StoppedState and bool(item.filename)
            position = item.player.position()
            was_position, since, reported = self.seen.get(key, (position, now, False))

            if not (playing or stopped) or position != was_position:
                # Moving, or deliberately stopped. Either way this is not a stall.
                if reported:
                    logger.warning(f"{item} Started advancing again at {position}")
                self.seen[key] = (position, now, False)
                continue

            if not reported and now - since >= STALL_SECONDS:
                duration = item.player.duration()
                at_end = duration and position >= duration - END_TOLERANCE
                if not playing:
                    kind = "NOT PLAYING"
                elif at_end:
                    kind = "LOOP DID NOT WRAP"
                else:
                    kind = "STALLED"
                report = (
                    f"{item} {kind}: {'playing but stuck' if playing else 'holding a movie but stopped'} "
                    f"at {position} of {duration} for {now - since:.1f}s, "
                    f"playback state {state.name}, media status {item.player.mediaStatus().name}, "
                    f"out of {output_device(item)}, file {item.filename}"
                )
                logger.warning(report)
                stalled.append(report)
                self.seen[key] = (position, since, True)
            else:
                self.seen[key] = (position, since, reported)

        for key in set(self.seen) - live:
            del self.seen[key]

        if stalled:
            self.mark(stalled)
        return stalled

    def mark(self, stalled: list) -> None:
        """Leave a marker the watchdog can see, so it samples while the stall is still live.

        Sampling a stall after it has cleared says nothing, and the whole point of catching
        one is to look at the threads underneath it while they are still stuck.
        """
        try:
            (self.folder / "stall").write_text("\n".join(stalled) + "\n")
        except OSError as error:
            logger.warning(f"Could not write the stall marker: {error}")
