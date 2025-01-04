# built-in
import subprocess
import json
from threading import Thread
from pathlib import Path
from datetime import timedelta
from shutil import rmtree
from os import walk, mkdir, remove, listdir, getcwd, rmdir, rename
from os.path import isdir, isfile
from time import time, sleep
from math import ceil, gcd
from typing import TypedDict
from enum import Enum

# dependencies
from alive_progress import alive_bar
from playsound import playsound
from PIL import Image
import psutil
from colorama import init, Fore, Style
init()


# from VideoScripy import *
__all__ = [
    'VideoScripy',
    'VideoInfo', 'VideoProcess', 'ProcAsyncReturn', 'StreamInfo',
    'run',
]


class ProcAsyncReturn(TypedDict):
    returnCode : int
    stdout: str

class StreamInfo(TypedDict):
    index : int
    codec_type : str
    codec_name : str

class VideoInfo(TypedDict):
    """
    VideoScripy.vList typing
    """
    type: str
    path: str
    name: str
    duration: timedelta
    bitRate: int
    width: int
    height: int
    fps: float
    nbFrames: int
    streams : list[StreamInfo]
    fileSize : int

class VideoProcess(Enum):
    """
    Implemented processes and its substep
    """
    optimize = "optimize"
    resize = "resize"
    upscale = ["getFrames", "upscale", "frameToVideo"]
    interpolate = ["getFrames", "interpolate", "frameToVideo"]
    merge = "merge"
    preview = "preview"



def printC(text, color:str=None):
    """
    print with color : red green blue yellow
    """
    if color == "red":
        print(Fore.RED, end='')
    elif color == "green":
        print(Fore.GREEN, end='')
    elif color == "blue":
        print(Fore.BLUE, end='')
    elif color == "yellow":
        print(Fore.YELLOW, end='')
    else:
        pass
    print(text + Style.RESET_ALL)

def removeEmptyFolder(folderName:str):
    try:
        rmdir(folderName)
    except:
        pass

def noticeProcessBegin():
    sound = "./assets/typewriter_carriage_return.mp3"
    try:
        playsound(sound, block=False)
    except:
        pass

def noticeProcessEnd():
    sound = "./assets/typewriter_bell.mp3"
    try:
        playsound(sound, block=True)
    except:
        pass



