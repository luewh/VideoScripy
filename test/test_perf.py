"""Performance benchmark of the GIF dithering modes.

Converts ``demo2.mp4`` with fixed 480x854 / 10 FPS / 256 colors through the
real ``convertToGif`` pipeline once per mode of ``GIF_DITHERS``, records the
output size and the conversion time, and re-evaluates the compression/speed
scores published in ``GIF_DITHER_SCORES``.

A full pass converts the source nine times, which takes about five minutes,
so it is opt-in::

    $env:VIDEOSCRIPY_PERF=1; python.exe -m unittest discover -s test -p test_perf.py -v

The measured scores may differ from the published ones with hardware, source
content and disk speed. ``VIDEOSCRIPY_PERF_TOLERANCE`` sets how many points
of difference are accepted (default 3).
"""

from __future__ import annotations

import os
import time
import unittest
from dataclasses import dataclass
from pathlib import Path
from shutil import rmtree
from tempfile import mkdtemp
from unittest.mock import patch

from PIL import Image

from VideoScripy import (
    GIF_DITHER_SCORES,
    GIF_DITHERS,
    VideoProcess,
    VideoScripy,
)

ROOT_DIR = Path(__file__).resolve().parents[1]
DEMO_VIDEO = ROOT_DIR / "demo2.mp4"
GIF_WIDTH = 480
GIF_HEIGHT = 854
GIF_FPS = 10.0
GIF_COLORS = 256
PERF_ENV = "VIDEOSCRIPY_PERF"
TOLERANCE_ENV = "VIDEOSCRIPY_PERF_TOLERANCE"
DEFAULT_TOLERANCE = 3


@dataclass
class Measurement:
    """One dither mode run on the real pipeline."""

    dither: str
    size: int
    seconds: float
    width: int
    height: int
    frameDuration: int | None
    compression: int = 0
    speed: int = 0


def score(value: float, best: float) -> int:
    """Map a measurement to 1-10 where the best measurement scores 10."""
    return max(1, min(10, round(10 * best / value)))


def run_benchmark() -> tuple[list[Measurement], Path]:
    """Convert the demo video once per dither mode and score the results."""
    output_dir = Path(mkdtemp(prefix="videoscripy_perf_"))
    try:
        video_scripy = VideoScripy()
        video_scripy.setPath(str(output_dir))
        video_scripy.vList = [
            {
                "type": DEMO_VIDEO.suffix.lstrip(".").lower(),
                "path": str(DEMO_VIDEO),
                "name": DEMO_VIDEO.name,
            }
        ]
        video_scripy.getVideoInfo()
        if not video_scripy.vList:
            raise RuntimeError(f'FFprobe cannot read "{DEMO_VIDEO}"')

        gif_path = output_dir / VideoProcess.gif.name / f"{DEMO_VIDEO.stem}.gif"
        measurements: list[Measurement] = []
        # the notification sounds would otherwise add their playback time to the measurement
        with (
            patch.object(video_scripy, "noticeProcessBegin"),
            patch.object(video_scripy, "noticeProcessEnd"),
        ):
            for dither in GIF_DITHERS:
                started = time.perf_counter()
                video_scripy.convertToGif(
                    GIF_WIDTH,
                    GIF_HEIGHT,
                    GIF_FPS,
                    GIF_COLORS,
                    dither,
                )
                seconds = time.perf_counter() - started

                if not gif_path.is_file():
                    raise RuntimeError(f'GIF conversion failed for dither "{dither}"')
                with Image.open(gif_path) as image:
                    width, height = image.size
                    frame_duration = image.info.get("duration")
                measurements.append(
                    Measurement(
                        dither=dither,
                        size=gif_path.stat().st_size,
                        seconds=seconds,
                        width=width,
                        height=height,
                        frameDuration=frame_duration,
                    )
                )
    except BaseException:
        rmtree(output_dir, ignore_errors=True)
        raise

    smallest = min(measurement.size for measurement in measurements)
    fastest = min(measurement.seconds for measurement in measurements)
    for measurement in measurements:
        measurement.compression = score(measurement.size, smallest)
        measurement.speed = score(measurement.seconds, fastest)
    return measurements, output_dir


