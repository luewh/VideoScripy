"""Interactive command-line interface for VideoScripy."""

from __future__ import annotations

import argparse
from math import isfinite
from pathlib import Path
from typing import TYPE_CHECKING, Sequence

if TYPE_CHECKING:
    from VideoScripy import VideoProcess, VideoScripy


def _prompt_int(
    message: str,
    default: int,
    *,
    choices: Sequence[int] | None = None,
    minimum: int | None = None,
    allow_minus_one: bool = False,
) -> int:
    while True:
        entered = input(f"{message} [{default}]: ").strip()
        if not entered:
            return default

        try:
            value = int(entered)
        except ValueError:
            print(f"{entered!r} is not an integer.")
            continue

        if choices is not None and value not in choices:
            print(f"Choose one of: {', '.join(map(str, choices))}.")
            continue
        if minimum is not None and value < minimum:
            if not (allow_minus_one and value == -1):
                print(f"Enter a value of at least {minimum}.")
                continue
        return value


def _prompt_float(
    message: str,
    default: float,
    *,
    minimum: float = 0.0,
) -> float:
    while True:
        entered = input(f"{message} [{default}]: ").strip()
        if not entered:
            return default

        try:
            value = float(entered)
        except ValueError:
            print(f"{entered!r} is not a number.")
            continue

        if not isfinite(value) or value < minimum:
            print(f"Enter a value of at least {minimum}.")
            continue
        return value


def _select_process(process_type: type[VideoProcess]) -> VideoProcess:
    processes = list(process_type)
    print("\nAvailable processes:")
    for index, process in enumerate(processes, start=1):
        print(f"{index}. {process.name}")

    selection = _prompt_int(
        "Select a process",
        default=1,
        choices=range(1, len(processes) + 1),
    )
    return processes[selection - 1]


def _run_process(
    video_scripy: VideoScripy,
    process: VideoProcess,
    process_type: type[VideoProcess],
) -> None:
    if process is process_type.compress:
        quality = _prompt_float("Quality", 3.0, minimum=0.1)
        video_scripy.compress(quality=quality)
    elif process is process_type.resize:
        width = _prompt_int("Width", 1920, minimum=1, allow_minus_one=True)
        height = _prompt_int("Height (-1 keeps the aspect ratio)", -1, minimum=1, allow_minus_one=True)
        quality = _prompt_float("Quality", 3.0, minimum=0.1)
        video_scripy.resize(setWidth=width, setHeight=height, quality=quality)
    elif process is process_type.upscale:
        factor = _prompt_int("Upscale factor", 2, choices=[2, 3, 4])
        quality = _prompt_float("Quality", 3.0, minimum=0.1)
        video_scripy.upscale(upscaleFactor=factor, quality=quality)
    elif process is process_type.interpolate:
        fps = _prompt_float("Target FPS", 60.0, minimum=0.1)
        quality = _prompt_float("Quality", 3.0, minimum=0.1)
        video_scripy.interpolate(fpsInterp=fps, quality=quality)
    elif process is process_type.preview:
        width = _prompt_int("Grid columns", 3, minimum=1)
        height = _prompt_int("Grid rows", 2, minimum=1)
        video_scripy.preview(gridWidth=width, gridHeight=height)
    elif process is process_type.frame:
        video_scripy.frame()
    elif process is process_type.stream:
        video_scripy.stream()


def run(
    argv: Sequence[str] | None = None,
    *,
    video_scripy_type: type[VideoScripy] | None = None,
    process_type: type[VideoProcess] | None = None,
) -> None:
    parser = argparse.ArgumentParser(
        description="Scan and process videos from the command line."
    )
    parser.add_argument(
        "--path",
        type=Path,
        default=Path.cwd(),
        help="folder to scan (default: current folder)",
    )
    parser.add_argument(
        "--depth",
        type=int,
        default=0,
        help="maximum subfolder depth; use -1 for unlimited (default: 0)",
    )
    args = parser.parse_args(argv)

    if args.depth < -1:
        parser.error("--depth must be -1 or greater")
    if not args.path.is_dir():
        parser.error(f"folder does not exist: {args.path}")

    if video_scripy_type is None or process_type is None:
        from VideoScripy import VideoProcess, VideoScripy

        if video_scripy_type is None:
            video_scripy_type = VideoScripy
        if process_type is None:
            process_type = VideoProcess

    video_scripy = video_scripy_type()
    if not video_scripy.setPath(str(args.path)):
        parser.error(f"cannot use folder: {args.path}")
    if not video_scripy.getVideo(folderDepthLimit=args.depth):
        return
    video_scripy.getVideoInfo()

    if not video_scripy.vList:
        print(f"No supported media files found in {video_scripy.path}.")
        return

    print(f"\nFound {len(video_scripy.vList)} media file(s):")
    for video in video_scripy.vList:
        print(f"  {video['name']}")

    process = _select_process(process_type)
    _run_process(video_scripy, process, process_type)


if __name__ == "__main__":
    from sys import path

    path.insert(0, str(Path(__file__).resolve().parent))
    from VideoScripy import VideoProcess, VideoScripy

    run(video_scripy_type=VideoScripy, process_type=VideoProcess)
