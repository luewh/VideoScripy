import os
from threading import Lock

from VideoScripy import (
    GIF_MAX_COLORS,
    GIF_MIN_RECOMMENDED_COLORS,
    StreamInfo,
    VideoInfo as VideoInfoBase,
    VideoProcess,
    VideoScripy,
    colorAnsi,
)


IP = "localhost"
PORT = "8848"
PORTABLE_MODE = os.environ.get("VIDEOSCRIPY_PORTABLE") == "1"


class VideoInfo(VideoInfoBase):
    selected: bool


vs = VideoScripy()
process_lock = Lock()
allVideoList: list[VideoInfo] = []
hasFrameResult: list[int] = []
processes = [process.name for process in VideoProcess]
videoSizesDict = [
    {"label": "240p/SD", "width": 426, "height": 240},
    {"label": "360p/SD", "width": 640, "height": 360},
    {"label": "480p/SD", "width": 854, "height": 480},
    {"label": "720p/HD", "width": 1280, "height": 720},
    {"label": "1080p/FHD", "width": 1920, "height": 1080},
    {"label": "1440p/2K", "width": 2560, "height": 1440},
    {"label": "2160p/4K", "width": 3840, "height": 2160},
    {"label": "4320p/8K", "width": 7680, "height": 4320},
]
videoQualityDict = [
    {"label": "low : 1", "value": 1},
    {"label": "best : 3", "value": 3},
    {"label": "ultra : 6", "value": 6},
]
upscaleFactor = [2, 3, 4]


def _paletteSteps(minimum: int, maximum: int) -> list[int]:
    """Return every power of two from ``minimum`` up to ``maximum``."""
    steps = [minimum]
    while steps[-1] * 2 <= maximum:
        steps.append(steps[-1] * 2)
    return steps


# standard GIF palette sizes, from the recommended minimum up to the maximum
gifColorOptions = _paletteSteps(GIF_MIN_RECOMMENDED_COLORS, GIF_MAX_COLORS)
videoItemColor = {True: "info", False: "dark"}
videoSortBy = [
    "quality",
    "name",
    "width", "height", "w x h",
    "fps",
    "duration",
    "bitRate",
    "fileSize",
]
langDict = [
    {"label": "Undefined | undifined", "value": "und"},
    {"label": "English | english", "value": "eng"},
    {"label": "Chinese | 中文", "value": "zho"},
    {"label": "Japanese | 日本語", "value": "jpn"},
    {"label": "Korean | 한국어", "value": "kor"},
    {"label": "Hindi | हिन्दी", "value": "hin"},
    {"label": "Spanish | español", "value": "spa"},
    {"label": "French | français", "value": "fra"},
    {"label": "Arabic | العربية", "value": "ara"},
    {"label": "Bengali | বাংলা", "value": "ben"},
    {"label": "Portuguese | português", "value": "por"},
    {"label": "Urdu | اُردُو", "value": "urd"},
    {"label": "Dutch | nederlands", "value": "nld"},
    {"label": "German | deutsch", "value": "deu"},
]
_encoder_info = (
    ("h265", "H.265", "libx265", "hevc_nvenc", "H.265/HEVC"),
    ("h264", "H.264", "libx264", "h264_nvenc", "H.264/AVC"),
    ("av1", "AV1", "libaom-av1", "av1_nvenc", "AV1"),
)


def getEncoderOptions(device_id: int | None) -> list[dict[str, str]]:
    """Return codecs available on the selected CPU or GPU device."""
    device = next((item for item in vs.devices if item["id"] == device_id), None)
    if device is None:
        return []

    encoder_index = 2 if device["id"] == -1 else 3
    available_encoders = vs.availableEncoders
    return [
        {"label": label, "value": codec}
        for codec, label, cpu_encoder, gpu_encoder, device_codec in _encoder_info
        if device_codec in device["codecs"]
        and (cpu_encoder if encoder_index == 2 else gpu_encoder)
        in available_encoders
    ]


encoderDict = getEncoderOptions(
    vs.settedDevice["id"] if vs.settedDevice is not None else None
)
