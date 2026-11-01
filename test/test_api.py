import io
import json
import os
import re
import socket
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timedelta
from pathlib import Path
from threading import Thread
from types import SimpleNamespace
from unittest.mock import Mock, call, patch

from PIL import Image

import VideoScripy as public_api
from VideoScripy import VideoScripy


class VideoScripyApiTests(unittest.TestCase):
    PUBLIC_METHODS = {
        "checkTools",
        "checkGPUs",
        "selectDevice",
        "removeEmptyFolder",
        "noticeProcessBegin",
        "noticeProcessEnd",
        "setPath",
        "getVideo",
        "getVideoInfo",
        "setEncoder",
        "killProc",
        "pre_compress",
        "compress",
        "resize",
        "upscale",
        "interpolate",
        "preview",
        "frame",
        "stream",
    }

    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.root = Path(self.temporary_directory.name)
        self.video_scripy = VideoScripy.__new__(VideoScripy)
        self.video_scripy.path = str(self.root)
        self.video_scripy.root_dir = self.root
        self.video_scripy.vList = []
        self.video_scripy.vType = ["mp4", "mkv"]
        self.video_scripy.pType = ["png", "jpg", "jpeg", "webp"]
        self.video_scripy.aType = ["mp3", "m4a", "aac", "wav"]
        self.video_scripy.sType = ["smi", "srt"]
        self.video_scripy.scanType = (
            self.video_scripy.vType
            + self.video_scripy.pType
            + self.video_scripy.aType
            + self.video_scripy.sType
        )
        self.video_scripy.folderSkip = []
        self.video_scripy.COMPRESS_TOLERENCE = 0.1
        self.video_scripy.proc = None
        self.video_scripy.procAsync = []
        self.video_scripy.killed = False
        self.video_scripy.stop_threads = False
        self.video_scripy.EXIT_CODE_FILE_NAME = "exitCode.txt"
        self.video_scripy.h265 = False
        self.video_scripy.gpu = False
        self.video_scripy.devices = [
            {
                "id": -1,
                "name": "CPU",
                "codecs": ["H.264/AVC", "H.265/HEVC"],
            }
        ]
        self.video_scripy.selectedDevice = self.video_scripy.devices[0]
        self.video_scripy.DAY_ZERO = datetime(2000, 1, 1)

    def make_probe_result(self, width=266, height=200):
        return {
            "streams": [
                {
                    "index": 0,
                    "codec_type": "video",
                    "codec_name": "hevc",
                    "width": width,
                    "height": height,
                    "r_frame_rate": "25/1",
                    "duration": "10.240000",
                    "bit_rate": "144120",
                    "nb_frames": "256",
                }
            ],
            "format": {
                "duration": "10.240000",
                "size": "352691",
                "bit_rate": "275539",
            },
        }

    def make_video(self, **overrides):
        video = {
            "type": "mp4",
            "path": str(self.root / "clip.mp4"),
            "name": "clip.mp4",
            "width": 100,
            "height": 100,
            "fps": 25.0,
            "duration": timedelta(seconds=10),
            "bitRate": 1_000_000,
            "quality": 100.0,
            "nbFrames": 250,
        }
        video.update(overrides)
        return video

    def call_serial_api(self, method, video, *args, **kwargs):
        self.video_scripy.vList = [video]
        with (
            patch.object(self.video_scripy, "noticeProcessBegin"),
            patch.object(self.video_scripy, "noticeProcessEnd"),
            patch.object(self.video_scripy, "removeEmptyFolder"),
        ):
            getattr(self.video_scripy, method)(*args, **kwargs)

    def test_public_method_inventory(self):
        actual_methods = {
            name
            for name in dir(VideoScripy)
            if not name.startswith("_") and callable(getattr(VideoScripy, name))
        }
        self.assertEqual(actual_methods, self.PUBLIC_METHODS)

    def test_legacy_module_exports_remain_available(self):
        self.assertEqual(
            public_api.__all__,
            [
                "colorAnsi",
                "printC",
                "GPUInfo",
                "ProcAsyncReturn",
                "StreamInfo",
                "FrameByte",
                "VideoInfo",
                "VideoProcess",
                "VideoScripy",
                "run",
            ],
        )

    def test_manual_debug_entry_initializes_and_scans_without_running_operations(self):
        video_scripy = Mock()
        video_scripy.vList = [{"name": "clip.mp4"}]

        with patch.object(public_api, "VideoScripy", return_value=video_scripy):
            public_api._run_manual_debug()

        self.assertEqual(
            video_scripy.method_calls,
            [call.getVideo(), call.getVideoInfo()],
        )

    def test_constructor_initializes_and_checks_tools(self):
        with (
            patch.object(VideoScripy, "_add_project_tools_to_path"),
            patch.object(VideoScripy, "checkGPUs") as check_gpus,
            patch.object(VideoScripy, "selectDevice") as select_device,
            patch.object(VideoScripy, "setEncoder") as set_encoder,
            patch.object(VideoScripy, "checkTools") as check_tools,
        ):
            video_scripy = VideoScripy()

        self.assertEqual(video_scripy.vList, [])
        self.assertEqual(video_scripy.devices[0]["id"], -1)
        check_gpus.assert_called_once_with()
        select_device.assert_called_once_with()
        set_encoder.assert_called_once_with(h265=True)
        check_tools.assert_called_once_with()

    def test_check_tools_runs_all_tools_and_reports_results(self):
        results = [
            {"returnCode": 0, "stdout": b""},
            {"returnCode": 1, "stdout": b""},
            {"returnCode": 0, "stdout": b""},
            {"returnCode": 1, "stdout": b""},
            {"returnCode": 4294967295, "stdout": b""},
        ]
        output = io.StringIO()

        with (
            patch.object(
                self.video_scripy,
                "_resolve_tool",
                side_effect=lambda name: f"resolved/{name}",
            ),
            patch.object(self.video_scripy, "_runProcAsync") as run_proc_async,
            patch.object(
                self.video_scripy,
                "_runProcAsyncWait",
                return_value=results,
            ),
            redirect_stdout(output),
        ):
            self.video_scripy.checkTools()

        self.assertEqual(
            run_proc_async.call_args_list,
            [
                call("resolved/ffmpeg -version"),
                call("resolved/ffprobe -version"),
                call("resolved/realesrgan-ncnn-vulkan -h"),
                call("resolved/ifrnet-ncnn-vulkan -h"),
                call("resolved/NVEncC64 --version"),
            ],
        )
        self.assertIn("FFmpeg found", output.getvalue())
        self.assertIn("FFprobe not found", output.getvalue())
        self.assertIn("NVEncC found", output.getvalue())

    def test_check_gpus_discovers_devices_and_codecs(self):
        self.video_scripy.devices = [self.video_scripy.devices[0].copy()]
        results = [
            [{"returnCode": 0, "stdout": b"DeviceId #0: Test GPU\r\n"}],
            [
                {
                    "returnCode": 0,
                    "stdout": b"Codec: H.264/AVC\r\nCodec: H.265/HEVC\r\n",
                }
            ],
        ]

        with (
            patch.object(self.video_scripy, "_runProcAsync") as run_proc_async,
            patch.object(
                self.video_scripy,
                "_runProcAsyncWait",
                side_effect=results,
            ),
        ):
            self.video_scripy.checkGPUs()

        self.assertEqual(
            self.video_scripy.devices[1],
            {
                "id": 0,
                "name": "Test GPU",
                "codecs": ["H.264/AVC", "H.265/HEVC"],
            },
        )
        self.assertEqual(run_proc_async.call_count, 2)

    def test_select_device_sets_gpu_and_resets_encoder(self):
        gpu = {"id": 0, "name": "GPU", "codecs": ["H.264/AVC"]}
        self.video_scripy.devices.append(gpu)
        with patch.object(self.video_scripy, "setEncoder") as set_encoder:
            self.video_scripy.selectDevice(0)

        self.assertIs(self.video_scripy.selectedDevice, gpu)
        self.assertTrue(self.video_scripy.gpu)
        set_encoder.assert_called_once_with(False)

    def test_select_device_falls_back_to_cpu_for_unknown_id(self):
        output = io.StringIO()
        with (
            patch.object(self.video_scripy, "setEncoder") as set_encoder,
            redirect_stdout(output),
        ):
            self.video_scripy.selectDevice(42)

        self.assertEqual(self.video_scripy.selectedDevice["id"], -1)
        self.assertFalse(self.video_scripy.gpu)
        self.assertIn("Using CPU as default device", output.getvalue())
        set_encoder.assert_called_once_with(False)

    def test_remove_empty_folder_removes_only_empty_directory(self):
        empty = self.root / "empty"
        empty.mkdir()
        self.video_scripy.removeEmptyFolder(empty)
        self.assertFalse(empty.exists())

        nonempty = self.root / "nonempty"
        nonempty.mkdir()
        (nonempty / "keep.txt").write_text("content", encoding="utf-8")
        self.video_scripy.removeEmptyFolder(nonempty)
        self.assertTrue(nonempty.exists())

    def test_process_notifications_play_expected_sounds(self):
        with patch("videoscripy._core.playsound") as play_sound:
            self.video_scripy.noticeProcessBegin()
            self.video_scripy.noticeProcessEnd()

        self.assertEqual(play_sound.call_count, 2)
        self.assertEqual(play_sound.call_args_list[0].kwargs, {"block": False})
        self.assertEqual(play_sound.call_args_list[1].kwargs, {"block": True})

    def test_set_path_accepts_directory_and_rejects_missing_path(self):
        self.assertTrue(self.video_scripy.setPath(str(self.root)))
        self.assertEqual(self.video_scripy.path, str(self.root))
        self.assertFalse(self.video_scripy.setPath(str(self.root / "missing")))

    def test_set_path_empty_value_uses_current_directory(self):
        self.assertTrue(self.video_scripy.setPath(""))
        self.assertEqual(self.video_scripy.path, str(Path.cwd().resolve()))

    def test_get_video_scans_supported_files(self):
        (self.root / "clip.MP4").write_bytes(b"")
        (self.root / "song.mp3").write_bytes(b"")
        (self.root / "ignore.txt").write_bytes(b"")

        self.assertTrue(self.video_scripy.getVideo())
        self.assertEqual(
            [video["name"] for video in self.video_scripy.vList],
            ["clip.MP4", "song.mp3"],
        )
        self.assertEqual(
            [video["type"] for video in self.video_scripy.vList],
            ["mp4", "mp3"],
        )

    def test_get_video_rejects_missing_root(self):
        self.video_scripy.path = str(self.root / "missing")
        self.assertFalse(self.video_scripy.getVideo())
        self.assertEqual(self.video_scripy.vList, [])

    def test_get_video_info_calculates_video_properties(self):
        self.video_scripy.vList = [
            {"type": "mp4", "path": "clip.mp4", "name": "clip.mp4"}
        ]
        result = {
            "returnCode": 0,
            "stdout": json.dumps(self.make_probe_result()).encode("utf-8"),
        }
        with (
            patch.object(self.video_scripy, "_runProcAsync"),
            patch.object(
                self.video_scripy,
                "_runProcAsyncWait",
                return_value=[result],
            ),
        ):
            self.video_scripy.getVideoInfo()

        video = self.video_scripy.vList[0]
        self.assertEqual(video["width"], 266)
        self.assertEqual(video["height"], 200)
        self.assertEqual(video["fps"], 25.0)
        self.assertEqual(video["quality"], 2.7)
        self.assertEqual(video["nbFrames"], 256)

    def test_get_video_info_keeps_probe_results_with_their_videos(self):
        first_video = {
            "type": "mp4",
            "path": "first.mp4",
            "name": "first.mp4",
        }
        second_video = {
            "type": "mp4",
            "path": "second.mp4",
            "name": "second.mp4",
        }
        self.video_scripy.vList = [first_video, second_video]
        results = [
            {
                "returnCode": 0,
                "stdout": json.dumps(
                    self.make_probe_result(width=320, height=180)
                ).encode("utf-8"),
            },
            {
                "returnCode": 0,
                "stdout": json.dumps(
                    self.make_probe_result(width=1920, height=1080)
                ).encode("utf-8"),
            },
        ]
        with (
            patch.object(self.video_scripy, "_runProcAsync"),
            patch.object(
                self.video_scripy,
                "_runProcAsyncWait",
                return_value=results,
            ),
        ):
            self.video_scripy.getVideoInfo()

        self.assertEqual(first_video["width"], 320)
        self.assertEqual(first_video["height"], 180)
        self.assertEqual(second_video["width"], 1920)
        self.assertEqual(second_video["height"], 1080)

    def test_get_video_info_keeps_successful_result_aligned_after_probe_failure(self):
        failed_video = {
            "type": "mp4",
            "path": "failed.mp4",
            "name": "failed.mp4",
        }
        successful_video = {
            "type": "mp4",
            "path": "successful.mp4",
            "name": "successful.mp4",
        }
        self.video_scripy.vList = [failed_video, successful_video]
        results = [
            {"returnCode": 1, "stdout": b""},
            {
                "returnCode": 0,
                "stdout": json.dumps(
                    self.make_probe_result(width=1920, height=1080)
                ).encode("utf-8"),
            },
        ]
        with (
            patch.object(self.video_scripy, "_runProcAsync"),
            patch.object(
                self.video_scripy,
                "_runProcAsyncWait",
                return_value=results,
            ),
        ):
            self.video_scripy.getVideoInfo()

        self.assertEqual(self.video_scripy.vList, [successful_video])
        self.assertEqual(successful_video["width"], 1920)
        self.assertEqual(successful_video["height"], 1080)

    def test_get_video_info_handles_mkv_and_zero_dimensions(self):
        video = {"type": "mkv", "path": "clip.mkv", "name": "clip.mkv"}
        self.video_scripy.vList = [video]
        result = {
            "returnCode": 0,
            "stdout": json.dumps(
                self.make_probe_result(width=0)
            ).encode("utf-8"),
        }
        with (
            patch.object(self.video_scripy, "_runProcAsync"),
            patch.object(
                self.video_scripy,
                "_runProcAsyncWait",
                return_value=[result],
            ),
        ):
            self.video_scripy.getVideoInfo()

        self.assertEqual(video["width"], 0)
        self.assertEqual(video["quality"], 0.0)

    def test_set_encoder_configures_cpu_and_gpu(self):
        self.video_scripy.setEncoder(h265=False)
        self.assertEqual(self.video_scripy.encoder, " libx264 -crf 1 -preset medium")

        self.video_scripy.devices.append(
            {"id": 1, "name": "GPU", "codecs": ["H.264/AVC", "H.265/HEVC"]}
        )
        self.video_scripy.selectedDevice = self.video_scripy.devices[1]
        self.video_scripy.gpu = True
        self.video_scripy.setEncoder(h265=True)
        self.assertIn("hevc_nvenc", self.video_scripy.encoder)
        self.assertNotIn("weighted_pred", self.video_scripy.encoder)
        self.assertIn("-gpu 1", self.video_scripy.encoder)

    def test_kill_proc_kills_children_of_active_processes(self):
        child = SimpleNamespace(kill=Mock())
        parent = SimpleNamespace(children=Mock(return_value=[child]))
        self.video_scripy.proc = SimpleNamespace(pid=10)
        self.video_scripy.procAsync = [SimpleNamespace(pid=20)]

        with patch("videoscripy._processing.psutil.Process", return_value=parent) as process:
            self.video_scripy.killProc()

        self.assertEqual(process.call_args_list, [call(10), call(20)])
        self.assertEqual(child.kill.call_count, 2)
        self.assertTrue(self.video_scripy.killed)

    def test_run_proc_displays_command_output_when_it_fails(self):
        output = io.StringIO()
        process = Mock()
        process.stdout = io.BytesIO(b"encoder initialization failed")
        process.wait.return_value = 1
        self.video_scripy.EXIT_CODE_FILE_NAME = "exitCode.txt"

        with (
            patch("videoscripy._processing.subprocess.Popen", return_value=process),
            patch.object(self.video_scripy, "_checkExitCode", return_value=False),
            redirect_stdout(output),
        ):
            result = self.video_scripy._runProc("ffmpeg", "compress")

        self.assertFalse(result)
        self.assertIn("encoder initialization failed", output.getvalue())

    def test_displays_structured_ffmpeg_progress_record(self):
        output = io.StringIO()
        progress_record = (
            b"frame=24710\n"
            b"fps=257.00\n"
            b"stream_0_0_q=28.0\n"
            b"total_size=175636480\n"
            b"out_time=00:16:28.280000\n"
            b"bitrate=1421.8kbits/s\n"
            b"speed=10.3x\n"
            b"progress=continue\n"
        )
        receiver, sender = socket.socketpair()
        sender_thread = Thread(
            target=lambda: (sender.sendall(progress_record), sender.close())
        )

        with receiver, redirect_stdout(output):
            sender_thread.start()
            displayed = self.video_scripy._display_ffmpeg_progress(receiver, False)
            sender_thread.join()

        self.assertTrue(displayed)
        self.assertIn("frame=", output.getvalue())
        self.assertIn("24710", output.getvalue())
        self.assertIn("speed=10.3x", output.getvalue())

    @unittest.skipUnless(
        os.name == "nt"
        and (Path(__file__).resolve().parents[1] / "tools" / "ffmpeg-full_build" / "bin" / "ffmpeg.exe").is_file(),
        "Windows portable FFmpeg is required",
    )
    def test_windows_run_proc_streams_ffmpeg_progress_live(self):
        output = io.StringIO()
        self.video_scripy.EXIT_CODE_FILE_NAME = "exitCode.txt"
        ffmpeg = (
            Path(__file__).resolve().parents[1]
            / "tools"
            / "ffmpeg-full_build"
            / "bin"
            / "ffmpeg.exe"
        )
        command = (
            f'"{ffmpeg}" -hide_banner -re -f lavfi '
            f'-i testsrc=size=320x240:rate=30 -t 1 -f null NUL'
        )

        with redirect_stdout(output):
            result = self.video_scripy._runProc(command, "progress-test")

        self.assertTrue(result)
        self.assertIn("frame=", output.getvalue())
        self.assertIn("speed=", output.getvalue())

    def test_pre_compress_sets_bitrate_parameters_and_decides(self):
        video = self.make_video(quality=10.0)
        self.assertTrue(self.video_scripy.pre_compress(video, 100, 100, 3.0))
        self.assertEqual(video["compressBitRate"], 30_000)
        self.assertIn("-maxrate:v 30000", video["compressBitRateParam"])

        video["quality"] = 3.02
        self.assertFalse(self.video_scripy.pre_compress(video, 100, 100, 3.0))

    def test_compress_runs_for_supported_video(self):
        video = self.make_video()
        with (
            patch.object(self.video_scripy, "_getCommand", return_value="ffmpeg"),
            patch.object(self.video_scripy, "_runProc", return_value=True) as run_proc,
        ):
            self.call_serial_api("compress", video)

        run_proc.assert_called_once_with("ffmpeg", "compress")

    def test_resize_calculates_output_dimensions_and_runs(self):
        video = self.make_video()
        with (
            patch.object(self.video_scripy, "_getCommand", return_value="ffmpeg"),
            patch.object(self.video_scripy, "_runProc", return_value=True) as run_proc,
        ):
            self.call_serial_api("resize", video, 50, -1)

        self.assertEqual(video["resizeWidth"], 50)
        self.assertEqual(video["resizeHeight"], 50)
        run_proc.assert_called_once_with("ffmpeg", "resize")

    def test_upscale_runs_image_upscaler(self):
        video = self.make_video(type="png", path=str(self.root / "image.png"))
        with (
            patch.object(self.video_scripy, "_runProc", return_value=True) as run_proc,
            patch.object(
                self.video_scripy,
                "_resolve_tool",
                return_value="realesrgan",
            ),
        ):
            self.call_serial_api("upscale", video, 2)

        self.assertIn("realesrgan", run_proc.call_args.args[0])

    def test_interpolate_skips_audio_files(self):
        video = self.make_video(type="mp3")
        with patch.object(self.video_scripy, "_getFrames") as get_frames:
            self.call_serial_api("interpolate", video)
        get_frames.assert_not_called()

    def test_preview_generates_contact_sheet(self):
        video = self.make_video()
        self.video_scripy.DAY_ZERO = datetime(2000, 1, 1)

        def create_frame(command):
            output_path = re.search(r'"([^"]+\.png)"$', command).group(1)
            Image.new("RGB", (1, 1), color="red").save(output_path)

        with (
            patch.object(
                self.video_scripy,
                "_runProcAsync",
                side_effect=create_frame,
            ),
            patch.object(self.video_scripy, "_runProcAsyncWait", return_value=[]),
        ):
            self.call_serial_api("preview", video, 1, 1)

        self.assertTrue((self.root / "preview" / "clip.png").is_file())

    def test_frame_calculates_packet_and_second_data(self):
        video = self.make_video()
        video["path"] = "clip.mp4"
        self.video_scripy.DAY_ZERO = datetime(2000, 1, 1)
        probe = {
            "packets": [
                {"pts_time": "0.5", "size": "100"},
                {"pts_time": "1.5", "size": "200"},
            ]
        }
        result = {
            "returnCode": 0,
            "stdout": json.dumps(probe).encode("utf-8"),
        }
        with (
            patch.object(self.video_scripy, "_runProcAsync"),
            patch.object(
                self.video_scripy,
                "_runProcAsyncWait",
                return_value=[result],
            ),
        ):
            self.call_serial_api("frame", video)

        self.assertEqual(video["frameBytePerPacket"]["size"], [100, 200])
        self.assertEqual(video["frameBytePerSecond"]["size"], [100])

    def test_stream_without_video_finishes_without_running_command(self):
        self.video_scripy.vList = [
            {"type": "mp3", "path": "song.mp3", "name": "song.mp3"}
        ]
        with (
            patch.object(self.video_scripy, "noticeProcessBegin"),
            patch.object(self.video_scripy, "noticeProcessEnd"),
            patch.object(self.video_scripy, "removeEmptyFolder"),
            patch.object(self.video_scripy, "_runProc") as run_proc,
        ):
            self.video_scripy.stream()

        run_proc.assert_not_called()


if __name__ == "__main__":
    unittest.main()
