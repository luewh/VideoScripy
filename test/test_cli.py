from unittest.mock import Mock, call, patch
import unittest

from VideoScripy import VideoProcess
from VideoScripyCLI import _run_process


class VideoScripyCliTests(unittest.TestCase):
    def test_gif_process_prompts_for_size_and_fps(self):
        video_scripy = Mock()
        with (
            patch("VideoScripyCLI._prompt_int", side_effect=[-1, -1]) as prompt_int,
            patch("VideoScripyCLI._prompt_float", return_value=10.0) as prompt_float,
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
            ],
        )
        prompt_float.assert_called_once_with("GIF FPS", 10.0, minimum=0.1)
        video_scripy.convertToGif.assert_called_once_with(
            setWidth=-1,
            setHeight=-1,
            fps=10.0,
        )


if __name__ == "__main__":
    unittest.main()