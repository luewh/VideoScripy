

# VideoScript & WebUI

VideoScript is a collection of video processes including video **Upscale** and video frame **Interpolation**, it uses Python to generate **FFmpeg**, **Real-ESRGAN** and **IFRNet** command line script and performes serial processing on scanned **mp4**/**mkv** videos.

VideoScriptWebUI is a local web user interface developed with **Dash**, it has the goal of enhancing user experience.
![demo.gif](./doc/demo.gif)



## Installation

- Download the repo

- Download and install Python

- Requirements (Tested on Python 3.10)

    ```shell
    pip install -r requirements.txt
    ```

- Hardware

    NVIDIA card and [CUDA Toolkit](https://developer.nvidia.com/cuda-toolkit) are needed for FFmpeg hardware acceleration.

- Tools

    [FFmpeg](https://www.ffmpeg.org/download.html) full build is needed for hardware acceleration.  
    [Real-ESRGAN-ncnn-vulkan](https://github.com/xinntao/Real-ESRGAN-ncnn-vulkan/releases) is needed for video upscaling.  
    [Ifrnet-ncnn-vulkan](https://github.com/nihui/ifrnet-ncnn-vulkan/releases) is needed for frame interpolation.  
    
    > <span style="color:orange">**⚠ Important**</span>  
    > Make sure to put  
    > *pathTo\ffmpeg-full_build\bin*  
    > *pathTo\Real-ESRGAN* and  
    > *pathTo\Ifrnet*  
    > in the environment variable *PATH*



## Usage

- VideoScript.py

    Run the script on where videos are located and follow the command line indication

- VideoScriptWebUI.py

    Run the script, a web page should be opened automatically, select a process, select a path where videos are located, **SCAN** then **RUN**. The processed videos are under a folder of selected path example ./upscaled.



## Processes

- optimize

    Reduce the video biteRate in order to gain storage space.  
    The processed videos will have a bitRate = width * height * quality, which quality=3 is generally the lowest value before appearance of artifacts (bad images, blurry...). In other words, humain wont notice the visual difference between video of quality 3 and 6.

- resize

    Reduce the video width and height.

- upscale

    Recover old video from 360p to 4K, enhance video quality.  
    Begin with a transformation of video to image frames, then upscale each frames, finally reassemble to video.   
    It has the ability to start from last upscal progress if the "_upscaled_frame" wasn't deleted.

- interpolate

    Increase video frame rate (FPS), smooth video motions.  
    Begin with a transformation of video to image frames, then interpolate between frames, finally reassemble to video.

- merge

    Merge all video, including each of its audio and subtitle by option, into mkv. Then use media player as PotPlayer to switch between video/audio/subtitle.



## Credits

This project relies on the following software and projects.
- [alive-progress](https://github.com/rsalmei/alive-progress)
- [Real-ESRGAN](https://github.com/xinntao/Real-ESRGAN)
- [IFRNet](https://github.com/ltkong218/IFRNet)
- [FFmpeg](https://www.ffmpeg.org/)
- [Dash](https://dash.plotly.com/)



## TODO list

- [X] stdout to Dash
- [ ] Stop upscale and interpolate process, at the same time stdout to Dash
- [ ] Embed release
- [ ] Gif to explain processes, tooltip on process dropdown
- [ ] Remain vh for div_processRunning
- [ ] Log ?


