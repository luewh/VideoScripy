from __future__ import annotations

from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from subprocess import Popen
from threading import Thread
from typing import NotRequired, Protocol, Required, TypedDict


ROOT_DIR = Path(__file__).resolve().parent.parent


class GPUInfo(TypedDict):
    id: int
    name: str
    codecs: list[str]


class ProcAsyncReturn(TypedDict):
    returnCode: int
    stdout: bytes


class StreamInfo(TypedDict):
    index: int
    codec_type: str
    codec_name: str
    selected: bool
    language: str
    title: str


class FrameByte(TypedDict):
    pts_time: datetime
    size: int


class VideoInfo(TypedDict):
    """Video metadata stored in ``VideoScripy.vList``."""

    type: Required[str]
    path: Required[str]
    name: Required[str]
    duration: NotRequired[timedelta]
    bitRate: NotRequired[int]
    quality: NotRequired[float]
    width: NotRequired[int]
    height: NotRequired[int]
    fps: NotRequired[float]
    nbFrames: NotRequired[int]
    streams: NotRequired[list[StreamInfo]]
    fileSize: NotRequired[int]
    compressBitRate: NotRequired[float]
    compressBitRateParam: NotRequired[str]
    resizeWidth: NotRequired[int]
    resizeHeight: NotRequired[int]
    getFramesOutputPath: NotRequired[str]
    upscaleOutputPath: NotRequired[str]
    upscaleFactor: NotRequired[int | str]
    interpolateOutputPath: NotRequired[str]
    interpolateFrame: NotRequired[int]
    interpolateFps: NotRequired[float]
    frameBytePerPacket: NotRequired[list[FrameByte] | dict[str, list[float | int]]]
    frameBytePerSecond: NotRequired[list[FrameByte] | dict[str, list[float | int]]]


class VideoProcess(Enum):
    """Supported video processes and their substeps."""

    compress = "compress"
    resize = "resize"
    upscale = ["getFrames", "upscale", "frameToVideo"]
    interpolate = ["getFrames", "interpolate", "frameToVideo"]
    preview = "preview"
    frame = "frame"
    stream = "stream"


class VideoScripyContext(Protocol):
    """Shared state and cross-module methods used by implementation mixins."""

    path: str
    root_dir: Path
    vList: list[VideoInfo]
    vType: list[str]
    pType: list[str]
    aType: list[str]
    sType: list[str]
    scanType: list[str]
    folderSkip: list[str]
    COMPRESS_TOLERENCE: float
    proc: Popen[bytes] | None
    procAsync: list[Popen[bytes]]
    killed: bool
    stop_threads: bool
    EXIT_CODE_FILE_NAME: str
    h265: bool
    gpu: bool
    devices: list[GPUInfo]
    selectedDevice: GPUInfo | None
    encoder: str
    DAY_ZERO: datetime
    watch: Thread

    def _project_tool_paths(self) -> list[Path]: ...

    @staticmethod
    def _quote_command_path(path: Path) -> str: ...

    def _resolve_tool(self, name: str) -> str | None: ...

    def _asset_path(self, *parts: str | Path) -> Path: ...

    def _path(self, *parts: str | Path) -> Path: ...

    def removeEmptyFolder(self, folderName: str | Path | None = None) -> None: ...

    def noticeProcessBegin(self) -> None: ...

    def noticeProcessEnd(self) -> None: ...

    def setEncoder(self, h265: bool = True) -> None: ...

    def _getCommand(
        self, video: VideoInfo, process: str, substep: int = 0
    ) -> str | None: ...

    def _runProc(self, command: str, processName: str = "", silence: bool = False) -> bool: ...

    def _checkExitCode(self, silence: bool = False) -> bool: ...

    def _runProcAsync(self, command: str) -> None: ...

    def _runProcAsyncWait(self) -> list[ProcAsyncReturn]: ...

    def _frameWatch(self, outDir: str, total: int) -> None: ...

    def _frameWatchStart(self, outDir: str, total: int) -> None: ...

    def _frameWatchStop(self) -> None: ...

    def _getFrames(self, video: VideoInfo, process: VideoProcess) -> bool: ...

    def pre_compress(
        self, video: VideoInfo, width: int, height: int, quality: float
    ) -> bool: ...
