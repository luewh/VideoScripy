"""Public API facade for the VideoScripy application."""

from __future__ import annotations

import subprocess
from datetime import datetime
from pathlib import Path

from videoscripy._core import _CoreMixin
from videoscripy._operations import _OperationsMixin
from videoscripy._processing import _ProcessingMixin
from videoscripy._types import (
    GIF_DEFAULT_DITHER,
    GIF_DEFAULT_MAX_COLORS,
    GIF_DITHER_SCORES,
    GIF_DITHERS,
    GIF_MAX_COLORS,
    GIF_MIN_RECOMMENDED_COLORS,
    ROOT_DIR,
    FrameByte,
    GIFDitherScore,
    GPUInfo,
    ProcAsyncReturn,
    StreamInfo,
    VideoInfo,
    VideoProcess,
)
from videoscripy._utilities import colorAnsi, printC


__all__ = [
    "colorAnsi",
    "printC",
    "GPUInfo",
    "ProcAsyncReturn",
    "StreamInfo",
    "FrameByte",
    "VideoInfo",
    "VideoProcess",
    "VideoScripy",
    "GIFDitherScore",
    "GIF_DITHERS",
    "GIF_DITHER_SCORES",
    "GIF_DEFAULT_DITHER",
    "GIF_DEFAULT_MAX_COLORS",
    "GIF_MIN_RECOMMENDED_COLORS",
    "GIF_MAX_COLORS",
]


class VideoScripy(_OperationsMixin, _ProcessingMixin, _CoreMixin):
    """Manage video discovery, metadata, and processing operations."""

    def __init__(self) -> None:
        self.path = str(Path.cwd().resolve())
        self.root_dir = ROOT_DIR
        self._add_project_tools_to_path()

        self.vList: list[VideoInfo] = []
        self.vType = ["mp4", "mkv"]
        # Real-ESRGAN support format
        self.pType = ["png", "jpg", "jpeg", "webp"]
        self.aType = ["mp3", "m4a", "aac", "wav"]
        self.sType = ["smi", "srt"]
        self.scanType = self.vType + self.pType + self.aType + self.sType
        self.folderSkip = [p.name for p in VideoProcess]
        self.COMPRESS_TOLERENCE = 0.1

        self.proc: subprocess.Popen[bytes] | None = None
        self.killed = False
        self.stop_threads = False
        self.procAsync: list[subprocess.Popen[bytes]] = []

        self.EXIT_CODE_FILE_NAME = "exitCode.txt"

        self.videoCodec = "h265"
        self.gpu = True
        self.devices: list[GPUInfo] = [
            {
                "id": -1,
                "name": "CPU",
                "codecs": [],
            }
        ]
        self.availableEncoders: set[str] = set()
        self.getEncoders()
        self.settedDevice: GPUInfo | None = None
        self.setDevice()

        self.checkTools()

        self.DAY_ZERO = datetime(2000, 1, 1)


def _run_manual_debug() -> None:
    """Initialize and scan the current folder for manual operation debugging."""
    video_scripy = VideoScripy()
    video_scripy.getVideo()
    video_scripy.getVideoInfo()

    for video in video_scripy.vList:
        print(video["name"])
        # print()

    # Uncomment an operation to debug it against the scanned media:
    # video_scripy.compress(0.3)
    # video_scripy.resize(setWidth=1920, setHeight=-1)
    # video_scripy.upscale(upscaleFactor=2)
    # video_scripy.interpolate(fpsInterp=60.0)
    # video_scripy.preview()
    # video_scripy.frame()
    # video_scripy.stream()


if __name__ == "__main__":
    _run_manual_debug()
    pass
