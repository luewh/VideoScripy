from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
from datetime import datetime, timedelta
from math import ceil
from pathlib import Path
from os import rmdir, walk
from typing import Any

from playsound import playsound

from ._types import (
    ROOT_DIR,
    GPUInfo,
    StreamInfo,
    VideoInfo,
    VideoProcess,
    VideoScripyContext,
)
from ._utilities import printC


class _CoreMixin(VideoScripyContext):
    """Device setup, paths, media discovery, and metadata handling."""

    def checkTools(self) -> None:
        """
        Check all tools by running -version or -h with cmd.exe asynchronously.\n
        Tool found if returned code is 0 or 4_294_967_295
        """
        tool_commands = {
            "FFmpeg": (self._resolve_tool("ffmpeg") or "ffmpeg") + " -version",
            "FFprobe": (self._resolve_tool("ffprobe") or "ffprobe") + " -version",
            "Real-ESRGAN": (self._resolve_tool("realesrgan-ncnn-vulkan") or "realesrgan-ncnn-vulkan") + " -h",
            "IFRNet": (self._resolve_tool("ifrnet-ncnn-vulkan") or "ifrnet-ncnn-vulkan") + " -h",
            "NVEncC": (self._resolve_tool("NVEncC64") or "NVEncC64") + " --version",
        }
        for cmd in tool_commands.values():
            self._runProcAsync(cmd)

        results = self._runProcAsyncWait()
        for tool, result in zip(tool_commands, results):
            if result["returnCode"] in [0, 4294967295]:
                printC(f'{tool} found', 'green')
            else:
                printC(f'{tool} not found, please check the project tools folder or environment "PATH"', 'red')

    def checkGPUs(self) -> None:
        """
        Fill up self.devices by each GPU's info.
        """
        # get gpu device
        command = (self._resolve_tool("NVEncC64") or "NVEncC64") + " --check-device"
        self._runProcAsync(command)
        gpu_device_result = self._runProcAsyncWait()[0]
        gpu_lines = gpu_device_result["stdout"].decode('utf-8').split("\r\n")
        for resultStr in gpu_lines:
            if "DeviceId" in resultStr:
                id = re.findall("#.+:", resultStr)[0].replace("#", "").replace(":", "")
                try:
                    id = int(id)
                except:
                    printC("Unexpected int conversion error at self.checkGPUs()", "red")
                
                name = re.split("#.+:", resultStr)[-1].strip()

                self.devices.append({
                    "id" : id,
                    "name" : name,
                    "codecs" : [],
                })

        # get codec of each gpu
        for device in self.devices:

            # skip CPU
            if device["id"] == -1:
                continue

            command = (self._resolve_tool("NVEncC64") or "NVEncC64") + f' --check-features {device["id"]}'
            self._runProcAsync(command)
            codec_result = self._runProcAsyncWait()[0]
            codec_lines = codec_result["stdout"].decode('utf-8').split("\r\n")
            for resultStr in codec_lines:
                if "Codec:" in resultStr:
                    device["codecs"].append(resultStr.split(":")[-1].strip())

    def selectDevice(self, deviceId:int=0) -> None:
        """
        Set self.selectedDevice to corresponding element of self.devices.\n
        Re setEncoder() with self.h265 as argument.\n
        Set self.gpu to True if selected device's id is not -1.\n
        If wrong id entered, will use -1 as default which correspond to CPU.\n
        """
        # check device id availability
        if deviceId not in [device["id"] for device in self.devices]:
            printC(f'Wrong device id "{deviceId}" is entered, available id are:', "red")
            for device in self.devices:
                print(f'    {device["id"]} : {device["name"]}')
            printC("Using CPU as default device", "yellow")
            deviceId = -1

        # select device
        for device in self.devices:
            if deviceId == device["id"]:
                self.selectedDevice = device
                printC(f'Selecting device {self.selectedDevice["id"]} : {self.selectedDevice["name"]}', "blue")
                printC(f'Available codec : {" | ".join(self.selectedDevice["codecs"])}', "blue")
        
        # set gpu state
        self.gpu = deviceId != -1
        
        # set encoder according to selected device ability
        # print("Need to reset the video encoder")
        self.setEncoder(self.h265)

    def removeEmptyFolder(self, folderName: str | Path | None = None):
        if folderName is not None:
            try:
                rmdir(folderName)
            except:
                pass
        else:
            for process in [p.name for p in VideoProcess]:
                outputFolder = self._path(process)
                self.removeEmptyFolder(outputFolder)

    def _project_tool_paths(self) -> list[Path]:
        return [
            self.root_dir / "tools" / "ffmpeg-full_build" / "bin",
            self.root_dir / "tools" / "Real-ESRGAN",
            self.root_dir / "tools" / "Ifrnet",
            self.root_dir / "tools" / "NVEncC",
        ]

    def _add_project_tools_to_path(self) -> None:
        tool_paths = self._project_tool_paths()
        existing = [p for p in os.environ.get("PATH", "").split(os.pathsep) if p]
        normalized = {str(Path(p).resolve()) for p in existing}

        for tool_path in tool_paths:
            if not tool_path.exists():
                continue
            resolved = str(tool_path.resolve())
            if resolved not in normalized:
                os.environ["PATH"] = resolved + os.pathsep + os.environ.get("PATH", "")
                normalized.add(resolved)

    def _resolve_tool(self, name: str) -> str | None:
        candidates: list[str] = []
        if os.name == "nt":
            candidates.extend([name, name.replace(".exe", "")])
        else:
            candidates.extend([name, name.replace(".exe", "")])

        if os.name == "nt" and not name.lower().endswith(".exe"):
            candidates.append(f"{name}.exe")

        for candidate in candidates:
            resolved = os.environ.get("PATH", "")
            if resolved:
                for part in resolved.split(os.pathsep):
                    if not part:
                        continue
                    candidate_path = Path(part) / candidate
                    if candidate_path.is_file():
                        return self._quote_command_path(candidate_path)
            found = __import__("shutil").which(candidate)
            if found is not None:
                return self._quote_command_path(Path(found))

        for path in self._project_tool_paths():
            for file_name in [name, name.replace(".exe", "")]:
                possible = path / file_name
                if possible.is_file():
                    return self._quote_command_path(possible)
                if os.name == "nt" and not file_name.lower().endswith(".exe"):
                    possible = path / f"{file_name}.exe"
                    if possible.is_file():
                        return self._quote_command_path(possible)

        return None

    @staticmethod
    def _quote_command_path(path: Path) -> str:
        if os.name == "nt":
            return subprocess.list2cmdline([str(path)])
        return shlex.quote(str(path))

    def _asset_path(self, *parts:str | Path) -> Path:
        return self.root_dir.joinpath(*map(str, parts))

    def _path(self, *parts:str | Path) -> Path:
        return Path(self.path).joinpath(*map(str, parts))

    def noticeProcessBegin(self):
        sound = self._asset_path("assets", "typewriter_carriage_return.mp3")
        try:
            playsound(str(sound), block=False)
        except:
            pass

    def noticeProcessEnd(self):
        sound = self._asset_path("assets", "typewriter_bell.mp3")
        try:
            playsound(str(sound), block=True)
        except:
            pass

    def setPath(self, path:str="") -> bool:
        """
        Set attributes path, return setting result

        Parameters:
            path (str):
                set to empty "" will use os.getcwd() as default path
        """
        if path == "":
            self.path = str(Path.cwd().resolve())
            printC(f'Path set to default "{self.path}"', "green")
            return True

        candidate = Path(path).expanduser()
        if not candidate.is_absolute():
            candidate = (Path.cwd() / candidate).resolve()
        else:
            candidate = candidate.resolve()

        if candidate.is_dir():
            self.path = str(candidate)
            printC(f'Path correctly set to "{self.path}"', "green")
            return True

        printC(f'Path "{path}" do not exist', "red")
        return False

    def getVideo(self, folderDepthLimit:int=0) -> bool:
        """
        Set attribute vList's path and name by os.walk().\n
        Return false if self.path do not exist anymore.

        Parameters:
            folderDepthLimit (int):
                limit the scan depth
        """
        
        # empty video list
        self.vList = []
        
        # check path validity
        root_path = Path(self.path).resolve()
        if not root_path.is_dir():
            printC(f'Path "{self.path}" do not exist', "red")
            return False

        for root, _, files in walk(root_path):
            root_path_obj = Path(root)
            relative_root = root_path_obj.relative_to(root_path)
            currentDepth = len(relative_root.parts) if relative_root != Path('.') else 0

            # skip too deep folder
            if currentDepth > folderDepthLimit and folderDepthLimit != -1:
                continue
            # skip folder
            skip = False
            for folderSkip in self.folderSkip:
                if root_path_obj.name == folderSkip:
                    printC(f'Self generated folder "{folderSkip}" skiped', "yellow")
                    skip = True
                    break
            if skip:
                continue

            # get videos
            for file in files:
                # skip not supported type
                fileFormat = file.split(".")[-1].lower()
                if fileFormat not in self.scanType:
                    continue
                file_path = root_path_obj / file
                if "&" in str(file_path):
                    printC(f'"&" must not used in path or file name', "yellow")
                    printC(f'Skipped "{file}"', "yellow")
                    continue
                self.vList.append({
                    "type" : fileFormat,
                    "path" : str(file_path),
                    "name" : str(file_path.relative_to(root_path)).replace("/", "__")
                })
            
            # stop scan for perfomance
            if folderDepthLimit == 0:
                break
        
        # order by name
        self.vList.sort(key= lambda video: video['name'])

        return True

    def getVideoInfo(self) -> None:
        """
        Set attributes vList's stream and video properties with ffprobe asynchronously
        """
    
        # run probe
        for video in self.vList:
            command = (
                f' ffprobe'
                f' -i "{video["path"]}"'
                f' -show_format'
                f' -show_streams'
                f' -of json'
            )
            self._runProcAsync(command)

        # wait and retrieve results
        probe_results = self._runProcAsyncWait()
        parsed_results: list[dict[str, Any] | None] = []
        for result in probe_results:
            if result["returnCode"] != 0:
                parsed_results.append(None)
            else:
                parsed_results.append(
                    json.loads(result["stdout"].decode("utf-8"))
                )

        # get info
        for videoIndex in range(len(self.vList)-1, -1, -1):
            results = parsed_results[videoIndex]
            if results is None:
                printC(f'FFprobe error, remove {self.vList[videoIndex]["name"]}', "red")
                self.vList.pop(videoIndex)
                continue

            try:
                current_video = self.vList[videoIndex]
                current_video_data: dict[str, Any] = dict(current_video)
                streamInfo:list[StreamInfo] = []
                videoStream: list[dict[str, Any]] = []
                for stream in results['streams']:
                    try:
                        codecName = stream["codec_name"]
                    except KeyError:
                        codecName = stream["codec_tag_string"]

                    try:
                        tagLanguage = stream["tags"]["language"]
                    except KeyError:
                        tagLanguage = "und"

                    try:
                        tagTitle = stream["tags"]["handler_name"]
                    except KeyError:
                        try:
                            tagTitle = stream["tags"]["HANDLER_NAME"]
                        except KeyError:
                            tagTitle = ""

                    streamInfo.append({
                        "index": int(stream["index"]),
                        "codec_type": stream["codec_type"],
                        "codec_name": codecName,
                        "selected": True,
                        "language": tagLanguage,
                        "title": tagTitle,
                    })

                    if stream['codec_type'] == 'video':
                        videoStream.append(stream)

                current_video['streams'] = streamInfo
                current_video['fileSize'] = int(results['format']['size'])

                width_value = 0
                height_value = 0
                if current_video["type"] in self.vType:
                    try:
                        videoStreamItem = videoStream[0]
                        width_value = int(videoStreamItem['width'])
                        height_value = int(videoStreamItem['height'])
                        current_video['width'] = width_value
                        current_video['height'] = height_value
                        num, denom = videoStreamItem['r_frame_rate'].split('/')
                        frame_rate_denominator = float(denom)
                        current_video['fps'] = (
                            round(float(num) / frame_rate_denominator, 2)
                            if frame_rate_denominator != 0
                            else 0.0
                        )
                    except Exception:
                        printC(
                            f'"{current_video["name"]}" typed as video but has no video content',
                            "yellow"
                        )
                        current_video["type"] = "other"

                if current_video["type"] == "mp4":
                    current_video['duration'] = timedelta(seconds=float(videoStream[0]['duration']))
                    bit_rate = int(videoStream[0]['bit_rate'])
                    current_video['bitRate'] = bit_rate
                    current_video['nbFrames'] = int(videoStream[0]['nb_frames'])
                    current_video["quality"] = round(
                        bit_rate / (width_value * height_value), 1
                    ) if width_value > 0 and height_value > 0 else 0.0
                elif current_video["type"] == "mkv":
                    duration_value = current_video_data.get('duration')
                    if duration_value is None:
                        duration_value = timedelta(seconds=float(results['format']['duration']))
                    current_video['duration'] = duration_value
                    bit_rate = int(results['format']['bit_rate'])
                    current_video['bitRate'] = bit_rate
                    fps_value = current_video.get('fps', 0.0)
                    current_video['nbFrames'] = ceil(
                        fps_value * current_video['duration'].total_seconds()
                    )
                    current_video["quality"] = round(
                        bit_rate / (width_value * height_value), 1
                    ) if width_value > 0 and height_value > 0 else 0.0
                elif current_video["type"] in self.pType:
                    current_video['duration'] = timedelta(seconds=0)
                    current_video['bitRate'] = 0
                    current_video['nbFrames'] = 1
                    current_video['width'] = int(videoStream[0]['width'])
                    current_video['height'] = int(videoStream[0]['height'])
                    current_video['fps'] = 1.0
                    current_video["quality"] = 0.0
                elif current_video["type"] in self.aType:
                    current_video['duration'] = timedelta(seconds=float(results['format']['duration']))
                    current_video['bitRate'] = int(results['format']['bit_rate'])
                    current_video['nbFrames'] = 0
                    current_video['width'] = 0
                    current_video['height'] = 0
                    current_video['fps'] = 0.0
                    current_video["quality"] = 0.0
                elif current_video["type"] in self.sType + ["other"]:
                    current_video['duration'] = timedelta(seconds=0)
                    current_video['bitRate'] = 0
                    current_video['nbFrames'] = 0
                    current_video['width'] = 0
                    current_video['height'] = 0
                    current_video['fps'] = 0.0
                    current_video["quality"] = 0.0
                else:
                    printC(
                        f'Uncovered type "{current_video["type"]}" at "{current_video["name"]}"',
                        "red"
                    )

            except Exception as e:
                printC(f'Unexpected erro "{e.with_traceback(None)}"', "red")
                printC(f'Can not get video info of "{self.vList[videoIndex]["name"]}"', "red")
                self.vList.pop(videoIndex)

        print(f"Get {len(self.vList)} file info")

    def setEncoder(self, h265=True) -> None:
        """
        Set encoder parameters according h265 and GPU usage.\n
        Make sure to be called after self.checkGPUs() and self.selectDevice().

        Parameters:
            h265 (bool):
                _
        """        
        if self.selectedDevice is None:
            self.selectedDevice = {
                "id": -1,
                "name": "CPU",
                "codecs": ["H.264/AVC", "H.265/HEVC"],
            }
            self.gpu = False

        # check h265 possibility
        if (h265) and ("265" not in " ".join(self.selectedDevice["codecs"])):
            printC("Selected device do not has H265 video encoder", "yellow")
            h265 = False

        # summary
        self.h265 = h265
        printC(f'Using {"(h265)" if h265 else "(h264)"} and {"(gpu)" if self.gpu else "(cpu)"} as video encoder', "blue")
        
        # cpu
        if not self.gpu:
            if not h265:
                self.encoder = ' libx264 -crf 1'
            else:
                self.encoder = ' libx265 -crf 0'
            
            self.encoder += (
                ' -preset medium'
            )
        # gpu
        else:
            if not h265:
                self.encoder = ' h264_nvenc -b_ref_mode middle'
            else:
                self.encoder = ' hevc_nvenc'

            self.encoder += (
                f' -gpu {self.selectedDevice["id"]}'
                ' -preset p6'
                ' -tune hq'
                ' -rc vbr'
                ' -rc-lookahead 32'
                ' -multipass fullres'
                ' -spatial_aq 1'
                ' -cq 1'
            )
