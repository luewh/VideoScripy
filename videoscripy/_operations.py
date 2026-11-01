from __future__ import annotations

import json
from datetime import timedelta
from math import ceil, gcd
from os import mkdir, remove, rename, walk
from os.path import isdir
from pathlib import Path
from shutil import rmtree
from time import time
from typing import Any, Callable

from PIL import Image

from ._types import VideoInfo, VideoProcess, VideoScripyContext
from ._utilities import printC


def _serial(
    func: Callable[..., str],
) -> Callable[..., None]:
    """
    Run a video operation serially for every item in vList.
    """
    def wrapper(
        self: Any,
        *args: object,
        **kwargs: object,
    ) -> None:
        results:list[str] = []
        for index, video in enumerate(self.vList):
            self.noticeProcessBegin()
            # show current video
            print(f'{index+1}/{len(self.vList)}'.center(20, '-'))
            print(video["name"])

            result = func(self, video, *args, **kwargs)
            results.append(result)
            if result == "stop":
                break

        self.noticeProcessEnd()
        self.removeEmptyFolder()

        # complete results if stopped
        if len(results) < len(self.vList):
            results += ["x"]*(len(self.vList)-len(results))
        # complete results to multiple of 5
        if len(results)%5 != 0:
            results += [" "]*(5-len(results)%5)
        # show SUMMARY
        if len(results) != 0:
            print("SUMMARY :", end='')
            for index, result in enumerate(results):
                if index%5 == 0:
                    print("\n"+"-"*36)
                    print("|", end='')
                print(result.center(6,' ')+"|", end='')
            print("\n"+"-"*36)

    return wrapper