class VideoScripy():
    """
    Class for video processesing

    Attributes:
        path (str):
            absolute folder path of running script

        vList ([VideoInfo]): 
            list of dictionnary contanning info of scanned videos
            such as path, duration, bit rate etc.

        vType ([str]):
            supported video type are .mp4 and .mkv
        
        folderSkip ([str]):
            self generated folders, skiped when scanning

        OPTIMIZE_TOLERENCE (float):
            do not optimize if optimizedBitRate * OPTIMIZE_TOLERENCE < bitRate

        highQualityParam (str):
            hevc_nvenc high quality parameters
        
        proc (subprocess.Popen):
            running video process : ffmpeg, Real-ESRGAN, or Ifrnet
        
        killed (bool):
            indicate that kill video process is done
        
    """

    def __init__(self) -> None:
        """
        Initialise attributes
        """

        self.path = getcwd()
        
        self.vList:list[VideoInfo] = []
        self.vType = ["mp4","mkv"]
        self.folderSkip = [p.name for p in VideoProcess]
        self.OPTIMIZE_TOLERENCE = 1.15
        
        self.h265 = True
        self.gpu = True
        self.setEncoder(h265=True, gpu=True)

        self.proc:subprocess.Popen = None
        self.killed = False
        self.stop_threads = False
        self.procAsync:list[subprocess.Popen] = []

        self.EXIT_CODE_FILE_NAME = "exitCode.txt"

        self.checkTools()
        
    def checkTools(self) -> None:
        tools = {
            "FFmpeg": "ffmpeg -version",
            "FFprobe": "ffprobe -version",
            "Real-ESRGAN": "realesrgan-ncnn-vulkan.exe -h",
            "IFRNet": "ifrnet-ncnn-vulkan.exe -h",
        }
        for tool, cmd in tools.items():
            self._runProcAsync(cmd)

        results = self._runProcAsyncWait()
        for tool, result in zip(tools, results):
            if result["returnCode"] in [0, 4294967295]:
                printC(f'{tool} found', 'green')
            else:
                printC(f'{tool} not found, please check if it is in environment "PATH"', 'red')


    # get video related
    def setPath(self, path:str="") -> bool:
        """
        Set attributes path, return setting result

        Parameters:
            path (str):
                set to "" will use getcwd() as default path
        
        Used attributes:
            path
        """
        if path == "":
            self.path = getcwd()
            printC(f'Path set to default "{self.path}"', "green")
            return True
        else:
            if isdir(path):
                self.path = path
                printC(f'Path correctly set to "{self.path}"', "green")
                return True
            else:
                printC(f'Path "{path}" do not exist', "red")
                return False
    
    def getVideo(self, folderDepthLimit:int=0) -> None:
        """
        Set attributes vList's path and name by file scan

        Parameters:
            folderDepthLimit (int):
                limit the scan depth
        
        Used attributes:
            path
            vList
            vType
            folderSkip
        """
        # empty video list
        self.vList = []

        for root, _, files in walk(self.path):
            # get current root's depth
            currentDepth = len(root.replace(self.path,"").split("\\"))-1

            # skip too deep folder
            if currentDepth > folderDepthLimit and folderDepthLimit != -1:
                continue
            # skip folder
            skip = False
            for folderSkip in self.folderSkip:
                if Path(root).name == folderSkip:
                    printC(f'Self generated folder "{folderSkip}" skiped', "yellow")
                    skip = True
                    break
            if skip:
                continue

            # get videos
            for file in files:
                # skip not supported type
                fileFormat = file.split(".")[-1].lower()
                if fileFormat not in self.vType:
                    continue
                # check &
                if "&" in root+"\\"+file:
                    printC(f'"&" must not used in path or file name', "yellow")
                    printC(f'Skipped "{file}"', "yellow")
                    continue
                self.vList.append({
                    "type" : fileFormat,
                    "path" : root+"\\"+file,
                    "name" : (root+"\\"+file).replace(self.path+'\\','').replace('\\','__')
                })
            
            # stop scan for perfomance
            if folderDepthLimit == 0:
                break
        
        # order by name
        self.vList.sort(key= lambda video: video['name'])
    
    def getVideoInfo(self) -> None:
        """
        Set attributes vList's video properties with ffprobe
        
        Used attributes:
            vList
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
        results = self._runProcAsyncWait()
        for index in range(len(results)-1,-1,-1):
            if results[index]['returnCode'] != 0:
                print(f'FFprobe error, remove {self.vList[index]["name"]}')
                # delete errored video
                self.vList.pop(index)
                results.pop(index)
            else:
                # convert stdout to json format
                results[index] = (
                    json.loads(results[index]['stdout'].decode('utf-8'))
                )

        # get info
        for videoIndex in range(len(self.vList)-1,-1,-1):
            try:
                streamInfo = []
                videoStream = []
                # get stream info
                for stream in results[videoIndex]['streams']:
                    try :
                        codecName = stream["codec_name"]
                    except:
                        codecName = stream["codec_tag_string"]
                    streamInfo.append({
                        "index": int(stream["index"]),
                        "codec_type": stream["codec_type"],
                        "codec_name": codecName,
                    })
                    if stream['codec_type'] == 'video':
                        videoStream.append(stream)

                # warn more than video stream
                if len(videoStream) > 1:
                    printC(
                        f'More than 1 video stream found in "{self.vList[videoIndex]["name"]}", '
                        f'only the first will be processed', "yellow"
                    )
                videoStream = videoStream[0]

                # write info
                self.vList[videoIndex]['streams'] = streamInfo
                self.vList[videoIndex]['fileSize'] = int(results[videoIndex]['format']['size'])
                self.vList[videoIndex]['width'] = int(videoStream['width'])
                self.vList[videoIndex]['height'] = int(videoStream['height'])
                num, denom = videoStream['r_frame_rate'].split('/')
                self.vList[videoIndex]['fps'] = round(float(num)/float(denom),2)
                # mp4
                try:
                    self.vList[videoIndex]['duration'] = timedelta(seconds=float(videoStream['duration']))
                    self.vList[videoIndex]['bitRate'] = int(videoStream['bit_rate'])
                    self.vList[videoIndex]['nbFrames'] = int(videoStream['nb_frames'])
                # mkv
                except KeyError:
                    self.vList[videoIndex]['duration'] = timedelta(seconds=float(results[videoIndex]['format']['duration']))
                    self.vList[videoIndex]['bitRate'] = int(results[videoIndex]['format']['bit_rate'])
                    self.vList[videoIndex]['nbFrames'] = ceil(
                        self.vList[videoIndex]['fps'] 
                        * self.vList[videoIndex]['duration'].total_seconds()
                    )
            
            except Exception as e:
                printC(f'Unexpected erro "{e.with_traceback()}"', "red")
                printC(f'Can not get video info of "{self.vList[videoIndex]["name"]}"', "red")
                # delete errored video
                self.vList.pop(videoIndex)

        print(f"Get {len(self.vList)} video info")


    # ffmpeg encoder related
    def setEncoder(self, h265=True, gpu=True):
        """
        Set encoder parameters according h265 and GPU usage

        Parameters:
            h265 (bool):
                _

            gpu (bool):
                _
        
        Used attributes:
            h265
            gpu
            encoder
        """
        self.h265 = h265
        self.gpu = gpu
        
        if not gpu:
            if not h265:
                self.encoder = ' libx264 -crf 1'
            else:
                self.encoder = ' libx265 -crf 0'
            
            self.encoder += (
                ' -preset medium'
            )

        else:
            if not h265:
                self.encoder = ' h264_nvenc -b_ref_mode middle'
            else:
                self.encoder = ' hevc_nvenc -weighted_pred 1'

            self.encoder += (
                ' -preset p6'
                ' -tune hq'
                ' -rc vbr'
                ' -rc-lookahead 32'
                ' -multipass fullres'
                ' -spatial_aq 1'
                ' -cq 1'
            )

    def _getCommand(self, video:VideoInfo, process:str, substep='') -> str:
        
        videoPath = video['path']
        videoName = video['name']

        videoFps = video['fps']
        if substep == 2 and process == VideoProcess.interpolate.name:
            videoFps = video["interpolateFps"]

        haccel = ''
        if self.gpu:
            haccel = ' -hwaccel cuda -hwaccel_output_format cuda'

        if process != VideoProcess.merge.name:
            communFFmpegOut = (
                f' -c:v copy -c:a copy -c:s copy'
                f' -c:v:0 {self.encoder} {video["optimizeBitRateParam"]}'
                f' -r {videoFps}'
                f' -y'
                f' "{process}\\{videoName}"'
            )

        if process == VideoProcess.optimize.name:
            command = (
                f' ffmpeg'
                f' {haccel}'
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
                f' {haccel}'
                f' -i "{videoPath}"'
                f' -map 0:v -map 0:a? -map 0:s?'
                f' -filter:v:0 {resizeFilter}={video["resizeWidth"]}:{video["resizeHeight"]}'
                f' {communFFmpegOut}'
            )

        elif process in [VideoProcess.upscale.name, VideoProcess.interpolate.name]:

            if substep == 0:
                command = (
                    f' ffmpeg'
                    f' -i "{videoPath}"'
                    f' -qscale:v 1 -qmin 1 -qmax 1 -y'
                    f' -r {videoFps}'
                    f' "{video["getFramesOutputPath"]}/frame%08d.jpg"'
                )
            else:
                if process == VideoProcess.upscale.name:
                    processOutputPath = video["upscaleOutputPath"]
                    upscaleFactor = video["upscaleFactor"]
                elif process == VideoProcess.interpolate.name:
                    processOutputPath = video["interpolateOutputPath"]

                if substep == 1 and process == VideoProcess.upscale.name:
                    command = (
                        f' realesrgan-ncnn-vulkan.exe'
                        f' -i "{video["getFramesOutputPath"]}"'
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
                        f' -f jpg -g 1'
                    )
                elif substep == 1 and process == VideoProcess.interpolate.name:
                    command = (
                        f' ifrnet-ncnn-vulkan.exe'+
                        f' -i "{video["getFramesOutputPath"]}"'+
                        f' -o "{processOutputPath}"'+
                        ' -m IFRNet_GoPro -g 1 -f frame%08d.jpg'+
                        f' -n {video["interpolateFrame"]}'
                    )

                elif substep == 2:
                    command = (
                        f' ffmpeg'
                        f' {haccel}'
                        f' -i "{videoPath}"'
                        f' {haccel}'
                        f' -c:v mjpeg_cuvid -r {videoFps}'
                        f' -i "{processOutputPath}/frame%08d.jpg"'
                        f' -map 1:v:0 -map 0:a? -map 0:s?'
                        f' {communFFmpegOut}'
                    )

        elif process == VideoProcess.merge.name:
            command = (
                f' ffmpeg'
                f' {video["commandInputs"]}'
                f' {video["commandMap"]}'
                f' -c copy'
                f' {video["commandMetadata"]}'
                f' -y'
                f' "{process}\\{videoName}"'
            )
        
        else:
            printC(f'Unknown video process "{process}"', "red")
            return None
        
        return command


    # run process related
    def killProc(self) -> None:
        """
        Kill and stop running process of _runProc() and _runProcAsync(),
        Set self.killed to True if correctly killed.
        
        Used attributes:
            killed
            proc
            procAsync
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
        
        Used attributes:
            path
            EXIT_CODE_FILE_NAME
            killed
            proc
        """

        processTime = time()

        printC(f'Running process : {processName}', "green")

        commandWarped = (
            f' start "VideoScripy-{processName}" /I /min /wait /realtime'
            f' cmd /v:on /c " {self.path[0]}:'
            f' & cd {self.path}'
            f' & {command}'
            f' & echo ^!errorLevel^! > {self.EXIT_CODE_FILE_NAME}"'
        )

        self.killed = False
        self.proc = subprocess.Popen(
            commandWarped,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        self.proc.communicate()
        self.proc = None

        if not silence:
            processTime = time() - processTime
            processTime = timedelta(seconds=processTime)
            print(f"Took :{str(processTime)[:-3]}")

        return self._checkExitCode(silence)

    def _checkExitCode(self, silence=False) -> bool:
        filePath = self.path+f'\\{self.EXIT_CODE_FILE_NAME}'

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
                return False

    def _runProcAsync(self, command:str) -> None:
        """
        Run shell script in a hidden "cmd.exe".\n
        Warning ! Output path must be absolute.\n
        Must call _runProcAsyncWait() to get its return code and content.
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
        Return list of process's (return code, stdout)
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
        Track video frame process with progress bar,
        Set global variable stop_threads to True to stop.

        Parameters:
            outDir (str):
                process output directory, where progress increase
            
            total (int):
                when to stop
        """
        self.stop_threads = False
        
        alreadyProgressed = len(listdir(outDir))
        restToProgress = total - alreadyProgressed
        print(f"Already progressed : {alreadyProgressed}/{total}")
        print(f"Remain to progress : {restToProgress}/{total}")

        progressedPrev = 0
        with alive_bar(total) as bar:
            if alreadyProgressed != 0:
                bar(alreadyProgressed, skipped=True)
            while len(listdir(outDir)) < total:
                sleep(0)
                progressed = len(listdir(outDir)) - alreadyProgressed
                bar(progressed - progressedPrev)
                progressedPrev = progressed

                if self.stop_threads:
                    break
            
            progressed = len(listdir(outDir)) - alreadyProgressed
            bar(progressed - progressedPrev)
            progressedPrev = progressed

    def _frameWatchStart(self, outDir:str, total:int) -> None:
        self.watch = Thread(
            target=self._frameWatch,
            args=(outDir, total)
        )
        self.watch.start()

    def _frameWatchStop(self) -> None:
        self.stop_threads = True
        while self.watch.is_alive():
            pass


    # video process related
    def _getFrames(self, video:VideoInfo, process:VideoProcess) -> bool:
        """
        Transform video to frames

        Parameters:
            video (dict):
                info of one video. path, name, fps are used
        
        Used attributes:
            path
            proc
        """
        getFramesOutputPath = video["getFramesOutputPath"]
        # check if get frame is necessary
        if isdir(getFramesOutputPath):

            # get number of frames, 3rd round
            if isdir(f'{getFramesOutputPath}\\processed'):
                obtainedFrames = (
                    len(listdir(getFramesOutputPath)) - 1
                    + len(listdir(f'{getFramesOutputPath}\\processed'))
                )
            # get number of frames, less than 3rd round
            else:
                obtainedFrames = len(listdir(getFramesOutputPath))

            # equal to what it should has, allow +- 1 frame difference
            if abs(obtainedFrames - video["nbFrames"]) <= 1:
                printC("No need to get frames", "yellow")
                return True
            else:
                printC("Missing frames, regenerate frames needed", "yellow")
                rmtree(getFramesOutputPath)

        # create new temporary frames folder
        mkdir(getFramesOutputPath)

        command = self._getCommand(video, process.name, substep=0)
        result = self._runProc(command, process.value[0])

        # check frames count
        obtainedFrames = len(listdir(getFramesOutputPath))
        if obtainedFrames != video["nbFrames"]:
            printC(
                f'Warning, obtained frames {obtainedFrames}'
                f'is not equal to video frames {video["nbFrames"]}',
                "yellow"
            )
            # modify frame number if +- 1 frame difference
            if abs(video["nbFrames"] - obtainedFrames) <= 1:
                video["nbFrames"] = obtainedFrames
        
        return result

    def pre_optimize(self, video:VideoInfo, width:int, height:int, quality:float) -> None:

        # compute optimization bit rate
        optimizeBitRate = width * height * quality

        print(f'{video["bitRate"]/1_000:_.0f} Kbits/s --> {optimizeBitRate/1_000:_.0f} Kbits/s')

        video['optimizeBitRate'] = optimizeBitRate
        video['optimizeBitRateParam'] = (
            f' -maxrate:v {optimizeBitRate}'
            f' -bufsize:v {optimizeBitRate*2} '
        )


    def optimize(self, quality:float=3.0) -> None:
        """
        Reduce video bit rate

        Parameters:
            quality (float):
                video bit rate = width x height x quality
        
        Used attributes:
            path
            vList
            OPTIMIZE_TOLERENCE
            highQualityParam
            killed
            proc
        """
        
        process = VideoProcess.optimize.name
        # create output folder
        outputFolder = self.path+f'\\{process}'
        if not isdir(outputFolder):
            mkdir(outputFolder)
        
        for index, video in enumerate(self.vList):
            noticeProcessBegin()

            name = video['name']
            width = video['width']
            height = video['height']
            bitRate = video['bitRate']

            # show current optimizing video
            print(f'{index+1}/{len(self.vList)}'.center(20, '-'))
            print(name)
            print('{}x{}'.format(width, height))

            self.pre_optimize(video, width, height, quality)

            # check if optimization needed
            if video["optimizeBitRate"] * self.OPTIMIZE_TOLERENCE > bitRate:
                printC('Skipped', "yellow")
                continue

            command = self._getCommand(video, process)
            self._runProc(command, process)

            # stop whole process if killProc() called
            if self.killed:
                break
        
        removeEmptyFolder(outputFolder)
        noticeProcessEnd()
    
    def resize(self, setWidth:int, setHeight:int, quality:float=3.0) -> None:
        """
        Resize video

        Parameters:
            setWidth (int):
                -1 to let it by default

            setHeight (int):
                -1 to let it by default

            quality (float):
                video bit rate = width x height x quality
        
        Used attributes:
            path
            vList
            highQualityParam
        """
        
        process = VideoProcess.resize.name
        # create output folder
        outputFolder = self.path+f'\\{process}'
        if not isdir(outputFolder):
            mkdir(outputFolder)
        
        for index, video in enumerate(self.vList):
            noticeProcessBegin()
            
            name = video['name']
            width = video['width']
            height = video['height']

            # show current resizing video
            print(f'{index+1}/{len(self.vList)}'.center(20, '-'))
            print(name)

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
                continue
            
            video["resizeWidth"] = widthResize
            video["resizeHeight"] = heightResize

            self.pre_optimize(video, widthResize, heightResize, quality)

            command = self._getCommand(video, process)
            self._runProc(command, process)

            # stop whole process if killProc() called
            if self.killed:
                break
        
        removeEmptyFolder(outputFolder)
        noticeProcessEnd()

    def upscale(self, upscaleFactor:int=2, quality:float=3) -> None:
        """
        Upscale video

        Parameters:
            upscaleFactor (int):
                2, 3 or 4
            
            quality (float):
                video bit rate = width x height x quality
        
        Used attributes:
            path
            vList
            highQualityParam
        
        Used functions/methodes:
            _getFrames()
            frameWatch()
        
        """

        process = VideoProcess.upscale
        # create output folder
        outputFolder = self.path+f'\\{process.name}'
        if not isdir(outputFolder):
            mkdir(outputFolder)

        for index, video in enumerate(self.vList):
            noticeProcessBegin()
            
            name = video['name']
            width = video['width']
            height = video['height']

            # show current upscaling video
            print(f'{index+1}/{len(self.vList)}'.center(20, '-'))
            print(name)

            # save and show size change
            widthUpscale = width * upscaleFactor
            heightUpscale = height * upscaleFactor
            print(f'{width}x{height} --> {widthUpscale}x{heightUpscale}')

            self.pre_optimize(video, widthUpscale, heightUpscale, quality)

            getFramesOutputPath = self.path+f'\\{name}_tmp_frames'
            video["getFramesOutputPath"] = getFramesOutputPath

            result = self._getFrames(video, process)
            
            # stop whole process if killProc() called
            if self.killed:
                break
            
            # skip next steps if process not correctly ended
            if not result:
                continue

            upscaleOutputPath = self.path+f'\\{name}_{process.name}x{upscaleFactor}_frames'
            # new upscaling
            if not isdir(upscaleOutputPath):
                print(f'New upscaling')
                mkdir(upscaleOutputPath)
            # continue upscaling
            else:
                print(f'Continue upscaling')
                for _, _, files in walk(upscaleOutputPath):

                    # create processed folder
                    processedFolder = f'{getFramesOutputPath}\\processed'
                    if not isdir(processedFolder):
                        mkdir(processedFolder)

                    # move frame to processed folder except last two
                    for framesUpscaled in files[:-2]:
                        try:
                            rename(
                                f'{getFramesOutputPath}\\{framesUpscaled}',
                                f'{processedFolder}\\{framesUpscaled}',
                            )
                        # do nothing to already moved
                        except FileNotFoundError:
                            pass

                    # remove last two upscaled frames
                    for lastTwoUpscaled in files[-2:]:
                        remove(upscaleOutputPath+'\\'+lastTwoUpscaled)

                    break

            # frames watch
            self._frameWatchStart(upscaleOutputPath, video["nbFrames"])

            video["upscaleOutputPath"] = upscaleOutputPath
            video["upscaleFactor"] = upscaleFactor
            command = self._getCommand(video, process.name, substep=1)
            result = self._runProc(command, process.value[1])
            
            # frames watch end
            self._frameWatchStop()

            # stop whole process if killProc() called
            if self.killed:
                break
            
            # skip next steps if process not correctly ended
            if not result:
                continue

            # remove frames
            rmtree(getFramesOutputPath)
            
            # upscaled frames to video
            command = self._getCommand(video, process.name, substep=2)
            result = self._runProc(command, process.value[2])

            # stop whole process if killProc() called
            if self.killed:
                break
            
            # skip next steps if process not correctly ended
            if not result:
                continue
            
            # remove upscaled frames
            rmtree(upscaleOutputPath)

        removeEmptyFolder(outputFolder)
        noticeProcessEnd()

    def interpolate(self, fpsInterp:float=30.0, quality:float=3) -> None:
        """
        Interpolate video to increase fps

        Parameters:
            fps (float):
                must > than original fps

            quality (float):
                video bit rate = width x height x quality
        
        Used attributes:
            path
            vList
            highQualityParam
        
        Used functions/methodes:
            _getFrames()
            frameWatch()
        
        """
        
        process = VideoProcess.interpolate
        # create output folder
        outputFolder = self.path+f'\\{process.name}'
        if not isdir(outputFolder):
            mkdir(outputFolder)

        for index, video in enumerate(self.vList):
            noticeProcessBegin()

            name = video['name']
            width = video['width']
            height = video['height']
            fps = video['fps']
            duration = video['duration']

            # show current resizing video
            print(f'{index+1}/{len(self.vList)}'.center(20, '-'))
            print(name)

            # check if interpolation needed
            if fpsInterp < fps:
                print(fpsInterp, '<', fps)
                printC("Skipped", "yellow")
                continue

            # save and show interpolate change
            interpolateFrame = ceil(duration.total_seconds() * fpsInterp)
            video["interpolateFrame"] = interpolateFrame

            print(f'{fps}fps --> {fpsInterp}fps')

            self.pre_optimize(video, width, height, quality)
            
            getFramesOutputPath = self.path+'\\{}_tmp_frames'.format(name)
            video["getFramesOutputPath"] = getFramesOutputPath
            video['interpolateFps'] = fpsInterp
            result = self._getFrames(video, process)

            # stop whole process if killProc() called
            if self.killed:
                break
            
            # skip next steps if process not correctly ended
            if not result:
                continue

            interpolateOutputPath = self.path+f'\\{name}_{process.name}_frames'
            video["interpolateOutputPath"] = interpolateOutputPath

            # empty interpolate frames folder
            if isdir(interpolateOutputPath):
                rmtree(interpolateOutputPath)

            # new frames interpolate
            mkdir(interpolateOutputPath)

            # frames watch
            self._frameWatchStart(interpolateOutputPath,interpolateFrame)
            
            command = self._getCommand(video, process.name, substep=1)
            result = self._runProc(command, process.value[1])
            
            # frame watch end
            self._frameWatchStop()

            # stop whole process if killProc() called
            if self.killed:
                break
            
            # skip next steps if process not correctly ended
            if not result:
                continue

            # remove frames
            rmtree(getFramesOutputPath)

            # interpolate frames to video
            command = self._getCommand(video, process.name, substep=2)
            result = self._runProc(command, process.value[2])

            # stop whole process if killProc() called
            if self.killed:
                break
            
            # skip next steps if process not correctly ended
            if not result:
                continue

            # remove interpolated frames
            rmtree(interpolateOutputPath)

        removeEmptyFolder(outputFolder)
        noticeProcessEnd()

    def merge(self, allVideo:bool=True, allAudio:bool=False, allSubtitle:bool=False) -> None:
        """
        Merge video0.mp4 video1.mp4 ... to video.mkv

        Parameters:
            allVideo (bool):
                set to False to keep only the first video, default=True
            
            allAudio (bool):
                set to True to keep all audio, default=False
                
            allSubtitle (bool):
                set to True to keep all subtitle, default=False
        
        Used attributes:
            path
            vList
        """
        
        noticeProcessBegin()
        
        process = VideoProcess.merge.name
        # create output folder
        outputFolder = self.path+f'\\{process}'
        if not isdir(outputFolder):
            mkdir(outputFolder)

        print(f'{len(self.vList)}'.center(20, '-'))

        # check number of video
        if len(self.vList) <= 1:
            printC("0 or 1 video is not enought to merge", "yellow")
        else:
            # check video length
            duration = self.vList[0]['duration']
            for video in self.vList:
                if duration != video['duration']:
                    printC(f'Warning, "{video["name"]}" has different duration', "yellow")
            
            commandInputs = ""
            commandMap = ""
            commandMetadata = ""
            for index, video in enumerate(self.vList):

                path = video['path']
                name = video['name']
                print(name)

                if index == 0:
                    commandInputs += f'-i "{path}" '
                    commandMap += f'-map {index} '
                    # remove time codec for mp4
                    commandMap += f'-map -{index}:d '
                    commandMetadata += f'-metadata:s:v:{index} title="{name}" '
                    commandMetadata += f'-metadata:s:a:{index} title="{name}" '
                    commandMetadata += f'-metadata:s:s:{index} title="{name}" '
                else:
                    commandInputs += f'-i "{path}" '
                    # remove time codec for mp4
                    commandMap += f'-map -{index}:d '
                    if allVideo:
                        commandMap += f'-map {index}:v? '
                        commandMetadata += f'-metadata:s:v:{index} title="{name}" '
                    if allAudio:
                        commandMap += f'-map {index}:a? '
                        commandMetadata += f'-metadata:s:a:{index} title="{name}" '
                    if allSubtitle:
                        commandMap += f'-map {index}:s? '
                        commandMetadata += f'-metadata:s:s:{index} title="{name}" '

            video["commandInputs"] = commandInputs
            video["commandMap"] = commandMap
            video["commandMetadata"] = commandMetadata
            command = self._getCommand(video, process)
            self._runProc(command, process)
            
        removeEmptyFolder(outputFolder)
        noticeProcessEnd()

    def preview(self, gridWidth:int=3, gridHeight:int=2) -> None:

        process = VideoProcess.preview.name
        # create output folder
        outputFolder = self.path+f'\\{process}'
        if not isdir(outputFolder):
            mkdir(outputFolder)

        gridNb = gridWidth*gridHeight
        
        for index, video in enumerate(self.vList):
            noticeProcessBegin()

            name = video['name']
            duration = video['duration'].total_seconds()
            width = video['width']
            height = video['height']

            outputName = video['name'].replace(f".{video['type']}",".png")

            # show current previewing video
            print(f'{index+1}/{len(self.vList)}'.center(20, '-'))
            print(name)
            
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

                command = (
                    f' ffmpeg'
                    f' -ss {imgTime}'
                    f' -i "{video["path"]}"'
                    f' -frames:v 1'
                    f' -y'
                    f' "{self.path}\\{process}\\{imgNb}.png"'
                )
                self._runProcAsync(command)
            self._runProcAsyncWait()
            
            # stop whole process if killProc() called
            if self.killed:
                break

            newImageWidth = width*gridWidth
            newImageHeight = height*gridHeight
            newImage = Image.new('RGB', (newImageWidth,newImageHeight))

            imgNb = 0
            for ghCount in range(gridHeight):
                for gwCount in range(gridWidth):
                    imTempPath = f"{self.path}\\{process}\\{imgNb}.png"
                    imgNb += 1
                    imTemp = Image.open(imTempPath)
                    newImage.paste(imTemp, (gwCount*width, ghCount*height))

            newImage.save(f"{self.path}\\{process}\\{outputName}")

            for imgNb in range(gridNb):
                imTempPath = f"{self.path}\\{process}\\{imgNb}.png"
                imgNb += 1
                remove(imTempPath)

            processTime = time() - processTime
            processTime = timedelta(seconds=processTime)
            print(f"Took :{str(processTime)[:-3]}")

        noticeProcessEnd()
        removeEmptyFolder(outputFolder)




def run():
    def getInputInt(
            message:str="",
            default:int=None,
            selections:list=[],
            absolute=True,
        ) -> int:

        while True:
            # get input
            entered = input(f"{message} [{default}]:")

            # check if default
            if default != None and entered == "":
                print(default)
                return default

            try:
                entered = int(entered)
                if absolute:
                    entered = abs(entered)
            except:
                print(f'{entered} is not an integer')

            # no selection constrain
            if selections == []:
                print(entered)
                return entered
            
            # check if in selections
            elif entered in selections:
                print(entered)
                return entered
            else:
                print(f'{entered} is not in {selections}')

    def getInputFloat(
            message:str="",
            default:float=None,
            absolute=True,
        ) -> float:

        while True:
            # get input
            entered = input(f"{message} [{default}]:")

            # check if default
            if default != None and entered == "":
                print(default)
                return default

            try:
                entered = int(entered)
                if absolute:
                    entered = abs(entered)
                print(entered)
                return entered
            except:
                print(f'{entered} is not a float')

    def getInputBool(
            message:str="",
            default:bool=None,
        ) -> bool:

        while True:
            # get input
            entered = input(f"{message} [{default}]:")

            # check if default
            if default != None and entered == "":
                print(default)
                return default

            try:
                if entered.lower() in ["1", "y", "yes", "o", "oui"]:
                    print(True)
                    return True
                else:
                    print(False)
                    return False
            except:
                print(f'{entered} is not a boolean')
    
    vs = VideoScripy()

    vs.getVideo(folderDepthLimit=0)
    vs.getVideoInfo()

    for index, process in enumerate(VideoProcess):
        print(f'{index+1} - {process.name}')
    process = getInputInt(
        message='Select a process',
        default=1,
        selections=[i+1 for i in range(len(VideoProcess))]
    )

    if process == 1:
        quality = getInputFloat("Quality",3.0)
        vs.optimize(quality)

    elif process == 2:
        width = getInputInt("Width",1920)
        height = getInputInt("Height",-1)
        quality = getInputFloat("Quality",3.0)
        vs.resize(width, height, quality)

    elif process == 3:
        upFactor = getInputInt('Upscale factor',2,[2,3,4])
        quality = getInputFloat("Quality",3.0)
        vs.upscale(upFactor, quality)

    elif process == 4:
        fps = getInputFloat("FPS",60.0)
        quality = getInputFloat("Quality",3.0)
        vs.interpolate(fps, quality)

    elif process == 5:
        allVideo = getInputBool("All video",True)
        allAudio = getInputBool("All audio",False)
        allSubtitle = getInputBool("All subtitle",False)
        vs.merge(allVideo, allAudio, allSubtitle)

    elif process == 6:
        gridWidth = getInputInt("Width",3)
        gridHeight = getInputInt("Height",2)
        vs.preview(gridWidth, gridHeight)
    
    input("Press enter to exit")



if __name__ == '__main__':
    run()




