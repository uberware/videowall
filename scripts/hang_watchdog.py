#!/usr/bin/env python3
"""Watch a running Video Wall and sample it the moment its window freezes.

The freeze is random, sometimes hours away and sometimes absent, so it cannot be
reproduced to order. This watches for it instead. ``videowall --diagnostics DIR``
stamps a heartbeat from the Qt event loop once a second; a frozen main thread stops
stamping it, and that is the same main thread the frozen window belongs to. When the
stamp goes stale this samples the process, which is the one artifact that says whether
the main thread is blocked inside Apple's AudioQueue bridge or somewhere else entirely.

It also catches the milder fault, where one player stops advancing while the rest of the
wall carries on and the heartbeat keeps ticking. The wall drops a "stall" marker for that,
and a sample taken then shows the threads under a single stuck player.

Sampling has to happen while the deadlock is still standing, which is why this runs
unattended rather than waiting for someone to notice and run it by hand.

Usage:
    videowall --diagnostics ~/vw-diag &
    python3 scripts/hang_watchdog.py ~/vw-diag

    python3 scripts/hang_watchdog.py ~/vw-diag --now    # sample immediately, frozen or not
"""

import argparse
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

POLL_SECONDS = 1.0
DEFAULT_STALE = 5.0
SAMPLE_SECONDS = 10


def read_pid(folder: Path) -> int:
    """Return the pid the wall recorded, or exit saying how to get one."""
    pid_file = folder / "pid"
    if not pid_file.exists():
        sys.exit(f"No pid in {folder}. Start the wall with: videowall --diagnostics {folder}")
    pid = int(pid_file.read_text().strip())
    if subprocess.run(["kill", "-0", str(pid)], capture_output=True).returncode != 0:
        sys.exit(f"Process {pid} is gone. If it crashed, the report is in ~/Library/Logs/DiagnosticReports.")
    return pid


def heartbeat_age(folder: Path) -> float:
    """Return seconds since the event loop last stamped the heartbeat."""
    try:
        return time.time() - float((folder / "heartbeat").read_text().strip())
    except (OSError, ValueError):
        return 0.0


def analyse(sample_text: str, frozen: bool) -> str:
    """Read the sample for the one thing it is being taken to settle.

    For a frozen window the question is the main thread: blocked in AudioQueue means the
    freeze and the deadlock in the crash report are one fault, blocked anywhere else means
    they are two and the audio theory is wrong.

    For a single stalled player the main thread is expected to be idle, because the rest of
    the wall is still running. There the number to read is how many threads are sitting in
    the AudioQueue bridge, and which movie the log names alongside it.
    """
    lines = sample_text.splitlines()
    main, inside = [], False
    for line in lines:
        if "com.apple.main-thread" in line or "Main Thread" in line:
            inside = True
        elif inside and line.strip().startswith("Thread_"):
            break
        if inside:
            main.append(line)

    blocked = [x for x in main if any(k in x for k in ("AudioQueue", "wait_for_ownership", "dispatch_sync"))]
    total = sum("AudioQueueXPC_Bridge" in x for x in lines)
    report = [f"Threads in the AudioQueue XPC bridge: {total}"]
    if blocked:
        report.append(">>> MAIN THREAD IS BLOCKED IN AUDIO.")
        report.append("    The frozen window and the AudioQueue deadlock are the same fault.")
        report += [f"      {x.strip()}" for x in blocked[:6]]
    elif not main:
        report.append(">>> Could not find the main thread in the sample; read it by hand.")
    elif frozen:
        report.append(">>> Main thread is NOT in the audio path, so the freeze is something else.")
        report.append("    Read the main thread in the sample to see what it is waiting on.")
    else:
        report.append(">>> Main thread is idle, which is expected while the rest of the wall runs.")
        report.append("    Read the bridge count above and the stalled movie named below.")
    return "\n".join(report)


def capture(pid: int, folder: Path, why: str) -> None:
    """Sample the process and write the sample, the verdict and the log tail side by side."""
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out = folder / f"hang-{stamp}.sample.txt"
    print(f"\n[{stamp}] {why} — sampling pid {pid} for {SAMPLE_SECONDS}s...", flush=True)
    subprocess.run(["sample", str(pid), str(SAMPLE_SECONDS), "-file", str(out)], capture_output=True)

    if not out.exists():
        print(f"  sample produced nothing. Try: sudo sample {pid} {SAMPLE_SECONDS}")
        return

    verdict = analyse(out.read_text(errors="replace"), frozen="silent" in why)
    print(verdict, flush=True)

    log = folder / "videowall.log"
    tail = log.read_text(errors="replace").splitlines()[-40:] if log.exists() else []
    (folder / f"hang-{stamp}.verdict.txt").write_text(
        f"{why}\n\n{verdict}\n\nLast 40 log lines:\n" + "\n".join(tail) + "\n"
    )
    print(f"  sample:  {out}")
    print(f"  verdict: {folder / f'hang-{stamp}.verdict.txt'}", flush=True)


def main() -> None:
    """Poll the heartbeat and capture the first freeze, then keep watching for the next."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path, help="The --diagnostics directory the wall is writing to.")
    parser.add_argument("--stale", type=float, default=DEFAULT_STALE, help="Seconds of silence that means frozen.")
    parser.add_argument("--now", action="store_true", help="Sample straight away, frozen or not.")
    args = parser.parse_args()

    pid = read_pid(args.folder)
    if args.now:
        capture(pid, args.folder, "Sampled on request")
        return

    print(f"Watching pid {pid} via {args.folder}. A freeze of over {args.stale}s is captured automatically.")
    print("A single player that stops advancing is captured too. Ctrl-C to stop.", flush=True)
    stall = args.folder / "stall"
    stall.unlink(missing_ok=True)
    frozen = False
    while True:
        time.sleep(POLL_SECONDS)
        if subprocess.run(["kill", "-0", str(pid)], capture_output=True).returncode != 0:
            print("\nThe wall exited. If it crashed, check ~/Library/Logs/DiagnosticReports.")
            return

        # A stalled player is sampled first: the whole wall is still responsive, so this is
        # the best possible look at a single wedged player before it clears or spreads.
        if stall.exists():
            why = stall.read_text(errors="replace").strip()
            stall.unlink(missing_ok=True)
            capture(pid, args.folder, f"A player stopped advancing\n{why}")

        age = heartbeat_age(args.folder)
        if age > args.stale and not frozen:
            frozen = True
            capture(pid, args.folder, f"Event loop silent for {age:.1f}s")
        elif age <= args.stale and frozen:
            frozen = False
            print("  ...the wall came back. Still watching.", flush=True)


if __name__ == "__main__":
    main()
