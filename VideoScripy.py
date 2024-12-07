# dependencies
from ffmpeg import probe
from alive_progress import alive_bar
from colorama import init, Fore, Style

init()

# built-in
import subprocess
import psutil
from threading import Thread
from pathlib import Path
from datetime import timedelta
from shutil import rmtree
from os import walk, mkdir, remove, listdir, getcwd, rmdir
from os.path import isdir, isfile
from time import time, sleep
from winsound import Beep
from math import ceil
from typing import TypedDict
from enum import Enum
from math import ceil


# from VideoScripy import *
__all__ = ['VideoScripy', 'run']



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

class VideoProcess(Enum):
    optimize = "optimize"
    resize = "resize"
    getFrames = "getFrames"
    upscale = "upscale"
    interpolate = "interpolate"
    merge = "merge"

def printC(text, color:str=None):
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

def noticeProcessEnd():
    pass
    Beep(440, 1500)
    # input('Press enter to exit')

def frameWatch(outDir:str, total:int):
    """
    Track video frame process with progress bar,
    Set global variable stop_threads to True to stop.

    Parameters:
        outDir (str):
            process output directory, where progress increase
        
        total (int):
            when to stop
    """
    
    global stop_threads
    stop_threads = False
    
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

            if stop_threads:
                break
        else:
            progressed = len(listdir(outDir)) - alreadyProgressed
            bar(progressed - progressedPrev)
            progressedPrev = progressed



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

        optimizationTolerence (float):
            do not optimize if optimizedBitRate * optimizationTolerence < bitRate

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
        self.folderSkip = [p.value for p in VideoProcess]
        self.optimizationTolerence = 1.15
        
        self.h265 = True
        self.gpu = True
        self.setEncoder(h265=True, gpu=True)

        self.proc = None
        self.killed = False

        self.exitCodeFileName = "exitCode.txt"

        self.checkTools()
    

    
    def checkTools(self):
        tools = {
            "FFmpeg": "ffmpeg -h",
            "Real-ESRGAN": "realesrgan-ncnn-vulkan.exe -h",
            "IFRNet": "ifrnet-ncnn-vulkan.exe -h",
        }
        prefix = 'start "checkTools" /min /wait cmd /v:on /c " '
        sufix = f' & echo ^!errorLevel^! > {self.exitCodeFileName}"'
        for tool, cmd in tools.items():
            proc = subprocess.Popen(
                prefix+cmd+sufix,
                cwd=self.path,
                shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            proc.communicate()
            result = self._checkExitCode(silence=True)
            if result:
                printC(f'{tool} found', 'green')
            else:
                printC(f'{tool} not found, please check if it is correctly installed', 'red')


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
                printC("Path do not exist", "red")
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
                fileFormat = file.split(".")[-1].lower()
                if fileFormat in self.vType:
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
        Set attributes vList's video properties with ffmpeg probe
        
        Used attributes:
            vList
        """

        # get info
        for videoIndex in range(len(self.vList)-1,-1,-1):
            try:
                # get video probe
                videoProbe = probe(self.vList[videoIndex]["path"])
                # get first video stream info
                # TODO add multiple video stream waring
                videoStreamTemp = [
                    streams for streams in videoProbe['streams']
                    if streams['codec_type'] == 'video'
                ][0]
                # write info
                self.vList[videoIndex]['duration'] = timedelta(seconds=float(videoStreamTemp['duration']))
                self.vList[videoIndex]['bitRate'] = int(videoStreamTemp['bit_rate'])
                self.vList[videoIndex]['width'] = int(videoStreamTemp['width'])
                self.vList[videoIndex]['height'] = int(videoStreamTemp['height'])
                num, denom = videoStreamTemp['r_frame_rate'].split('/')
                self.vList[videoIndex]['fps'] = round(float(num)/float(denom),2)
                self.vList[videoIndex]['nbFrames'] = int(videoStreamTemp['nb_frames'])
            except Exception as e:
                printC(e, "red")
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

    def _getFFmpegCommand(
            self, video:VideoInfo, process:str,
            commandInputs:str=None, commandMap:str=None, commandMetadata:str=None,
        ) -> str:
        
        command = (
            f'start "VideoScripy-{process}" /I /min /wait /realtime'
            f' cmd /v:on /c " {self.path[0]}:'
            f' & cd {self.path}'
            ' & ffmpeg'
        )

        path = video['path']
        name = video['name']
        fps = video['fps']

        if self.gpu:
            haccel = ' -hwaccel cuda -hwaccel_output_format cuda'
        else:
            haccel = ''

        if process == VideoProcess.optimize.value:
            command += (
                f' {haccel}'
                f' -i "{path}"'
                ' -map 0:v -map 0:a? -map 0:s?'
            )

        elif process == VideoProcess.resize.value:
            if self.gpu:
                resizeFilter = "scale_cuda"
            else:
                resizeFilter = "scale"
            command += (
                f' {haccel}'
                f' -i "{path}"'
                ' -map 0:v -map 0:a? -map 0:s?'
                f' -vf {resizeFilter}={video["resizeWidth"]}:{video["resizeHeight"]}'
            )
            
        elif process == VideoProcess.getFrames.value:
            command += (
                f' -i "{path}"'
                ' -qscale:v 1 -qmin 1 -qmax 1 -y'
                f' -r {fps}'
                f' "{video["getFramesOutputPath"]}/frame%08d.jpg"'
                f' & echo ^!errorLevel^! > {self.exitCodeFileName}"'
            )
            return command

        elif process in [VideoProcess.upscale.value, VideoProcess.interpolate.value]:

            if process == VideoProcess.upscale.value:
                processOutputPath = video["upscaleOutputPath"]

            elif process == VideoProcess.interpolate.value:
                processOutputPath = video["interpolateOutputPath"]
                fps = video["interpolateFps"]

            command += (
                f' {haccel}'
                f' -i "{path}"'
                f' {haccel}'
                f' -c:v mjpeg_cuvid -r {fps}'
                f' -i "{processOutputPath}/frame%08d.jpg"'
                ' -map 1:v:0 -map 0:a? -map 0:s?'
            )

        elif process == VideoProcess.merge.value:
            command += (
                f' {commandInputs}'
                f' {commandMap}'
                ' -c copy'
                f' {commandMetadata}'
                f' -y'
                f' "{process}\\{name}"'
                f' & echo ^!errorLevel^! > {self.exitCodeFileName}"'
            )
            return command
        
        else:
            printC(f'Unknown video process "{process}"', "red")
            return None
        
        command += (
            f' -c:v copy -c:a copy -c:s copy'
            f' -c:v:0 {self.encoder} {video["optimizeBitRateParam"]}'
            f' -r {fps}'
            f' -y'
            f' "{process}\\{name}" '
            f' & echo ^!errorLevel^! > {self.exitCodeFileName}"'
        )
        return command


    # video process related
    def killProc(self) -> None:
        """
        Kill and stop running video process,
        Only set killed to True if no running video process.
        
        Used attributes:
            killed
            proc
        """
        if self.proc != None:
            parent = psutil.Process(self.proc.pid)
            for child in parent.children(recursive=True):
                child.kill()
            self.killed = True

    def _runProc(self, command:str) -> bool:
        """
        Run shell script and wait till its end

        Parameters:
            command (str):
                command line script
        
        Used attributes:
            killed
            proc
        """
        processTime = time()

        self.killed = False
        self.proc = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        self.proc.communicate()
        self.proc = None

        processTime = time() - processTime
        processTime = timedelta(seconds=processTime)
        print(f"Took :{str(processTime)[:-3]}")

        return self._checkExitCode()

    def _checkExitCode(self, silence=False) -> bool:
        filePath = self.path+f'\\{self.exitCodeFileName}'

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

            

    def _getFrames(self, video:VideoInfo) -> bool:
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
            # equal to what it should has
            if len(listdir(getFramesOutputPath)) == video["nbFrames"]:
                printC("No need to get frames", "yellow")
                self.killed = False
                return True
            # less than what it should has
            elif len(listdir(getFramesOutputPath)) < video["nbFrames"]:
                printC("Missing frames, regenerate frames needed", "yellow")
                rmtree(getFramesOutputPath)
            # more than what it should has
            elif len(listdir(getFramesOutputPath)) > video["nbFrames"]:
                printC("To much frames, regenerate frames needed", "yellow")
                rmtree(getFramesOutputPath)
            else:
                printC("_getFrames() : ???", "red")

        # create new temporary frames folder
        mkdir(getFramesOutputPath)

        command = self._getFFmpegCommand(video, VideoProcess.getFrames.value)
        
        printC(f'Getting Frames', "green")
        result = self._runProc(command)

        # check _getFrames accuracy
        getedFrames = len(listdir(getFramesOutputPath))
        if getedFrames != video["nbFrames"]:
            printC(f'Waring, geted frames {getedFrames} != video frames {video["nbFrames"]}', "yellow")
        
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
            optimizationTolerence
            highQualityParam
            killed
            proc
        """
        
        process = VideoProcess.optimize.value
        # create output folder
        outputFolder = self.path+f'\\{process}'
        if not isdir(outputFolder):
            mkdir(outputFolder)
        
        for index, video in enumerate(self.vList):

            name = video['name']
            width = video['width']
            height = video['height']
            bitRate = video['bitRate']

            # show current optimizing video
            print('--- {}/{} ---'.format(index+1,len(self.vList)))
            print(name)
            print('{}x{}'.format(width, height))

            self.pre_optimize(video, width, height, quality)

            # check if optimization needed
            if video["optimizeBitRate"] * self.optimizationTolerence > bitRate:
                printC('Skipped', "yellow")
                continue

            command = self._getFFmpegCommand(video, process)
            
            printC(f'Optimizing "{name}"', "green")
            self._runProc(command)

            if self.killed:
                return
        
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
        
        process = VideoProcess.resize.value
        # create output folder
        outputFolder = self.path+f'\\{process}'
        if not isdir(outputFolder):
            mkdir(outputFolder)
        
        for index, video in enumerate(self.vList):
            
            name = video['name']
            width = video['width']
            height = video['height']

            # show current resizing video
            print('--- {}/{} ---'.format(index+1,len(self.vList)))
            print(name)

            # TODO directly use -1
            # compute setWidth and setHeight
            if setWidth == -1 and setHeight == -1:
                newWidth = width
                newHeight = height
            elif setWidth == -1:
                newWidth = ceil(width * setHeight/height)
                newHeight = setHeight
            elif setHeight == -1:
                newWidth = setWidth
                newHeight = ceil(height * setWidth/width)
            else:
                newWidth = setWidth
                newHeight = setHeight
            
            # to positive size
            newWidth = abs(newWidth)
            newHeight = abs(newHeight)

            # even newWidth and newHeight
            if newWidth%2 != 0:
                newWidth += 1
            if newHeight%2 != 0:
                newHeight += 1

            # ratio warning
            if newWidth/newHeight != width/height:
                printC('Warning, rize ratio will be changed', "yellow")
            
            print(f'{width}x{height} --> {newWidth}x{newHeight}')
            
            # check if resize needed
            if newWidth == width and newHeight == height:
                printC("Skipped", "yellow")
                continue
            
            video["resizeWidth"] = newWidth
            video["resizeHeight"] = newHeight

            self.pre_optimize(video, newWidth, newHeight, quality)

            command = self._getFFmpegCommand(video, process)

            printC(f'Resizing "{name}"', "green")
            self._runProc(command)

            if self.killed:
                return
        
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

        process = VideoProcess.upscale.value
        # create output folder
        outputFolder = self.path+f'\\{process}'
        if not isdir(outputFolder):
            mkdir(outputFolder)

        for index, video in enumerate(self.vList):
            
            name = video['name']
            width = video['width']
            height = video['height']

            # show current upscaling video
            print('--- {}/{} ---'.format(index+1,len(self.vList)))
            print(name)

            # save and show size change
            newWidth = width * upscaleFactor
            newHeight = height * upscaleFactor
            print(f'{width}x{height} --> {newWidth}x{newHeight}')

            self.pre_optimize(video, newWidth, newHeight, quality)

            getFramesOutputPath = self.path+'\\{}_tmp_frames'.format(name)
            video["getFramesOutputPath"] = getFramesOutputPath

            result = self._getFrames(video)
            
            if self.killed:
                return
            if not result:
                continue

            upscaleOutputPath = self.path+f'\\{name}_{process}x{upscaleFactor}_frames'
            # create upscaled frames folder if not existing
            if not isdir(upscaleOutputPath):
                mkdir(upscaleOutputPath)
                printC(f'Upscaling "{name}"', "green")
            # continue existing frames upscale
            else:
                for _, _, files in walk(upscaleOutputPath):
                    # remove upscaled frame's origin frames except last two
                    for framesUpscaled in files[:-2]:
                        remove(getFramesOutputPath+'\\'+framesUpscaled)
                    # remove last two upscaled frames
                    for lastTwoUpscaled in files[-2:]:
                        remove(upscaleOutputPath+'\\'+lastTwoUpscaled)
                printC(f'Continue upscaling "{name}"', "green")
            
            # frames watch
            watch = Thread(
                target=frameWatch,
                args=(upscaleOutputPath, video["nbFrames"])
            )
            watch.start()

            command = (
                f'start "VideoScripy-{process}" /min /wait /realtime'+
                f' cmd /v:on /c " {self.path[0]}:'+
                f' & cd {self.path}'+
                ' & realesrgan-ncnn-vulkan.exe'+
                f' -i "{getFramesOutputPath}"'+
                f' -o "{upscaleOutputPath}"'
            )
            if upscaleFactor in [2,3,4]:
                command += f' -n realesr-animevideov3 -s {upscaleFactor}'
            # TODO
            elif upscaleFactor == "4p":
                command += ' -n realesrgan-x4plus'
            elif upscaleFactor == "4pa":
                command += ' -n realesrgan-x4plus-anime'
            else:
                printC(f'Unknown upscale factor "{upscaleFactor}"', "red")
                return
            command += (
                ' -f jpg -g 1'
                f' & echo ^!errorLevel^! > {self.exitCodeFileName}"'
            )


            result = self._runProc(command)
            if not result:
                global stop_threads
                stop_threads = True
                while watch.is_alive():
                    pass
            else:
                watch.join()

            if self.killed:
                return
            if not result:
                continue

            # remove frames
            rmtree(getFramesOutputPath)

            
            video["upscaleOutputPath"] = upscaleOutputPath
            # upscaled frames to video
            command = self._getFFmpegCommand(video, process)
            printC(f'Upscaling frame to video "{name}"', "green")

            result = self._runProc(command)

            if self.killed:
                return
            if not result:
                continue
            
            # remove upscaled frames
            rmtree(upscaleOutputPath)

        removeEmptyFolder(outputFolder)
        noticeProcessEnd()

    def interpolate(self, fps:float=30.0, quality:float=3) -> None:
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
        
        process = VideoProcess.interpolate.value
        # create output folder
        outputFolder = self.path+f'\\{process}'
        if not isdir(outputFolder):
            mkdir(outputFolder)

        for index, video in enumerate(self.vList):

            name = video['name']
            width = video['width']
            height = video['height']
            frameRate = video['fps']
            duration = video['duration']

            # show current resizing video
            print('--- {}/{} ---'.format(index+1,len(self.vList)))
            print(name)

            # check if interpolation needed
            if fps < frameRate:
                print(fps, '<', frameRate)
                printC("Skipped", "yellow")
                continue

            # save and show interpolate change
            interpolateFrame = ceil(duration.total_seconds() * fps)

            print(f'{frameRate}fps --> {fps}fps')

            self.pre_optimize(video, width, height, quality)
            
            getFramesOutputPath = self.path+'\\{}_tmp_frames'.format(name)
            video["getFramesOutputPath"] = getFramesOutputPath
            result = self._getFrames(video)

            if self.killed:
                return
            if not result:
                continue

            interpolateOutputPath = self.path+f'\\{name}_{process}_frames'

            # empty interpolate frames folder
            if isdir(interpolateOutputPath):
                rmtree(interpolateOutputPath)

            # new frames interpolate
            mkdir(interpolateOutputPath)

            # frames watch
            watch = Thread(
                target=frameWatch,
                args=(interpolateOutputPath,interpolateFrame)
            )
            watch.start()
            
            command = (
                f'start "VideoScripy-{process}" /min /wait /realtime'+
                f' cmd /v:on /c " {self.path[0]}:'+
                f' & cd {self.path}'+
                ' & ifrnet-ncnn-vulkan.exe'+
                f' -i "{getFramesOutputPath}"'+
                f' -o "{interpolateOutputPath}"'+
                ' -m IFRNet_GoPro -g 1 -f frame%08d.jpg'+
                f' -n {interpolateFrame}'
                f' & echo ^!errorLevel^! > {self.exitCodeFileName}"'
            )
            printC(f'Interpolating "{name}"', "green")

            result = self._runProc(command)
            if not result:
                global stop_threads
                stop_threads = True
                while watch.is_alive():
                    pass
            else:
                watch.join()

            if self.killed:
                return
            if not result:
                continue

            # remove frames
            rmtree(getFramesOutputPath)

            video['interpolateFps'] = fps
            video["interpolateOutputPath"] = interpolateOutputPath

            # interpolate frames to video
            command = self._getFFmpegCommand(video, process)

            printC(f'Interpolating frame to video "{name}"', "green")
            result = self._runProc(command)

            if self.killed:
                return
            if not result:
                continue

            # remove upscaled frames
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
        
        process = VideoProcess.merge.value
        # create output folder
        outputFolder = self.path+f'\\{process}'
        if not isdir(outputFolder):
            mkdir(outputFolder)

        # check number of video
        if len(self.vList) <= 1:
            printC("0 or 1 video is not enought to merge", "yellow")
            return

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

        command = self._getFFmpegCommand(
            video, process,
            commandInputs=commandInputs,
            commandMap=commandMap,
            commandMetadata=commandMetadata,
        )
        printC(f'Merging {len(self.vList)} videos', "green")
        self._runProc(command)

        if self.killed:
            return
        
        removeEmptyFolder(outputFolder)
        noticeProcessEnd()


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

    print('1 - optimize')
    print('2 - resize')
    print('3 - upscale')
    print('4 - interpolate')
    print('5 - merge')
    process = getInputInt(
        message='Select a process',
        default=1,
        selections=[1,2,3,4,5]
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
    
    input("Press enter to exit")



if __name__ == '__main__':
    run()




