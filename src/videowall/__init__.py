"""External API to use VideoWall in Python."""

import os
import sys

# Qt's ffmpeg backend opens the audio output at the media file's own sample rate. On macOS a
# rate below 44.1 kHz cannot be carried over Bluetooth A2DP, so CoreAudio renegotiates the link
# down to the hands-free profile and playback drops to 16 kHz mono for the rest of the session.
# AVFoundation resamples to the output device instead, so the link stays in A2DP. This has to be
# set before Qt Multimedia is imported below.
if sys.platform == "darwin":
    os.environ.setdefault("QT_MEDIA_BACKEND", "darwin")

from .main import main
from .player import Player
from .video_wall import VideoWall

__all__ = ["main", "Player", "VideoWall"]
