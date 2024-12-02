# dependencies
from ffmpeg import probe
from alive_progress import alive_bar

# built-in
import subprocess
import psutil
from threading import Thread
from pathlib import Path
from datetime import timedelta
from shutil import rmtree
from os import walk, mkdir, remove, listdir, getcwd
from os.path import isdir
from time import time, sleep
from winsound import Beep
from math import ceil
from typing import TypedDict
from enum import Enum



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

class VideoProcess(Enum):
    optimize = "optimize"
    resize = "resize"
    upscale = "upscale"
    interpolate = "interpolate"
    merge = "merge"




def noticeProcessEnd():
    # pass
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
    print("Already progressed : {}/{}".format(alreadyProgressed, total))
    print("Remain to progress : {}/{}".format(restToProgress, total))

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
                self.encoder = ' libx264'
            else:
                self.encoder = ' libx265'
            
            self.encoder += (
                ' -preset medium'+
                ' -crf 0'
            )

        else:
            if not h265:
                self.encoder = ' h264_nvenc'
            else:
                self.encoder = ' hevc_nvenc'

            self.encoder += (
                ' -preset p4'+
                ' -tune hq'+
                ' -rc vbr'+
                ' -rc-lookahead 32'+
                ' -multipass qres'+
                ' -spatial_aq 1'+
                ' -weighted_pred 1'+
                ' -bufsize:v 800M'+
                ' -maxrate:v 800M'+
                ' -cq 1'
            )



    ##################
    # region Get Video


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
            print(f'Path set to default "{self.path}"')
            return True
        else:
            if isdir(path):
                self.path = path
                print(f'Path correctly set to "{self.path}"')
                return True
            else:
                print("Path do not exist")
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
                    print(f'Self generated folder "{folderSkip}" skiped')
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
                        print(f'"&" must not used in path or file name')
                        print(f'Skipped "{file}"')
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
                videoProbeTemp = probe(self.vList[videoIndex]["path"])
                # get first video stream info
                videoStreamTemp = [streams for streams in videoProbeTemp['streams'] if streams['codec_type'] == 'video'][0]
                # get video format info
                videoFormatTemp = videoProbeTemp['format']
                # write info
                self.vList[videoIndex]['duration'] = timedelta(seconds=round(float(videoFormatTemp['duration']),3))
                self.vList[videoIndex]['bitRate'] = int(videoFormatTemp['bit_rate'])
                self.vList[videoIndex]['width'] = int(videoStreamTemp['width'])
                self.vList[videoIndex]['height'] = int(videoStreamTemp['height'])
                frameRateTemp = videoStreamTemp['r_frame_rate'].split('/')
                self.vList[videoIndex]['fps'] = round(float(frameRateTemp[0])/float(frameRateTemp[1]),2)
            except Exception as e:
                print(e)
                print(f'Can not get video info of "{self.vList[videoIndex]["name"]}"')
                # delete errored video
                self.vList.pop(videoIndex)
        

    # endregion get video
    #####################



    ##################
    # region Processes

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

    def _runProc(self, command:str) -> None:
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
        self.proc.wait()
        self.proc = None

        processTime = time() - processTime
        processTime = timedelta(seconds=processTime)
        print("Took :", str(processTime)[:-3])


    def _getFrames(self, video:VideoInfo) -> None:
        """
        Transform video to frames

        Parameters:
            video (dict):
                info of one video. path, name, fps are used
        
        Used attributes:
            path
            proc
        """
        name = video['name']
        path = video['path']
        frameRate = video['fps']
        duration = video['duration']

        frameOutputPath = self.path+'\\{}_tmp_frames'.format(name)
        # check if get frame is necessary
        if isdir(frameOutputPath):
            # less than what it should has
            if len(listdir(frameOutputPath)) < int(duration.total_seconds() * frameRate):
                print("Missing frames, regenerate frames needed")
                rmtree(frameOutputPath)
            else:
                print("No need to get frames")
                return

        # create new temporary frames folder
        mkdir(frameOutputPath)
        command = (
            'start "VideoScripy-getFrames" /min /wait cmd /c " {}:'.format(self.path[0])
            +' & cd {}'.format(self.path)
            +' & ffmpeg'
            +' -i "{}"'.format(path)
            +' -qscale:v 1 -qmin 1 -qmax 1 -y'
            +' -r {}'.format(frameRate)
            +' "{}_tmp_frames/frame%08d.jpg" "'.format(name)
        )
        print(f'Getting Frames of "{name}"')
        self._runProc(command)
        print("Done")

    def _getCommand(
            self, video:VideoInfo, process:str,
            bitRateParam:str=None,
            rWidth:int=None, rHeight:int=None,
            upscaleFactor:int=None,
            interpolateFrame:int=None, fps:float=None,
            frameToVideo:bool=False,
            commandInputs:str=None, commandMap:str=None, commandMetadata:str=None,
        ) -> str:
        if not frameToVideo:
            title = process
        else:
            title = f'{process}-frameToVideo'
        command = (
            f'start "VideoScripy-{title}" /min /wait /realtime'
            +f' cmd /c " {self.path[0]}:'
            +f' & cd {self.path}'
        )

        if process == VideoProcess.optimize.value:
            command += (
                ' & ffmpeg'
                +' -hwaccel cuda -hwaccel_output_format cuda'
                +f' -i "{video["path"]}"'
                +' -map 0:v -map 0:a? -map 0:s?'
                +f' -c:v {self.encoder} -c:a copy -c:s copy'
                +f' -b:v {bitRateParam}'
                +f' -r {video["fps"]}'
                +f' -y "{process}\\{video["name"]}" "'
            )

        elif process == VideoProcess.resize.value:
            command += (
                ' & ffmpeg'
                +' -hwaccel cuda -hwaccel_output_format cuda'
                +f' -i "{video["path"]}"'
                +' -map 0:v -map 0:a? -map 0:s?'
                +f' -vf scale_cuda={rWidth}:{rHeight}'
                +f' -c:v {self.encoder} -c:a copy -c:s copy'
                +f' -b:v {bitRateParam}'
                +f' -r {video["fps"]}'
                +f' -y "{process}\\{video["name"]}" "'
            )

        elif process == VideoProcess.upscale.value:
            if not frameToVideo:
                command += (
                    ' & realesrgan-ncnn-vulkan.exe'
                    +f' -i "{video["name"]}_tmp_frames" '
                    +f' -o "{video["name"]}_{process}x{upscaleFactor}_frames" '
                )
                # TODO
                # if upscaleFactor == "4p":
                #     command += ' -n realesrgan-x4plus'
                # elif upscaleFactor == "4pa":
                #     command += ' -n realesrgan-x4plus-anime'
                if upscaleFactor in [2,3,4]:
                    command += f' -n realesr-animevideov3 -s {upscaleFactor}'
                else:
                    print(f'Unknown video process "{upscaleFactor}"')
                    exit()
                command += ' -f jpg -g 1"'
            else:
                command += (
                    ' & ffmpeg'
                    +' -hwaccel cuda -hwaccel_output_format cuda'
                    +f' -c:v mjpeg_cuvid -r {video["fps"]}'
                    +f' -i "{video["name"]}_{process}x{upscaleFactor}_frames/frame%08d.jpg" '
                    +' -hwaccel cuda -hwaccel_output_format cuda'
                    +f' -i "{video["path"]}"'
                    +' -map 0:v:0 -map 1:a? -map 1:s?'
                    +f' -c:v {self.encoder} -c:a copy -c:s copy'
                    +f' -b:v {bitRateParam}'
                    +f' -r {video["fps"]}'
                    +f' -y "{process}\\{video["name"]}" "'
                )

        elif process == VideoProcess.interpolate.value:
            if not frameToVideo:
                command += (
                    ' & ifrnet-ncnn-vulkan.exe'
                    +f' -i "{video["name"]}_tmp_frames" '
                    +f' -o "{video["name"]}_{process}_frames" '
                    +' -m IFRNet_GoPro -g 1 -f frame%08d.jpg'
                    +f' -n {interpolateFrame}"'
                )
            else:
                command += (
                    ' & ffmpeg'
                    +' -hwaccel cuda -hwaccel_output_format cuda'
                    +f' -c:v mjpeg_cuvid -r {fps}'
                    +f' -i "{video["name"]}_{process}_frames/frame%08d.jpg" '
                    +' -hwaccel cuda -hwaccel_output_format cuda'
                    +f' -i "{video["path"]}"'
                    +' -map 0:v:0 -map 1:a? -map 1:s?'
                    +f' -c:v {self.encoder} -c:a copy -c:s copy'
                    +f' -b:v {bitRateParam}'
                    +f' -r {fps}'
                    +f' -y "{process}\\{video["name"]}" "'
                )

        elif process == VideoProcess.merge.value:
            command += (
                ' & ffmpeg'
                +' -hwaccel cuda -hwaccel_output_format cuda'
                +f' {commandInputs}'.format()
                +f' {commandMap}'.format()
                +' -c copy'
                +f' {commandMetadata}'.format()
                +f' -y "{process}\\{video["name"]}" "'
            )
        else:
            print(f'Unknown video process "{process}"')
            exit()
        
        return command


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
            path = video['path']
            name = video['name']
            width = video['width']
            height = video['height']
            bitRate = video['bitRate']
            frameRate = video['fps']

            # show current optimizing video
            print('--- {}/{} ---'.format(index+1,len(self.vList)))
            print(name)
            print('{}x{}'.format(width, height), flush=True)

            # compute optimization bit rate
            optimizedBitRate = width * height * quality
            # save and show bit rate change
            optimizedBitRateText = (
                '{:_.0f} --> {:_.0f} Kbits/s'
                .format(bitRate/1_000, optimizedBitRate/1_000)
            )
            self.vList[index]['optimizedBitRate'] = optimizedBitRateText
            print(optimizedBitRateText)
            bitRateParam = f'{optimizedBitRate} -maxrate:v {optimizedBitRate} -bufsize:v 800M '
            
            # check if optimization needed
            if optimizedBitRate * self.optimizationTolerence > bitRate:
                print('Skiped')
                continue

            command = self._getCommand(
                video, process,
                bitRateParam=bitRateParam
            )
            print(f'Optimizing "{name}"')
            self._runProc(command)

            if self.killed:
                return
            
            print("Done")
        
        # notice optimization end
        noticeProcessEnd()
    
    def resize(self, rWidth:int, rHeight:int, quality:float=3.0) -> None:
        """
        Resize video

        Parameters:
            rWidth (int):
                -1 to let it by default

            rHeight (int):
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
                
            path = video['path']
            name = video['name']
            width = video['width']
            height = video['height']
            bitRate = video['bitRate']
            frameRate = video['fps']

            # show current resizing video
            print('--- {}/{} ---'.format(index+1,len(self.vList)))
            print(name)

            # compute rWidth and rHeight
            if rWidth == -1 and rHeight == -1:
                widthTemp = width
                heightTemp = height
            elif rWidth == -1:
                widthTemp = ceil(width * rHeight/height)
                heightTemp = rHeight
            elif rHeight == -1:
                widthTemp = rWidth
                heightTemp = ceil(height * rWidth/width)
            else:
                widthTemp = rWidth
                heightTemp = rHeight
            
            # to positive size
            widthTemp = abs(widthTemp)
            heightTemp = abs(heightTemp)

            # even widthTemp and heightTemp
            if widthTemp%2 != 0:
                widthTemp += 1
            if heightTemp%2 != 0:
                heightTemp += 1

            # ratio warning
            if widthTemp/heightTemp != width/height:
                print('Warning, rize ratio will be changed')
            
            # save and show size change
            resizedSizeText = (
                '{}x{} --> {}x{}'
                .format(width, height, widthTemp, heightTemp)
            )
            self.vList[index]['resizedSize'] = resizedSizeText
            print(resizedSizeText)
            
            # check if resize needed
            if widthTemp == width and heightTemp == height:
                print("Skiped")
                continue

            # compute resizedBitRate
            resizedBitRate = widthTemp * heightTemp * quality
            # save and show bit rate change
            resizedBitRateText = (
                '{:_.0f} --> {:_.0f} Kbits/s'
                .format(bitRate/1_000, resizedBitRate/1_000)
            )
            self.vList[index]['resizedBitRate'] = resizedBitRateText
            print(resizedBitRateText)
            bitRateParam = f'{resizedBitRate} -maxrate:v {resizedBitRate} -bufsize:v 800M '

            command = self._getCommand(
                video, process,
                bitRateParam=bitRateParam,
                rWidth=widthTemp, rHeight=heightTemp
            )
            print(f'Resizing "{name}"')
            self._runProc(command)

            if self.killed:
                return
            
            print("Done")
        
        # notice resize end
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
                
            path = video['path']
            name = video['name']
            width = video['width']
            height = video['height']
            bitRate = video['bitRate']
            frameRate = video['fps']

            # show current upscaling video
            print('--- {}/{} ---'.format(index+1,len(self.vList)))
            print(name)

            # save and show size change
            upscaledSizeText = (
                '{}x{} --> {}x{}'
                .format(width, height, int(width*upscaleFactor), int(height*upscaleFactor))
            )
            self.vList[index]['upscaledSize'] = upscaledSizeText
            print(upscaledSizeText)

            # compute upscale bit rate
            upscaledBitRate = width * height * quality * upscaleFactor**2
            # save and show bit rate change
            upscaledBitRateText = (
                '{:_.0f} --> {:_.0f} Kbits/s'
                .format(bitRate/1_000, upscaledBitRate/1_000)
            )
            self.vList[index]['upscaledBitRate'] = upscaledBitRateText
            print(upscaledBitRateText)
            bitRateParam = f'{upscaledBitRate} -maxrate {upscaledBitRate} -bufsize 800M '

            ######################
            # region - --get frame

            # wait till end
            self._getFrames(video)
            
            if self.killed:
                return
            
            totalFrames = len(listdir(self.path+'\\{}_tmp_frames'.format(name)))
            
            # endregion frame
            #################

            ####################
            # region - --upscale

            upscaleOutputPath = self.path+f'\\{name}_{process}x{upscaleFactor}_frames'
            # create upscaled frames folder if not existing
            if not isdir(upscaleOutputPath):
                mkdir(upscaleOutputPath)
                print(f'Upscaling "{name}"')

            # continue existing frames upscale
            else:
                for root, _, files in walk(upscaleOutputPath):
                    # remove upscaled frame's origin frames except last two
                    for upscaled in files[:-2]:
                        remove(root.replace(f'_{process}x{upscaleFactor}_frames','_tmp_frames')+'\\'+upscaled)
                    # remove last two upscaled frames
                    for lastTwoUpscaled in files[-2:]:
                        remove(root+'\\'+lastTwoUpscaled)
                print(f'Continue upscaling "{name}"')
            
            command = self._getCommand(
                video, process,
                upscaleFactor=upscaleFactor
            )

            # frames watch
            watch = Thread(
                target=frameWatch,
                args=(upscaleOutputPath,totalFrames)
            )
            watch.start()
            
            self._runProc(command)

            if self.killed:
                global stop_threads
                stop_threads = True
                while watch.is_alive():
                    pass
                return
            else:
                watch.join()

            # remove frames
            rmtree(self.path+'\\{}_tmp_frames'.format(name))
            
            # endregion upscale
            ###################

            ###########################
            # region - --frame to video

            # upscaled frames to video
            command = self._getCommand(
                video, process,
                bitRateParam=bitRateParam,
                upscaleFactor=upscaleFactor,
                frameToVideo=True
            )
            print(f'Upscaling frame to video "{name}"')
            self._runProc(command)

            if self.killed:
                return
            
            print("Done")
            
            # remove upscaled frames
            rmtree(upscaleOutputPath)
            
            # endregion frame to video
            ##########################
            
            self.vList[index]['upscaleFactor'] = upscaleFactor

        # notice upscale end
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

            path = video['path']
            name = video['name']
            width = video['width']
            height = video['height']
            bitRate = video['bitRate']
            frameRate = video['fps']
            duration = video['duration']

            # show current resizing video
            print('--- {}/{} ---'.format(index+1,len(self.vList)))
            print(name)

            # check if interpolation needed
            if fps < frameRate:
                print("Skiped")
                print(fps, '<', frameRate)
                continue

            # save and show interpolate change
            interpolateFrame = int(duration.total_seconds() * fps)
            interpolateFrameText = (
                '{}fps --> {}fps'
                .format(frameRate, fps)
            )
            self.vList[index]['interpolateFrame'] = interpolateFrameText
            print(interpolateFrameText)

            # compute interpolate bit rate
            interpolateBitRate = width * height * quality
            # save and show bit rate change
            interpolateBitRateText = (
                '{:_.0f} --> {:_.0f} Kbits/s'
                .format(bitRate/1_000, interpolateBitRate/1_000)
            )
            self.vList[index]['interpolateBitRate'] = interpolateBitRateText
            print(interpolateBitRateText)
            bitRateParam = f'{interpolateBitRate} -maxrate:v {interpolateBitRate} -bufsize:v 800M '

            ######################
            # region - --get frame

            # wait till end
            self._getFrames(video)

            if self.killed:
                return
            
            # endregion frame
            #################
            
            ####################
            # region - --interpolate

            interpolateOutputPath = self.path+f'\\{name}_{process}_frames'
            # empty interpolate frames folder
            if isdir(interpolateOutputPath):
                rmtree(interpolateOutputPath)

            # new frames interpolate
            mkdir(interpolateOutputPath)
            command = self._getCommand(
                video, process,
                interpolateFrame=interpolateFrame
            )
            print(f'Interpolating "{name}"')

            # frames watch
            watch = Thread(
                target=frameWatch,
                args=(interpolateOutputPath,interpolateFrame)
            )
            watch.start()

            self._runProc(command)
            
            if self.killed:
                global stop_threads
                stop_threads = True
                while watch.is_alive():
                    pass
                return
            else:
                watch.join()

            # remove frames
            rmtree(self.path+'\\{}_tmp_frames'.format(name))
            
            # endregion interpolate
            ###################

            ###########################
            # region - --frame to video

            # interpolate frames to video
            command = self._getCommand(
                video, process,
                bitRateParam=bitRateParam,
                fps=fps,
                frameToVideo=True
            )
            print(f'Interpolating frame to video "{name}"')
            self._runProc(command)

            if self.killed:
                return

            print("Done")

            # remove upscaled frames
            rmtree(interpolateOutputPath)
            
            # endregion frame to video
            ##########################
            
            self.vList[index]['interpolateFrame'] = fps

        # notice interpolate end
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
            print("0 or 1 video is not enought to merge")
            return

        # check video length
        duration = self.vList[0]['duration']
        for video in self.vList:
            if duration != video['duration']:
                print(f'Warning, "{video["name"]}" has different duration')
        
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

        command = self._getCommand(
            video, process,
            commandInputs=commandInputs,
            commandMap=commandMap,
            commandMetadata=commandMetadata,
        )
        print(f'Merging {len(self.vList)} videos')
        self._runProc(command)

        if self.killed:
            return

        print("Done")
        
        # notice merging end
        noticeProcessEnd()

    # endregion processes
    #####################



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