def format_report(measurements: list[Measurement]) -> str:
    """Render the measurements and the re-evaluated scores as aligned tables."""
    ordered = sorted(
        measurements,
        key=lambda measurement: (
            -measurement.compression,
            -measurement.speed,
            measurement.dither,
        ),
    )

    header = ("dither", "size", "time", "compression", "speed", "published")
    # numbers are right aligned, only the dither name stays left aligned
    alignments = ("left", "right", "right", "right", "right", "right")
    rows = [
        (
            measurement.dither,
            f"{measurement.size / 1e6:.2f} MB",
            f"{measurement.seconds:.2f} s",
            f"{measurement.compression}/10",
            f"{measurement.speed}/10",
            f"{GIF_DITHER_SCORES[measurement.dither]['compression']}/"
            f"{GIF_DITHER_SCORES[measurement.dither]['speed']}",
        )
        for measurement in ordered
    ]
    widths = [
        max(len(row[column]) for row in (header, *rows))
        for column in range(len(header))
    ]

    def render(row: tuple[str, ...]) -> str:
        return "  ".join(
            cell.ljust(width) if alignment == "left" else cell.rjust(width)
            for cell, width, alignment in zip(row, widths, alignments)
        )

    lines = [
        f"GIF dither benchmark: {DEMO_VIDEO.name}, "
        f"{GIF_WIDTH}x{GIF_HEIGHT}, {GIF_FPS:g} fps, {GIF_COLORS} colors",
        "sorted by compression, then speed (10 = best)",
        "",
        render(header),
        "-" * (sum(widths) + 2 * (len(widths) - 1)),
        *(render(row) for row in rows),
        "",
        "published = compression/speed already stored in GIF_DITHER_SCORES",
        "",
        "GIF_DITHER_SCORES = {",
    ]
    for measurement in ordered:
        lines.append(
            f'    "{measurement.dither}": '
            f'{{"compression": {measurement.compression}, "speed": {measurement.speed}}},'
        )
    lines.append("}")
    return "\n".join(lines)


@unittest.skipUnless(
    os.environ.get(PERF_ENV),
    f"set {PERF_ENV}=1 to run the GIF dither benchmark",
)
class GifDitherPerformanceTests(unittest.TestCase):
    measurements: list[Measurement]

    @classmethod
    def setUpClass(cls):
        if not DEMO_VIDEO.is_file():
            raise unittest.SkipTest(f'"{DEMO_VIDEO}" is required')
        cls.measurements, output_dir = run_benchmark()
        cls.addClassCleanup(rmtree, output_dir, ignore_errors=True)
        print()
        print(format_report(cls.measurements))
        print()

    def test_every_dither_produces_the_requested_gif(self):
        self.assertEqual(
            [measurement.dither for measurement in self.measurements],
            list(GIF_DITHERS),
        )
        for measurement in self.measurements:
            with self.subTest(dither=measurement.dither):
                self.assertGreater(measurement.size, 0)
                self.assertEqual(
                    (measurement.width, measurement.height),
                    (GIF_WIDTH, GIF_HEIGHT),
                )
                self.assertEqual(measurement.frameDuration, 1000 / GIF_FPS)

    def test_none_dither_produces_the_smallest_file(self):
        smallest = min(self.measurements, key=lambda measurement: measurement.size)
        self.assertEqual(smallest.dither, "none")
        self.assertEqual(smallest.compression, 10)

    def test_measured_scores_match_the_published_scores(self):
        tolerance = int(os.environ.get(TOLERANCE_ENV, DEFAULT_TOLERANCE))
        report = format_report(self.measurements)
        for measurement in self.measurements:
            published = GIF_DITHER_SCORES[measurement.dither]
            with self.subTest(dither=measurement.dither):
                self.assertLessEqual(
                    abs(measurement.compression - published["compression"]),
                    tolerance,
                    report,
                )
                self.assertLessEqual(
                    abs(measurement.speed - published["speed"]),
                    tolerance,
                    report,
                )