class _OperationsMixin(VideoScripyContext):
    """Implement video transformations and stream operations."""

    @_serial
    def compress(self, video:VideoInfo, quality:float=3.0) -> str:
        """
        Reduce video bit rate\n
        Return "end", "err", "skip" or "stop"

        Parameters:
            quality (float):
                video bit rate = width x height x quality
        """
        
        process = VideoProcess.compress.name
        # create output folder
        outputFolder = self._path(process)
        if not isdir(outputFolder):
            mkdir(outputFolder)

        # skip not video type
        if video["type"] not in self.vType:
            printC('Skipped', "yellow")
            return "skip"

        video_data: dict[str, Any] = dict(video)
        width = int(video_data.get('width', 0) or 0)
        height = int(video_data.get('height', 0) or 0)

        # show current process changing info
        print('{}x{}'.format(width, height))

        if not self.pre_compress(video, width, height, quality):
            printC('Skipped', "yellow")
            return "skip"

        command = self._getCommand(video, process)
        if command is None:
            return "err"
        result = self._runProc(command, process)

        # stop whole process if killProc() called
        if self.killed:
            return "stop"
        
        # skip next steps if process not correctly ended
        if not result:
            return "err"
    
        self.removeEmptyFolder(outputFolder)
        return "end"

    @_serial
    def resize(self, video:VideoInfo, setWidth:int, setHeight:int, quality:float=3.0) -> str:
        """
        Resize video\n
        Return "end", "err", "skip" or "stop"

        Parameters:
            setWidth (int):
                -1 to let it by default

            setHeight (int):
                -1 to let it by default

            quality (float):
                video bit rate = width x height x quality
        """
        
        process = VideoProcess.resize.name
        # create output folder
        outputFolder = self._path(process)
        if not isdir(outputFolder):
            mkdir(outputFolder)
            
        # skip not video type
        if video["type"] not in self.vType:
            printC('Skipped', "yellow")
            return "skip"

        video_data: dict[str, Any] = dict(video)
        width = int(video_data.get('width', 0) or 0)
        height = int(video_data.get('height', 0) or 0)

        # compute setWidth and setHeight
        if setWidth == -1 and setHeight == -1:
            widthResize = width
            heightResize = height
        elif setWidth == -1:
            widthResize = ceil(width * setHeight/height)
            heightResize = setHeight
        elif setHeight == -1:
            widthResize = setWidth
            heightResize = ceil(height * setWidth/width)
        else:
            widthResize = setWidth
            heightResize = setHeight
        
        # to positive size
        widthResize = abs(widthResize)
        heightResize = abs(heightResize)

        # even size
        if widthResize%2 != 0:
            widthResize += 1
        if heightResize%2 != 0:
            heightResize += 1

        # show current process changing info
        print(f'{width}x{height} --> {widthResize}x{heightResize}')

        # ratio warning
        if width/height != widthResize/heightResize:
            sizeGCD = gcd(width, height)
            newSizeGCD = gcd(widthResize, heightResize)
            printC('Warning, rize ratio will be changed', "yellow")
            printC(
                f'{int(width/sizeGCD)}:{int(height/sizeGCD)} --> '
                f'{int(widthResize/newSizeGCD)}:{int(heightResize/newSizeGCD)}',
                "yellow"
            )
        
        # skip if same size
        # skip if bigger size
        if ((widthResize == width and heightResize == height)
            or (widthResize > width and heightResize > height)):
            printC("Skipped", "yellow")
            return "skip"
        
        video["resizeWidth"] = widthResize
        video["resizeHeight"] = heightResize

        self.pre_compress(video, widthResize, heightResize, quality)

        command = self._getCommand(video, process)
        if command is None:
            return "err"
        result = self._runProc(command, process)

        # stop whole process if killProc() called
        if self.killed:
            return "stop"
        
        # skip next steps if process not correctly ended
        if not result:
            return "err"
        
        self.removeEmptyFolder(outputFolder)
        return "end"

    @_serial
    def upscale(self, video:VideoInfo, upscaleFactor:int=2, quality:float=3) -> str:
        """
        Upscale video\n
        Return "end", "err", "skip" or "stop"

        Parameters:
            upscaleFactor (int):
                2, 3 or 4
            
            quality (float):
                video bit rate = width x height x quality
        """

        process = VideoProcess.upscale
        # create output folder
        outputFolder = self._path(process.name)
        if not isdir(outputFolder):
            mkdir(outputFolder)
            
        # skip not video or picture type
        if video["type"] not in self.vType + self.pType:
            printC('Skipped', "yellow")
            return "skip"
        
        name = video['name']
        video_data: dict[str, Any] = dict(video)
        width = int(video_data.get('width', 0) or 0)
        height = int(video_data.get('height', 0) or 0)

        # save and show size change
        widthUpscale = width * upscaleFactor
        heightUpscale = height * upscaleFactor
        print(f'{width}x{height} --> {widthUpscale}x{heightUpscale}')



        # shortcut for picture type
        gpuNumber = 0
        if self.gpu:
            if self.settedDevice is None:
                return "skip"
            gpuNumber = self.settedDevice["id"]+1
        
        if video["type"] in self.pType:
            command = (
                f' {self._resolve_tool("realesrgan-ncnn-vulkan") or "realesrgan-ncnn-vulkan"}'
                f' -i "{video["path"]}"'
                f' -o "{str(Path(self.path) / process.name / name)}"'
                f' -n realesr-animevideov3 -s {upscaleFactor}'
                f' -f jpg -g {gpuNumber}'
            )
            result = self._runProc(command, process.value[1])

            # stop whole process if killProc() called
            if self.killed:
                return "stop"
            
            # skip next steps if process not correctly ended
            if not result:
                return "err"
            
            return "end"



        self.pre_compress(video, widthUpscale, heightUpscale, quality)

        getFramesOutputPath = self._path(f"{name}_tmp_frames")
        video["getFramesOutputPath"] = str(getFramesOutputPath)

        result = self._getFrames(video, process)
        
        # stop whole process if killProc() called
        if self.killed:
            return "stop"
        
        # skip next steps if process not correctly ended
        if not result:
            return "err"

        upscaleOutputPath = self._path(f"{name}_{process.name}x{upscaleFactor}_frames")
        # new upscaling
        if not isdir(upscaleOutputPath):
            print(f'New upscaling')
            mkdir(upscaleOutputPath)
        # continue upscaling
        else:
            print(f'Continue upscaling')
            for _, _, files in walk(upscaleOutputPath):

                # create processed folder
                processedFolder = str(getFramesOutputPath / "processed")
                if not isdir(processedFolder):
                    mkdir(processedFolder)

                # move frame to processed folder except last two
                for framesUpscaled in files[:-2]:
                    try:
                        rename(
                            str(getFramesOutputPath / framesUpscaled),
                            str(Path(processedFolder) / framesUpscaled),
                        )
                    # do nothing to already moved
                    except FileNotFoundError:
                        pass

                # remove last two upscaled frames
                for lastTwoUpscaled in files[-2:]:
                    remove(str(Path(upscaleOutputPath) / lastTwoUpscaled))

                break

        # frames watch
        self._frameWatchStart(str(upscaleOutputPath), int(video_data.get("nbFrames", 0) or 0))

        video["upscaleOutputPath"] = str(upscaleOutputPath)
        video["upscaleFactor"] = upscaleFactor
        command = self._getCommand(video, process.name, substep=1)
        if command is None:
            return "err"
        result = self._runProc(command, process.value[1])
        
        # frames watch end
        self._frameWatchStop()

        # stop whole process if killProc() called
        if self.killed:
            return "stop"
        
        # skip next steps if process not correctly ended
        if not result:
            return "err"

        # # remove frames
        # rmtree(getFramesOutputPath)
        
        # upscaled frames to video
        command = self._getCommand(video, process.name, substep=2)
        if command is None:
            return "err"
        result = self._runProc(command, process.value[2])

        # stop whole process if killProc() called
        if self.killed:
            return "stop"
        
        # skip next steps if process not correctly ended
        if not result:
            return "err"
        
        # # remove upscaled frames
        # rmtree(upscaleOutputPath)

        self.removeEmptyFolder(outputFolder)
        return "end"

    @_serial
    def interpolate(self, video:VideoInfo, fpsInterp:float=30.0, quality:float=3) -> str:
        """
        Interpolate video to increase fps\n
        Return "end", "err", "skip" or "stop"

        Parameters:
            fps (float):
                must > than original fps

            quality (float):
                video bit rate = width x height x quality
        """
        
        process = VideoProcess.interpolate
        # create output folder
        outputFolder = self._path(process.name)
        if not isdir(outputFolder):
            mkdir(outputFolder)
            
        # skip not video type
        if video["type"] not in self.vType:
            printC('Skipped', "yellow")
            return "skip"

        name = video['name']
        video_data: dict[str, Any] = dict(video)
        width = int(video_data.get('width', 0) or 0)
        height = int(video_data.get('height', 0) or 0)
        fps = float(video_data.get('fps', 0.0) or 0.0)
        duration = video_data.get('duration')
        if duration is None:
            duration = timedelta(seconds=0)

        # check if interpolation needed
        if fpsInterp < fps:
            print(fpsInterp, '<', fps)
            printC("Skipped", "yellow")
            return "skip"

        # save and show interpolate change
        interpolateFrame = ceil(duration.total_seconds() * fpsInterp)
        video["interpolateFrame"] = interpolateFrame

        print(f'{fps}fps --> {fpsInterp}fps')

        self.pre_compress(video, width, height, quality)
        
        getFramesOutputPath = self._path(f"{name}_tmp_frames")
        video["getFramesOutputPath"] = str(getFramesOutputPath)
        video['interpolateFps'] = fpsInterp
        result = self._getFrames(video, process)

        # stop whole process if killProc() called
        if self.killed:
            return "stop"
        
        # skip next steps if process not correctly ended
        if not result:
            return "err"

        interpolateOutputPath = self._path(f"{name}_{process.name}_frames")
        video["interpolateOutputPath"] = str(interpolateOutputPath)

        # empty interpolate frames folder
        if isdir(interpolateOutputPath):
            rmtree(interpolateOutputPath)

        # new frames interpolate
        mkdir(interpolateOutputPath)

        # frames watch
        self._frameWatchStart(str(interpolateOutputPath), interpolateFrame)
        
        command = self._getCommand(video, process.name, substep=1)
        if command is None:
            return "err"
        result = self._runProc(command, process.value[1])
        
        # frame watch end
        self._frameWatchStop()

        # stop whole process if killProc() called
        if self.killed:
            return "stop"
        
        # skip next steps if process not correctly ended
        if not result:
            return "err"

        # remove frames
        rmtree(getFramesOutputPath)

        # interpolate frames to video
        command = self._getCommand(video, process.name, substep=2)
        if command is None:
            return "err"
        result = self._runProc(command, process.value[2])

        # stop whole process if killProc() called
        if self.killed:
            return "stop"
        
        # skip next steps if process not correctly ended
        if not result:
            return "err"

        # remove interpolated frames
        rmtree(interpolateOutputPath)

        self.removeEmptyFolder(outputFolder)
        return "end"

    @_serial
    def preview(self, video:VideoInfo, gridWidth:int=3, gridHeight:int=2) -> str:
        """
        Generate a grid of images\n
        Return "end", "err", "skip" or "stop"

        Parameters:
            gridWidth (int):
                number of column

            gridHeight (int):
                number of row
        """

        process = VideoProcess.preview.name
        # create output folder
        outputFolder = self._path(process)
        if not isdir(outputFolder):
            mkdir(outputFolder)

        gridNb = gridWidth*gridHeight
            
        # skip not video type
        if video["type"] not in self.vType:
            printC('Skipped', "yellow")
            return "skip"

        video_data: dict[str, Any] = dict(video)
        duration_value = video_data.get('duration')
        if duration_value is None:
            duration_value = timedelta(seconds=0)
        duration = duration_value.total_seconds()
        width = int(video_data.get('width', 0) or 0)
        height = int(video_data.get('height', 0) or 0)

        outputName = video['name'].replace(f".{video['type']}",".png")
        
        printC(f'Running process : {process}', "blue")
        processTime = time()

        if gridNb != 1:
            chopTime = 0.233 * duration/(gridNb-1)
        else:
            chopTime = 0.233 * duration
            
        for imgNb in range(gridNb):
            
            if imgNb == 0:
                imgTime = chopTime
            elif imgNb == gridNb-1:
                imgTime = duration - chopTime
            else:
                imgTime = chopTime + imgNb*(duration-2*chopTime)/(gridNb-1)

            frame_path = self._path(process, f"{imgNb}.png")
            command = (
                f' ffmpeg'
                f' -ss {imgTime}'
                f' -i "{video["path"]}"'
                f' -frames:v 1'
                f' -y'
                f' "{frame_path}"'
            )
            self._runProcAsync(command)
        self._runProcAsyncWait()
        
        # stop whole process if killProc() called
        if self.killed:
            return "stop"

        newImageWidth = width*gridWidth
        newImageHeight = height*gridHeight
        newImage = Image.new('RGB', (newImageWidth,newImageHeight))

        imgNb = 0
        for ghCount in range(gridHeight):
            for gwCount in range(gridWidth):
                imTempPath = self._path(process, f"{imgNb}.png")
                imgNb += 1
                imTemp = Image.open(str(imTempPath))
                newImage.paste(imTemp, (gwCount*width, ghCount*height))

        newImage.save(str(self._path(process, outputName)))

        for imgNb in range(gridNb):
            imTempPath = self._path(process, f"{imgNb}.png")
            imgNb += 1
            remove(str(imTempPath))

        processTime = time() - processTime
        processTime = timedelta(seconds=processTime)
        print(f"Took :{str(processTime)[:-3]}")

        self.removeEmptyFolder(outputFolder)
        return "end"

    @_serial
    def frame(self, video:VideoInfo) -> str:
        """
        Get bitrate of each video frame,\n
        results are stored in frameBytePerPacket and frameBytePerSecond\n
        Return "end", "err", "skip" or "stop"
        """

        # skip not video type
        if video["type"] not in self.vType:
            printC('Skipped', "yellow")
            return "skip"
        
        processTime = time()

        # print(video["duration"], "x", video["fps"])
        # print(
        #     "=>", video["duration"].total_seconds()*video["fps"],
        #     "=", video["nbFrames"]
        # )

        # run probe
        command = (
            f' ffprobe'
            f' -i "{video["path"]}"'
            f' -select_streams v:0'
            f' -show_entries packet=pts_time,size'
            f' -of json'
        )
        printC(f'Running process : frame', "blue")
        self._runProcAsync(command)

        # wait and retrieve results
        result = self._runProcAsyncWait()[0]

        # stop whole process if killProc() called
        if self.killed:
            return "stop"
        
        # skip next steps if process not correctly ended
        if result['returnCode'] != 0:
            printC(f'FFprobe error at {video["name"]}', "red")
            return "err"
        
        # convert stdout to json format
        result = (
            json.loads(result['stdout'].decode('utf-8'))
        )

        # get info
        packet_data = result["packets"]
        if not packet_data:
            printC(f'No frame packets found for {video["name"]}', "yellow")
            return "err"
        
        # convert str to value
        for p_d in packet_data:
            p_d["pts_time"] = float(p_d["pts_time"])
            p_d["size"] = int(p_d["size"])

        # sort by picture timestamp
        packet_data = sorted(packet_data, key=lambda x : x["pts_time"])
        
        # check sort
        pts_time_prev = float('-inf')
        for p_d in packet_data:
            if p_d["pts_time"] - pts_time_prev < 0:
                printC(
                    f'wrong'
                    f'{p_d["pts_time"]} {pts_time_prev}'
                    f'{p_d["pts_time"] - pts_time_prev}'
                    f'{p_d["pts_time"] - pts_time_prev < 0}'
                    f'{video["name"]}',
                    "red"
                )
                return "err"
            pts_time_prev = p_d["pts_time"]
        
        # per packet to per second
        second_data = []
        switch_time = 1
        size_cumul = 0
        for p_d in packet_data:

            if p_d["pts_time"] >= switch_time:
                switch_time += 1
                second_data.append({
                    "pts_time": p_d["pts_time"],
                    "size" : size_cumul
                })
                size_cumul = 0
            else:
                size_cumul += p_d["size"]

        if size_cumul > 0:
            second_data.append({
                "pts_time": packet_data[-1]["pts_time"],
                "size" : size_cumul
            })

        # re-struct data
        packet_data_new = {}
        packet_data_new["pts_time"] = [x["pts_time"] for x in packet_data]
        packet_data_new["size"] = [x["size"] for x in packet_data]
        second_data_new = {}
        second_data_new["pts_time"] = [x["pts_time"] for x in second_data]
        second_data_new["size"] = [x["size"] for x in second_data]

        # float to datetime
        packet_data_new["pts_time"] = [self.DAY_ZERO + timedelta(seconds=f) for f in packet_data_new["pts_time"]]
        second_data_new["pts_time"] = [self.DAY_ZERO + timedelta(seconds=f) for f in second_data_new["pts_time"]]

        # write info
        video["frameBytePerPacket"] = packet_data_new
        video["frameBytePerSecond"] = second_data_new
        
        processTime = time() - processTime
        processTime = timedelta(seconds=processTime)
        print(f"Took : {str(processTime)[:-3]}")

        return "end"

    def stream(self) -> None:
        """
        Merge selected stream of multiple videos into one video.
        And also modify metadata (title language).
        """
        
        self.noticeProcessBegin()

        process = VideoProcess.stream.name
        # create output folder
        outputFolder = self._path(process)
        if not isdir(outputFolder):
            mkdir(outputFolder)

        print(f'{len(self.vList)}'.center(20, '-'))

        # get first video name and type
        hasVideo = False
        videoType = ""
        videoName = ""
        videoDuration: timedelta | None = None
        for video in self.vList:
            if video["type"] in self.vType:
                videoType = video["type"]
                videoName = video["name"]
                video_data: dict[str, Any] = dict(video)
                videoDuration = video_data.get("duration")
                if videoDuration is None:
                    videoDuration = timedelta(seconds=0)
                hasVideo = True
                break
        # end process if no video
        if not hasVideo:
            self.removeEmptyFolder(outputFolder)
            self.noticeProcessEnd()
            return
        
        # warn different video duration
        for video in self.vList:
            video_data: dict[str, Any] = dict(video)
            duration_value = video_data.get('duration')
            if (videoDuration is not None
                and video["type"] in self.vType
                and videoDuration != duration_value
            ):
                printC(f'Warning, "{video["name"]}" has different duration', "yellow")
                printC(f'{videoDuration} -- {duration_value}', "yellow")
        
        # subtitle copy param
        subtitleCopy = '-c:s mov_text'
        if videoType == "mkv":
            subtitleCopy = ''
        
        # order stream by video, audio, subtitle
        commandInputs = ""
        commandMap = ""
        orderedStreams = [[],[],[],[]]
        videoIndex = 0
        for videoIndex, video in enumerate(self.vList):
            video_data: dict[str, Any] = dict(video)
            streams = video_data.get("streams", [])
            print(video['name'])
            commandInputs += f'-i "{video["path"]}" '
            
            for stream in streams:
                if stream["codec_type"] == "video":
                    orderedStreams[0].append({
                        "videoIndex":videoIndex,
                        "stream":stream,
                        "fileType":video["type"],
                    })
                elif stream["codec_type"] == "audio":
                    orderedStreams[1].append({
                        "videoIndex":videoIndex,
                        "stream":stream,
                        "fileType":video["type"],
                    })
                elif stream["codec_type"] == "subtitle":
                    orderedStreams[2].append({
                        "videoIndex":videoIndex,
                        "stream":stream,
                        "fileType":video["type"],
                    })
                else:
                    orderedStreams[3].append({
                        "videoIndex":videoIndex,
                        "stream":stream,
                        "fileType":video["type"],
                    })
        # flatten
        orderedStreams = [
            stream 
            for streamType in orderedStreams 
            for stream in streamType
        ]

        commandMetadata = ""
        outputStreamCount = 0
        for stream in orderedStreams:
            if stream["stream"]["selected"]:

                commandMap += f'-map {stream["videoIndex"]}:{stream["stream"]["index"]} '

                # remove time codec for mp4
                if stream["fileType"] == "mp4":
                    commandMap += f'-map -{videoIndex}:d? '

                # set picture disposition to attached_pic
                if stream["fileType"] in self.pType and stream["fileType"] != "webp":
                    commandMetadata += f'-disposition:{outputStreamCount} attached_pic '

                # clear title tag to avoid double title
                # allow double title tag, handler_name for mp4 ffprobe
                commandMetadata += f'-metadata:s:{outputStreamCount} title="{stream["stream"]["title"]}" '
                commandMetadata += f'-metadata:s:{outputStreamCount} handler_name="{stream["stream"]["title"]}" '

                commandMetadata += f'-metadata:s:{outputStreamCount} language={stream["stream"]["language"]} '
                outputStreamCount += 1
                    
        output_path = str(Path(self.path) / process / videoName)
        command = (
            f' ffmpeg'
            f' {commandInputs}'
            f' {commandMap}'
            f' -c copy'
            f' {subtitleCopy}'
            f' {commandMetadata}'
            f' -y'
            f' "{output_path}"'
        )
        self._runProc(command, process)
            
        self.removeEmptyFolder(outputFolder)
        self.noticeProcessEnd()
