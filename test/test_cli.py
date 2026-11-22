from unittest.mock import Mock, call, patch
import unittest

from VideoScripy import GIF_DEFAULT_DITHER, GIF_DEFAULT_MAX_COLORS, GIF_DITHERS, VideoProcess
from VideoScripyCLI import _run_process


class VideoScripyCliTests(unittest.TestCase):
    def test_gif_process_prompts_for_size_fps_and_palette(self):
        video_scripy = Mock()
        with (
            patch(
                "VideoScripyCLI._prompt_int",
                side_effect=[-1, -1, 64],
            ) as prompt_int,
            patch("VideoScripyCLI._prompt_float", return_value=10.0) as prompt_float,
            patch("VideoScripyCLI._prompt_str", return_value="bayer") as prompt_str,
        ):
            _run_process(video_scripy, VideoProcess.gif, VideoProcess)

        self.assertEqual(
            prompt_int.call_args_list,
            [
                call("GIF width", -1, minimum=1, allow_minus_one=True),
                call(
                    "GIF height (-1 keeps the aspect ratio)",
                    -1,
                    minimum=1,
                    allow_minus_one=True,
                ),
                call(
                    "GIF max colors (lower means a smaller file)",
                    GIF_DEFAULT_MAX_COLORS,
                    minimum=2,
                ),
            ],
        )
        prompt_float.assert_called_once_with("GIF FPS", 10.0, minimum=0.1)
        prompt_str.assert_called_once_with(
            "GIF dither ('none' gives the smallest file)",
            GIF_DEFAULT_DITHER,
            choices=GIF_DITHERS,
        )
        video_scripy.convertToGif.assert_called_once_with(
            setWidth=-1,
            setHeight=-1,
            fps=10.0,
            maxColors=64,
            dither="bayer",
        )


if __name__ == "__main__":
    unittest.main()