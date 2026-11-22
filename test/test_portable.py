import os
import socket
import subprocess
import time
import unittest
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parents[1]

_APP_VERSION = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
PORTABLE_DIR = Path(
    os.environ.get(
        "VIDEOSCRIPY_PORTABLE_DIR",
        ROOT / "dist" / f"VideoScripy-v{_APP_VERSION}",
    )
)
PYTHON_EXE = PORTABLE_DIR / "python" / "python.exe"
APP_PORT = 8848


class PortableBundleTests(unittest.TestCase):
    def test_portable_folder_contains_runtime_application_and_tools(self):
        required_paths = [
            PYTHON_EXE,
            PORTABLE_DIR / "VideoScripyWebUI.py",
            PORTABLE_DIR / "VideoScripy.py",
            PORTABLE_DIR / "webui" / "app.py",
            PORTABLE_DIR / "webui" / "layout.py",
            PORTABLE_DIR / "webui" / "callbacks" / "videos.py",
            PORTABLE_DIR / "videoscripy" / "_core.py",
            PORTABLE_DIR / "videoscripy" / "_operations.py",
            PORTABLE_DIR / "videoscripy" / "_processing.py",
            PORTABLE_DIR / "videoscripy" / "_types.py",
            PORTABLE_DIR / "videoscripy" / "_utilities.py",
            PORTABLE_DIR / "Run VideoScripyWebUI.bat",
            PORTABLE_DIR / "assets" / "style.css",
            PORTABLE_DIR / "tools" / "ffmpeg-full_build" / "bin" / "ffmpeg.exe",
            PORTABLE_DIR / "tools" / "ffmpeg-full_build" / "bin" / "ffprobe.exe",
            PORTABLE_DIR / "tools" / "Real-ESRGAN" / "realesrgan-ncnn-vulkan.exe",
            PORTABLE_DIR / "tools" / "Ifrnet" / "ifrnet-ncnn-vulkan.exe",
            PORTABLE_DIR / "tools" / "NVEncC" / "NVEncC64.exe",
        ]

        missing = [str(path) for path in required_paths if not path.is_file()]
        self.assertEqual(missing, [], f"Portable bundle is missing files: {missing}")

    def test_embedded_python_imports_dependencies_without_system_python(self):
        environment = os.environ.copy()
        environment.pop("PYTHONPATH", None)
        environment["PATH"] = os.pathsep.join(
            [
                str(PYTHON_EXE.parent),
                str(PYTHON_EXE.parent / "DLLs"),
                os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32"),
                os.environ.get("SystemRoot", r"C:\Windows"),
            ]
        )
        environment["TCL_LIBRARY"] = str(PYTHON_EXE.parent / "tcl" / "tcl8.6")
        environment["TK_LIBRARY"] = str(PYTHON_EXE.parent / "tcl" / "tk8.6")

        result = subprocess.run(
            [
                str(PYTHON_EXE),
                "-c",
                "import dash, dash_bootstrap_components, plotly, tkinter; print('imports-ok')",
            ],
            cwd=PORTABLE_DIR,
            env=environment,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("imports-ok", result.stdout)

    def test_bundled_dash_versions_match_the_dropdown_css(self):
        result = subprocess.run(
            [
                str(PYTHON_EXE),
                "-c",
                "import dash, dash_bootstrap_components; print(dash.__version__); print(dash_bootstrap_components.__version__)",
            ],
            cwd=PORTABLE_DIR,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        dash_version, dbc_version = result.stdout.splitlines()
        self.assertTrue(dash_version.startswith("2.18."), dash_version)
        self.assertTrue(dbc_version.startswith("1."), dbc_version)

    def test_portable_webui_starts_and_finds_local_tools(self):
        with socket.socket() as listener:
            try:
                listener.bind(("127.0.0.1", APP_PORT))
            except OSError:
                self.skipTest(f"Port {APP_PORT} is already in use")

        environment = os.environ.copy()
        environment.pop("PYTHONPATH", None)
        environment["VIDEOSCRIPY_PORTABLE"] = "1"
        environment["VIDEOSCRIPY_NO_BROWSER"] = "1"
        environment["PATH"] = os.pathsep.join(
            [
                str(PYTHON_EXE.parent),
                str(PYTHON_EXE.parent / "DLLs"),
                os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32"),
                os.environ.get("SystemRoot", r"C:\Windows"),
            ]
        )
        environment["TCL_LIBRARY"] = str(PYTHON_EXE.parent / "tcl" / "tcl8.6")
        environment["TK_LIBRARY"] = str(PYTHON_EXE.parent / "tcl" / "tk8.6")

        process = subprocess.Popen(
            [str(PYTHON_EXE), str(PORTABLE_DIR / "VideoScripyWebUI.py")],
            cwd=PORTABLE_DIR,
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        response_body = ""
        failure_message = "Portable WebUI did not respond before timeout."
        try:
            deadline = time.monotonic() + 45
            while time.monotonic() < deadline and process.poll() is None:
                try:
                    with urlopen(f"http://127.0.0.1:{APP_PORT}/", timeout=2) as response:
                        self.assertEqual(response.status, 200)
                        response_body = response.read().decode("utf-8", errors="replace")
                        break
                except (URLError, TimeoutError, ConnectionError):
                    time.sleep(0.5)

            if not response_body and process.poll() is not None:
                failure_message = f"Portable WebUI exited with code {process.returncode} before responding."
        finally:
            if process.poll() is None:
                process.terminate()
            output, _ = process.communicate(timeout=10)

        if not response_body:
            self.fail(f"{failure_message}\nApplication output:\n{output}")
        self.assertIn("VS WebUI", response_body)
        for tool in ("FFmpeg found", "FFprobe found", "Real-ESRGAN found", "IFRNet found", "NVEncC found"):
            self.assertIn(tool, output)


if __name__ == "__main__":
    unittest.main()
