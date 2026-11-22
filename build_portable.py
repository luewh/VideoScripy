"""Build a portable Windows release of VideoScripyWebUI.

Usage:
    python build_portable.py [--version X.Y.Z] [--output DIST] [--no-download]
                             [--no-archive] [--cache-dir DIR] [--verbose]

Improvements over the original:
  - Caches the embeddable Python zip, re-validating it before reuse
  - Skips re-download if cache is valid (--no-download forces re-download)
  - Uses the embedded Python's own pip (via ensurepip)
  - Creates a .zip archive at root by default (--no-archive disables)
  - Supports --version to bump and write VERSION automatically
  - Better logging with --verbose
  - Validates required tools exist before starting
  - Idempotent: safe to re-run without manual cleanup

Output defaults to ./dist folder (not project root).
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path
from typing import Optional

try:
    from tqdm import tqdm
except ImportError:
    # Fallback to no progress bars if tqdm is not available
    class tqdm:  # type: ignore[no-redef]
        """No-op stand-in for tqdm when it is not installed."""

        def __init__(self, iterable=None, **kwargs):
            self.iterable = iterable

        def __enter__(self):
            return self

        def __exit__(self, *exc_info):
            return False

        def __iter__(self):
            return iter(self.iterable or ())

        def update(self, n=1):
            pass


EMBEDDED_URL_TEMPLATE = (
    "https://www.python.org/ftp/python/{version}/"
    "python-{version}-embed-amd64.zip"
)

REQUIRED_TOOLS = [
    ("FFmpeg", "tools/ffmpeg-full_build/bin/ffmpeg.exe"),
    ("FFprobe", "tools/ffmpeg-full_build/bin/ffprobe.exe"),
    ("Real-ESRGAN", "tools/Real-ESRGAN/realesrgan-ncnn-vulkan.exe"),
    ("IFRNet", "tools/Ifrnet/ifrnet-ncnn-vulkan.exe"),
    ("NVEncC", "tools/NVEncC/NVEncC64.exe"),
]

COPY_FILES = [
    "VideoScripy.py",
    "VideoScripyWebUI.py",
    "LICENSE",
    "VERSION",
]

COPY_DIRS = [
    "videoscripy",
    "webui",
    "assets",
    "tools",
]


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    sys.exit(1)


def warn(message: str) -> None:
    print(f"WARNING: {message}", file=sys.stderr)


def log(message: str, verbose: bool = False) -> None:
    if verbose:
        print(f"[build] {message}")


def run(cmd: list[str], verbose: bool = False, **kwargs) -> subprocess.CompletedProcess:
    if verbose:
        print("+", " ".join(cmd))
    return subprocess.run(cmd, check=True, **kwargs)


def download(url: str, dest: Path, verbose: bool = False) -> None:
    log(f"Downloading {url}", verbose)

    # write next to the target and only move it into place once complete,
    # so an interrupted download never leaves a broken zip in the cache
    partial = dest.with_name(dest.name + ".part")
    try:
        with urllib.request.urlopen(url) as response, open(partial, "wb") as out_file:
            length = response.headers.get("Content-Length")
            total = int(length) if length else None

            with tqdm(
                total=total,
                initial=0,
                desc=dest.name,
                ncols=80,
                leave=False,
            ) as pbar:
                while True:
                    chunk = response.read(64 * 1024)
                    if not chunk:
                        break
                    out_file.write(chunk)
                    pbar.update(len(chunk))

        size = partial.stat().st_size
        if total is not None and size != total:
            raise IOError(f"incomplete download ({size} of {total} bytes)")
        if not is_valid_python_zip(partial):
            raise IOError("downloaded file is not a usable embeddable Python zip")

        os.replace(partial, dest)
    except Exception as e:
        partial.unlink(missing_ok=True)
        fail(f"Failed to download embeddable Python: {e}")


def read_app_version(root: Path) -> str:
    version_file = root / "VERSION"
    if not version_file.exists():
        fail(f"Version file not found: {version_file}")
    version = version_file.read_text(encoding="utf-8").strip()
    if not version:
        fail(f"Version file is empty: {version_file}")
    return version


def write_app_version(root: Path, version: str) -> None:
    (root / "VERSION").write_text(version + "\n", encoding="utf-8")


def validate_python_interpreter(python_cmd: str, verbose: bool = False) -> dict:
    info_cmd = [
        python_cmd, "-c",
        "import json, struct, sys; "
        "print(json.dumps({'version': list(sys.version_info[:3]), "
        "'prefix': sys.base_prefix, 'bits': struct.calcsize('P') * 8}))",
    ]
    result = run(info_cmd, capture_output=True, text=True, verbose=verbose)
    python_info = json.loads(result.stdout)

    if (python_info["version"][0] != 3
            or python_info["version"][1] != 13
            or python_info["bits"] != 64):
        found = f"{python_info['version'][0]}.{python_info['version'][1]}"
        fail(f"Requires 64-bit Python 3.13. Found {found} ({python_info['bits']}-bit).")

    return python_info


def validate_tools(root: Path, verbose: bool = False) -> None:
    missing = []
    for name, rel_path in REQUIRED_TOOLS:
        full = root / rel_path
        if not full.exists():
            missing.append(f"  {name}: {full}")
    if missing:
        fail("Required tools missing:\n" + "\n".join(missing))


def is_valid_python_zip(path: Path) -> bool:
    """A usable embeddable Python archive must be a readable zip with python.exe."""
    try:
        with zipfile.ZipFile(path) as zf:
            if "python.exe" not in zf.namelist():
                return False
            return zf.testzip() is None
    except (zipfile.BadZipFile, OSError):
        return False


def get_cached_python_zip(cache_dir: Path, version: str) -> Optional[Path]:
    cache_dir.mkdir(parents=True, exist_ok=True)
    expected_name = f"python-{version}-embed-amd64.zip"
    for f in cache_dir.glob("python-*-embed-amd64.zip"):
        if f.name == expected_name:
            if is_valid_python_zip(f):
                return f
            warn(f"Ignoring unusable cached zip ({f.stat().st_size} bytes): {f}")
            f.unlink(missing_ok=True)
            return None
    return None


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build a portable Windows release of VideoScripyWebUI."
    )
    parser.add_argument(
        "--python", default="python",
        help="Python executable for building (default: python)",
    )
    parser.add_argument(
        "--output", default="dist",
        help="Output directory (default: dist)",
    )
    parser.add_argument(
        "--version", metavar="X.Y.Z",
        help="Bump VERSION file to this value before building",
    )
    parser.add_argument(
        "--no-download", action="store_true",
        help="Do not re-download if a cached embeddable Python zip exists",
    )
    parser.add_argument(
        "--no-archive", action="store_true",
        help="Do not create a .zip archive of the portable folder",
    )
    parser.add_argument(
        "--cache-dir", default=None,
        help="Directory to cache the embeddable Python zip "
             "(default: %%TEMP%%/videoscripy-build-cache)",
    )
    parser.add_argument(
        "--verbose", action="store_true",
        help="Enable verbose logging",
    )
    args = parser.parse_args()

    root = Path(__file__).resolve().parent

    # --- Version handling -----------------------------------------------------
    if args.version:
        write_app_version(root, args.version)
        log(f"Version bumped to {args.version}", args.verbose)

    app_version = read_app_version(root)

    # --- Validate build interpreter ------------------------------------------
    python_info = validate_python_interpreter(args.python, args.verbose)
    python_cmd = shutil.which(args.python)
    if python_cmd is None:
        fail(f"Python executable not found: {args.python}")

    build_version = ".".join(str(v) for v in python_info["version"])
    base_prefix = python_info["prefix"]

    # --- Validate required tools ---------------------------------------------
    validate_tools(root, args.verbose)

    # --- Paths ----------------------------------------------------------------
    output_dir = Path(args.output).resolve()
    portable_dir = output_dir / f"VideoScripy-v{app_version}"
    runtime_dir = portable_dir / "python"
    site_packages = runtime_dir / "Lib" / "site-packages"
    runtime_dlls = runtime_dir / "DLLs"

    # --- Download / cache embeddable Python ----------------------------------
    cache_dir = Path(args.cache_dir) if args.cache_dir else Path(
        tempfile.gettempdir()
    ) / "videoscripy-build-cache"
    embedded_url = EMBEDDED_URL_TEMPLATE.format(version=build_version)

    cached_zip = get_cached_python_zip(cache_dir, build_version)
    if cached_zip and not args.no_download:
        log(f"Using cached embeddable Python: {cached_zip}", args.verbose)
        tmp_zip = cached_zip
    else:
        tmp_zip = cache_dir / f"python-{build_version}-embed-amd64.zip"
        download(embedded_url, tmp_zip, args.verbose)
        if not is_valid_python_zip(tmp_zip):
            tmp_zip.unlink(missing_ok=True)
            fail(f"Downloaded embeddable Python archive is unusable: {tmp_zip}")

    # --- Prepare output directory --------------------------------------------
    if portable_dir.exists():
        shutil.rmtree(portable_dir)
    runtime_dir.mkdir(parents=True, exist_ok=True)
    site_packages.mkdir(parents=True, exist_ok=True)
    runtime_dlls.mkdir(parents=True, exist_ok=True)

    try:
        # --- Extract runtime -------------------------------------------------
        log("Extracting embeddable Python...", args.verbose)
        with zipfile.ZipFile(tmp_zip, "r") as zip_ref:
            zip_ref.extractall(runtime_dir)

        # --- Copy Tcl/Tk support ---------------------------------------------
        log("Copying Tcl/Tk support...", args.verbose)
        tkinter_src = Path(base_prefix) / "Lib" / "tkinter"
        if tkinter_src.exists():
            shutil.copytree(
                tkinter_src,
                runtime_dir / "Lib" / "tkinter",
                dirs_exist_ok=True,
            )

        for dll in ["_tkinter.pyd", "tcl86t.dll", "tk86t.dll", "zlib1.dll"]:
            src = Path(base_prefix) / "DLLs" / dll
            if src.exists():
                shutil.copy2(src, runtime_dir / "DLLs" / dll)

        tcl_dir = runtime_dir / "tcl"
        tcl_dir.mkdir(parents=True, exist_ok=True)
        for tcl_ver in ["tcl8.6", "tk8.6"]:
            src = Path(base_prefix) / "tcl" / tcl_ver
            if src.exists():
                shutil.copytree(
                    src, tcl_dir / tcl_ver, dirs_exist_ok=True
                )

        # --- Configure python._pth -------------------------------------------
        pth_files = list(runtime_dir.glob("python*._pth"))
        if not pth_files:
            fail("Embedded Python package missing python._pth file.")
        pth_file = pth_files[0]

        pth_content = "\n".join([
            f"{pth_file.stem}.zip",
            "..",
            ".",
            "DLLs",
            "Lib",
            "Lib\\site-packages",
            "import site",
        ]) + "\n"
        pth_file.write_text(pth_content, encoding="ascii")

        # --- sitecustomize.py ------------------------------------------------
        sitecustomize = runtime_dir / "Lib" / "sitecustomize.py"
        sitecustomize.write_text(
            "\n".join([
                "import os",
                "import sys",
                "runtime = os.path.dirname(sys.executable)",
                "_dll_directory = os.add_dll_directory(os.path.join(runtime, 'DLLs'))",
                "os.environ.setdefault('TCL_LIBRARY', os.path.join(runtime, 'tcl', 'tcl8.6'))",
                "os.environ.setdefault('TK_LIBRARY', os.path.join(runtime, 'tcl', 'tk8.6'))",
            ]) + "\n",
            encoding="ascii",
        )

        # --- Install dependencies using system pip into embedded site-packages
        log("Installing dependencies into embedded runtime...", args.verbose)
        
        # Use pip with optimizations for smaller, faster installs:
        # --only-binary=:all: forces pre-built wheels (smaller, no source builds)
        # --prefer-binary prefers wheels over source even when not strictly required
        # --disable-pip-version-check avoids network calls to check pip version
        run([
            python_cmd, "-m", "pip", "install",
            "--only-binary=:all:",  # Use only pre-built wheels (much smaller)
            "--prefer-binary",      # Prefer wheels when available
            "--disable-pip-version-check",
            "--no-warn-script-location",
            "--no-compile",         # Skip .pyc files for faster startup
            "--no-cache-dir",       # Don't cache downloaded files (smaller final build)
            "--target", str(site_packages),
            "-r", str(root / "requirements.txt"),
        ], verbose=args.verbose)

        # --- Cleanup site-packages from unnecessary cached/wheel files
        log("Cleaning up site-packages...", args.verbose)
        
        # Remove any wheel cache or empty directories left in site-packages
        try:
            # Clean up any __pycache__ directories (already handled by --no-compile, but be safe)
            for pycache_dir in site_packages.glob("*/__pycache__"):
                shutil.rmtree(pycache_dir)
            
            # Remove any wheel cache subdirectories that might exist
            for wheel_cache in site_packages.glob("*/*.dist-info/wheels*"):
                if wheel_cache.is_dir():
                    shutil.rmtree(wheel_cache)
        except Exception as e:
            log(f"Cleanup warning: {e}", args.verbose)  # Don't fail on cleanup errors

        # --- Copy application files ------------------------------------------
        for source_file in COPY_FILES:
            shutil.copy2(root / source_file, portable_dir / source_file)

        for source_dir in COPY_DIRS:
            shutil.copytree(root / source_dir, portable_dir / source_dir,
                            dirs_exist_ok=True)

        # --- Launcher batch file ---------------------------------------------
        launcher = "\n".join([
            "@echo off",
            "setlocal",
            "cd /d \"%~dp0\"",
            "set \"TCL_LIBRARY=%~dp0python\\tcl\\tcl8.6\"",
            "set \"TK_LIBRARY=%~dp0python\\tcl\\tk8.6\"",
            "set \"VIDEOSCRIPY_PORTABLE=1\"",
            "set \"PATH=%~dp0python;%~dp0python\\DLLs;"
            "%~dp0tools\\ffmpeg-full_build\\bin;"
            "%~dp0tools\\Real-ESRGAN;"
            "%~dp0tools\\Ifrnet;"
            "%~dp0tools\\NVEncC;%PATH%\"",
            "\"%~dp0python\\python.exe\" \"%~dp0VideoScripyWebUI.py\"",
            "if errorlevel 1 pause",
            "",
        ])
        (portable_dir / "Run VideoScripyWebUI.bat").write_text(
            launcher, encoding="ascii"
        )

        # --- Portable README -------------------------------------------------
        readme = "\n".join([
            f"VideoScripy v{app_version} portable for Windows x64",
            "",
            "Run \"Run VideoScripyWebUI.bat\". This folder includes the embeddable Python",
            "runtime, application dependencies, Tcl/Tk, assets, and required tools.",
            "Python does not need to be installed on the target PC.",
            "",
            "Keep the complete folder together when moving it. NVIDIA GPU features require",
            "a compatible NVIDIA driver; the bundled AI tools may also require Vulkan support.",
            "",
        ])
        (portable_dir / "README_PORTABLE.txt").write_text(readme, encoding="ascii")

        # --- Validate embedded runtime ---------------------------------------
        log("Validating embedded runtime...", args.verbose)
        old_path = os.environ.get("PATH", "")
        old_tcl = os.environ.get("TCL_LIBRARY")
        old_tk = os.environ.get("TK_LIBRARY")

        try:
            os.environ["PATH"] = (
                f"{runtime_dir};{runtime_dir / 'DLLs'};"
                f"{os.environ.get('SystemRoot', '')}\\System32;"
                f"{os.environ.get('SystemRoot', '')}"
            )
            os.environ["TCL_LIBRARY"] = str(runtime_dir / "tcl" / "tcl8.6")
            os.environ["TK_LIBRARY"] = str(runtime_dir / "tcl" / "tk8.6")

            result = run(
                [str(runtime_dir / "python.exe"), "-c",
                 "import dash, dash_bootstrap_components, plotly, tkinter; "
                 "print('embedded-runtime-ok')"],
                capture_output=True, text=True,
            )
            if result.returncode != 0:
                fail("Embedded runtime validation failed:\n" + result.stderr)
            if "embedded-runtime-ok" not in result.stdout:
                fail("Embedded runtime validation produced unexpected output.")
        finally:
            os.environ["PATH"] = old_path
            if old_tcl is None:
                os.environ.pop("TCL_LIBRARY", None)
            else:
                os.environ["TCL_LIBRARY"] = old_tcl
            if old_tk is None:
                os.environ.pop("TK_LIBRARY", None)
            else:
                os.environ["TK_LIBRARY"] = old_tk

        # --- Create ZIP archive at root by default ---------------------------
        if not args.no_archive:
            archive_path = output_dir / f"VideoScripy-v{app_version}.zip"
            log(f"Creating archive {archive_path}...", args.verbose)

            # Count all files first for progress tracking
            base = output_dir / archive_path.stem  # This is the portable_dir (e.g., dist/VideoScripy-v0.7.4)
            
            # List files to verify we're zipping only the right content
            log(f"Archiving folder contents from {base}...", args.verbose)
            file_list = []
            for root, dirs, files in os.walk(base):
                dirs.sort()  # Process directories in alphabetical order
                for filename in sorted(files):
                    file_path = Path(root) / filename
                    if file_path.is_file():
                        arcname = file_path.relative_to(base)  # Relative to portable_dir
                        log(f"  - {arcname}", args.verbose)
                        file_list.append((str(arcname), file_path))
            
            total_files = len(file_list)
            
            # Use tqdm for visual progress bar during ZIP compression
            with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_LZMA) as zf:
                for i, (arcname_str, file_path) in enumerate(tqdm(
                    file_list, 
                    total=total_files, 
                    desc="Packaging files", 
                    ncols=80, 
                    leave=False,
                ), 1):
                    arcname = Path(arcname_str) if not isinstance(arcname_str, tuple) else Path(arcname_str[0])
                    with zf.open(str(arcname), "w") as zipf:
                        with open(file_path, "rb") as src:
                            shutil.copyfileobj(src, zipf)

            print()  # New line after progress bar
            print(f"Archive created: {archive_path}")

        print(f"Portable folder created at: {portable_dir} (VideoScripy v{app_version})")

    finally:
        # the cached zip is reused by later builds, only stale download leftovers are removed
        for partial in cache_dir.glob("python-*-embed-amd64.zip.part"):
            partial.unlink(missing_ok=True)


if __name__ == "__main__":
    main()