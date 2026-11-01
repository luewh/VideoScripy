from __future__ import annotations

import os
import re
import socket
import shlex
import subprocess
from datetime import timedelta
from os import listdir, mkdir, remove
from os.path import isdir, isfile
from pathlib import Path
from shutil import rmtree
from threading import Thread
from time import sleep, time
from typing import Any

import psutil
from alive_progress import alive_bar

from ._types import ProcAsyncReturn, VideoInfo, VideoProcess, VideoScripyContext
from ._utilities import printC


class _ProcessingMixin(VideoScripyContext):
    """Build and run commands and manage long-running process state."""

    @staticmethod
    def _add_ffmpeg_progress(command: str, port: int) -> str | None:
        executable = re.match(
            r'\s*(?:"[^"]*ffmpeg(?:\.exe)?"|[^\s"]*ffmpeg(?:\.exe)?)(?=\s|$)',
            command,
            re.IGNORECASE,
        )
        if executable is None:
            return None

        progress_options = f" -progress tcp://127.0.0.1:{port} -stats_period 0.5"
        return command[:executable.end()] + progress_options + command[executable.end():]

    @staticmethod
    def _format_ffmpeg_progress(fields: dict[str, str]) -> str:
        total_size = fields.get("total_size", "N/A")
        if total_size.isdigit():
            total_size = f"{int(total_size) // 1024}KiB"

        return (
            f"frame={fields.get('frame', 'N/A'):>7} "
            f"fps={fields.get('fps', 'N/A'):>5} "
            f"q={fields.get('stream_0_0_q', 'N/A')} "
            f"size={total_size} "
            f"time={fields.get('out_time', 'N/A')} "
            f"bitrate={fields.get('bitrate', 'N/A')} "
            f"speed={fields.get('speed', 'N/A')}"
        )

    @classmethod
    def _display_ffmpeg_progress(cls, connection: socket.socket, silence: bool) -> bool:
        if silence:
            while True:
                try:
                    if not connection.recv(4096):
                        break
                except ConnectionResetError:
                    break
            return False

        buffer = ""
        fields: dict[str, str] = {}
        displayed = False
        while True:
            try:
                chunk = connection.recv(4096)
            except ConnectionResetError:
                break
            if not chunk:
                break

            buffer += chunk.decode("utf-8", errors="replace")
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                key, separator, value = line.rstrip("\r").partition("=")
                if not separator:
                    continue
                if key == "progress":
                    print(
                        f"\r{cls._format_ffmpeg_progress(fields)}",
                        end="",
                        flush=True,
                    )
                    displayed = True
                    fields.clear()
                else:
                    fields[key] = value

        if displayed:
            print()
        return displayed

    def _getCommand(self, video:VideoInfo, process:str, substep:int = 0) -> str | None:
        """
        Return shell script according to videoInfo and process.\n
        Grouped in one function to handle ffmpeg command together.
        
        Parameters:
            video (VideoInfo):
                element of vList

            process (str):
                VideoProcess.[process].name
        """
        video_data: dict[str, Any] = dict(video)
        videoPath = video['path']
        videoName = video['name']
        command: str | None = None

        videoFps = video_data.get('fps', 0.0)
        if substep == 2 and process == VideoProcess.interpolate.name:
            videoFps = video_data.get("interpolateFps", videoFps)

        hwaccel = ''
        if self.gpu:
            if self.selectedDevice is None:
                return None
            hwaccel = (
                ' -hwaccel cuda'
                f' -hwaccel_device {self.selectedDevice["id"]}'
                ' -hwaccel_output_format cuda'
            )

        # set communFFmpegOut
        output_path = str(Path(self.path) / process / videoName)
        communFFmpegOut = (
            f' -c:v copy -c:a copy -c:s copy'
            f' -c:v:0 {self.encoder} {video_data.get("compressBitRateParam", "")} '
            f' -r {videoFps}'
            f' -y'
            f' "{output_path}"'
        )

        if process == VideoProcess.compress.name:
            command = (
                f' ffmpeg'
                f' {hwaccel}'
                f' -i "{videoPath}"'
                f' -map 0:v -map 0:a? -map 0:s?'
                f' {communFFmpegOut}'
            )

        elif process == VideoProcess.resize.name:
            
            resizeFilter = "scale"
            if self.gpu:
                resizeFilter = "scale_cuda"
            
            command = (
                f' ffmpeg'
                f' {hwaccel}'
                f' -i "{videoPath}"'
                f' -map 0:v -map 0:a? -map 0:s?'
                f' -filter:v:0 {resizeFilter}={video_data.get("resizeWidth", 0)}:{video_data.get("resizeHeight", 0)}'
                f' {communFFmpegOut}'
            )

        elif process in [VideoProcess.upscale.name, VideoProcess.interpolate.name]:
            processOutputPath: str | None = None
            upscaleFactor: int | str | None = None
            getFramesOutputPath = video_data.get("getFramesOutputPath")
            if substep == 0:
                command = (
                    f' ffmpeg'
                    f' -i "{videoPath}"'
                    f' -qscale:v 1 -qmin 1 -qmax 1 -y'
                    f' -r {videoFps}'
                    f' "{getFramesOutputPath}/frame%08d.jpg"'
                )
            else:
                gpuNumber = 0
                if self.gpu:
                    if self.selectedDevice is None:
                        return None
                    gpuNumber = self.selectedDevice["id"] + 1

                if process == VideoProcess.upscale.name:
                    processOutputPath = video_data.get("upscaleOutputPath")
                    upscaleFactor = video_data.get("upscaleFactor")
                elif process == VideoProcess.interpolate.name:
                    processOutputPath = video_data.get("interpolateOutputPath")

                if substep == 1 and process == VideoProcess.upscale.name:
                    if processOutputPath is None or upscaleFactor is None:
                        return None
                    command = (
                        f' {self._resolve_tool("realesrgan-ncnn-vulkan") or "realesrgan-ncnn-vulkan"}'
                        f' -i "{getFramesOutputPath}"'
                        f' -o "{processOutputPath}"'
                    )
                    if upscaleFactor in [2,3,4]:
                        command += f' -n realesr-animevideov3 -s {upscaleFactor}'
                    elif upscaleFactor == "4p":
                        command += ' -n realesrgan-x4plus'
                    elif upscaleFactor == "4pa":
                        command += ' -n realesrgan-x4plus-anime'
                    else:
                        printC(f'Unknown upscale factor "{upscaleFactor}"', "red")
                        return None
                    command += (
                        f' -f jpg -g {gpuNumber}'
                    )
                elif substep == 1 and process == VideoProcess.interpolate.name:
                    if processOutputPath is None:
                        return None
                    command = (
                        f' {self._resolve_tool("ifrnet-ncnn-vulkan") or "ifrnet-ncnn-vulkan"}' +
                        f' -i "{getFramesOutputPath}"' +
                        f' -o "{processOutputPath}"' +
                        f' -m IFRNet_GoPro -g {gpuNumber} -f frame%08d.jpg' +
                        f' -n {video_data.get("interpolateFrame", 0)}'
                    )

                elif substep == 2:
                    if processOutputPath is None:
                        return None
                    imgDecoder = "mjpeg"
                    if self.gpu:
                        imgDecoder = "mjpeg_cuvid"
                    command = (
                        f' ffmpeg'
                        f' {hwaccel}'
                        f' -i "{videoPath}"'
                        f' {hwaccel}'
                        f' -c:v {imgDecoder} -r {videoFps}'
                        f' -i "{processOutputPath}/frame%08d.jpg"'
                        f' -map 1:v:0 -map 0:a? -map 0:s?'
                        f' {communFFmpegOut}'
                    )

        else:
            printC(f'Unknown video process "{process}"', "red")
            return None

        if command is None:
            return None
        
        return command

    def killProc(self) -> None:
        """
        Kill and stop running process of _runProc() and _runProcAsync().\n
        Set self.killed to True if correctly killed.
        """
        
        if self.proc != None:
            parent = psutil.Process(self.proc.pid)
            for child in parent.children(recursive=True):
                child.kill()
            self.killed = True
        
        if self.procAsync != []:
            for procAsync in self.procAsync:
                parent = psutil.Process(procAsync.pid)
                for child in parent.children(recursive=True):
                    child.kill()
            self.killed = True

    def _runProc(self, command:str, processName='', silence=False) -> bool:
        """
        Warp shell script then run it in a minimized and realtime cmd.exe,
        wait till its end and check its exit code.\n
        Return True if exit code is 0 or -1, else False.

        Parameters:
            command (str):
                command line script

            processName (str):
                name shown on the cmd.exe

            silence (str):
                don't print time took and exit code check
        """

        processTime = time()

        printC(f'Running process : {processName}', "blue")

        exit_code_path = str(Path(self.path) / self.EXIT_CODE_FILE_NAME)
        progress_listener: socket.socket | None = None
        if os.name == "nt":
            progress_command = command
            progress_listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            progress_listener.bind(("127.0.0.1", 0))
            progress_listener.listen(1)
            progress_listener.settimeout(0.1)
            progress_command = self._add_ffmpeg_progress(
                command,
                progress_listener.getsockname()[1],
            )
            if progress_command is None:
                progress_listener.close()
                progress_listener = None

            cmd_script = (
                f'cd /d "{self.path}" & {progress_command or command}'
                f' & echo ^!errorLevel^! > "{exit_code_path}"'
            )
            commandWarped = (
                f' start "VideoScripy-{processName}" /min /I /wait /realtime'
                f' cmd /v:on /c "{cmd_script}"'
            )
            self.killed = False
            try:
                self.proc = subprocess.Popen(
                    commandWarped,
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                )
            except OSError:
                if progress_listener is not None:
                    progress_listener.close()
                raise
        else:
            safe_path = shlex.quote(self.path)
            safe_exit_path = shlex.quote(exit_code_path)
            cmd_script = (
                f'cd {safe_path} && {command} ; printf "%s" $? > {safe_exit_path}'
            )
            self.killed = False
            self.proc = subprocess.Popen(
                ["bash", "-lc", cmd_script],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )
        output = bytearray()
        progress_displayed = False
        if progress_listener is not None:
            connection: socket.socket | None = None
            try:
                while connection is None and self.proc.poll() is None:
                    try:
                        connection, _ = progress_listener.accept()
                    except socket.timeout:
                        continue

                if connection is not None:
                    with connection:
                        progress_displayed = self._display_ffmpeg_progress(
                            connection,
                            silence,
                        )
            finally:
                progress_listener.close()
        else:
            line = bytearray()
            stdout = self.proc.stdout
            if stdout is not None:
                while True:
                    character = stdout.read(1)
                    if not character:
                        break

                    output.extend(character)
                    if character in (b"\r", b"\n"):
                        progress_line = line.decode("utf-8", errors="replace")
                        if "frame=" in progress_line and not silence:
                            print(f"\r{progress_line}", end="", flush=True)
                            progress_displayed = True
                        line.clear()
                    else:
                        line.extend(character)

                if line:
                    progress_line = line.decode("utf-8", errors="replace")
                    if "frame=" in progress_line and not silence:
                        print(f"\r{progress_line}", end="", flush=True)
                        progress_displayed = True

        if self.proc.stdout is not None:
            output.extend(self.proc.stdout.read())
            self.proc.stdout.close()
        self.proc.wait()
        self.proc = None

        if progress_displayed:
            print()

        if not silence:
            processTime = time() - processTime
            processTime = timedelta(seconds=processTime)
            print(f"Took : {str(processTime)[:-3]}")

        succeeded = self._checkExitCode(silence)
        if not succeeded and output and not silence:
            print(output.decode("utf-8", errors="replace"))
        return succeeded

    def _checkExitCode(self, silence=False) -> bool:
        """
        Open EXIT_CODE_FILE_NAME file to get process returned code.\n
        Return True if 0 or -1, else False.

        Parameters:
            silence (str):
                don't print exit code check
        """

        filePath = str(Path(self.path) / self.EXIT_CODE_FILE_NAME)

        if not isfile(filePath):
            if not silence:
                printC("Process stoped", "red")
            return False

        else:
            with open(filePath, "r") as f:
                returnCode = int(f.readline().replace("\n",""))
            remove(filePath)

            if returnCode in [0, -1]:
                if not silence:
                    printC('Process end correctly', "green")
                return True
            else:
                if not silence:
                    printC(f'Process end with return code {returnCode}', "red")
                
                # real esrgan can not read/write special character named folder/file eg: ⋟﹏⋞
                if returnCode == -1073740791:
                    printC(f'Real-ESRGAN can not read/write special character named folder/file eg: ⋟﹏⋞', "red")
                return False

    def _runProcAsync(self, command:str) -> None:
        """
        Run shell script in a hidden "cmd.exe".\n
        Warning ! Output path must be absolute.\n
        Must call _runProcAsyncWait() to get its return code and content.
        
        Parameters:
            command (str):
                shell script command, _getCommand return command
        """
        self.killed = False
        self.procAsync.append(
            subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        )

    def _runProcAsyncWait(self) -> list[ProcAsyncReturn]:
        """
        Wait all "asynchronous" process.\n
        Return list of process's {returnCode, stdout}
        """
        result:list[ProcAsyncReturn] = []
        for proc in self.procAsync:
            out, _ = proc.communicate()
            result.append({
                "returnCode": proc.returncode,
                "stdout": out,
            })
        self.procAsync.clear()
        return result

    def _frameWatch(self, outDir:str, total:int) -> None:
        """
        Track video frame process with progress bar in while loop,
        Set attribute self.stop_threads to True to stop.

        Parameters:
            outDir (str):
                process output directory, where progress increase
            
            total (int):
                when to stop
        """
        self.stop_threads = False
        # wait 1s to avoid print overlap with "Running process"
        sleep(1)
        alreadyProgressed = len(listdir(outDir))
        restToProgress = total - alreadyProgressed
        print(f"Already progressed : {alreadyProgressed}/{total}")
        print(f"Remain to progress : {restToProgress}/{total}")

        progressedPrev = 0
        with alive_bar(total) as bar:
            if alreadyProgressed != 0:
                bar(alreadyProgressed, skipped=True)
            while len(listdir(outDir)) < total:
                sleep(1)
                progressed = len(listdir(outDir)) - alreadyProgressed
                bar(progressed - progressedPrev)
                progressedPrev = progressed

                if self.stop_threads:
                    break
            
            progressed = len(listdir(outDir)) - alreadyProgressed
            bar(progressed - progressedPrev)
            progressedPrev = progressed

    def _frameWatchStart(self, outDir:str, total:int) -> None:
        """
        Run _frameWatch() in a thread.

        Parameters:
            outDir (str):
                process output directory, where progress increase
            
            total (int):
                when to stop
        """
        self.watch = Thread(
            target=self._frameWatch,
            args=(outDir, total)
        )
        self.watch.start()

    def _frameWatchStop(self) -> None:
        """
        Stop the _frameWatch() thread by setting attribute self.stop_threads to True.
        """
        self.stop_threads = True
        while self.watch.is_alive():
            pass

    def _getFrames(self, video:VideoInfo, process:VideoProcess) -> bool:
        """
        Transform video to frames

        Parameters:
            video (VideoInfo):
                element of vList
        """
        video_data: dict[str, Any] = dict(video)
        getFramesOutputPath = video_data.get("getFramesOutputPath")
        if getFramesOutputPath is None:
            printC("Missing frame output path for video", "red")
            return False
        # check if get frame is necessary
        if isdir(getFramesOutputPath):

            # get number of frames, 3rd round
            processed_frames_dir = Path(getFramesOutputPath) / "processed"
            if isdir(str(processed_frames_dir)):
                obtainedFrames = (
                    len(listdir(getFramesOutputPath)) - 1
                    + len(listdir(str(processed_frames_dir)))
                )
            # get number of frames, less than 3rd round
            else:
                obtainedFrames = len(listdir(getFramesOutputPath))

            # equal to what it should has, allow +- 1 frame difference
            if abs(obtainedFrames - int(video_data.get("nbFrames", 0))) <= 1:
                printC("No need to get frames", "yellow")
                self.killed = False
                return True
            else:
                printC("Missing frames, regenerate frames needed", "yellow")
                rmtree(getFramesOutputPath)

        # create new temporary frames folder
        mkdir(getFramesOutputPath)

        command = self._getCommand(video, process.name, substep=0)
        if command is None:
            printC("Failed to prepare frame extraction command", "red")
            return False
        result = self._runProc(command, process.value[0])

        # check frames count
        obtainedFrames = len(listdir(getFramesOutputPath))
        expectedFrames = int(video_data.get("nbFrames", 0))
        if obtainedFrames != expectedFrames:
            printC(
                f'Warning, obtained frames {obtainedFrames} '
                f'is not equal to video frames {expectedFrames}',
                "yellow"
            )
            # modify frame number if +- 1 frame difference
            if abs(expectedFrames - obtainedFrames) <= 1:
                video["nbFrames"] = obtainedFrames
        
        return result

    def pre_compress(self, video:VideoInfo, width:int, height:int, quality:float) -> bool:
        """
        Compute compressBitRate and compressBitRateParam, to limit video bit rate\n
        Return True if compression is needed else False
        
        Parameters:
            video (VideoInfo):
                element of vList

            width (int):
                video width

            height (int):
                video height

            quality (float):
                video bit rate = width x height x quality
        
        """
        # compute compression bit rate
        video_data: dict[str, Any] = dict(video)
        current_bitrate = int(video_data.get("bitRate", 0) or 0)
        current_quality = float(video_data.get("quality", 0.0) or 0.0)
        compressBitRate = width * height * quality

        print(f'{current_bitrate/1_000:_.0f} Kbits/s --> {compressBitRate/1_000:_.0f} Kbits/s')

        video['compressBitRate'] = compressBitRate
        video['compressBitRateParam'] = (
            f' -maxrate:v {compressBitRate}'
            f' -bufsize:v {compressBitRate*2} '
        )

        # check if compression needed
        if round(current_quality - quality,1) < self.COMPRESS_TOLERENCE:
            return False
        else:
            return True
