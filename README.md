
# <img src="./assets/favicon.ico" alt="drawing" width="20px"/> VideoScripy & WebUI 

VideoScripy is a collection of video processes including video **Upscale** and video frame **Interpolation**, it uses Python to generate **FFmpeg**, **Real-ESRGAN** and **IFRNet** command line script and performes serial processing on scanned **mp4**/**mkv** videos.

VideoScripyWebUI is a local web user interface developed with **Dash**, it has the goal of enhancing user experience.
![demo.gif](./doc/demo_upscale.gif)

> <span style="color:red">**⚠ Currently only compatible with Windows users who have Nvidia cards.**</span> 



## Table of contents

- [Embedded version](#embedded-version)
    * [Installation](#installation)
    * [Usage](#usage)
<!-- 
- [Self setup version](#self-setup-version)
    * [Installation](#installation-1)
    * [Usage](#usage-1) -->

- [Benchmarking](#benchmarking)

- [Processes Description](#processes-description)

- [Credits](#credits)
<!-- 
- [TODO list](#todo-list) -->



## Embedded version

Simplest. Python, Tools are already setup.  
Advantage : **Beginner-friendly**

### Installation

1. Download and extract the [Embedded release](https://github.com/luewh/Video-Script/releases/latest)

### Usage

- Run the `RUN.bat` to launch WebUI

<!-- 

## Self setup version

Need to install Python dependencies, add tools to PATH manually.  
Advantage : **Freedom**

### Installation

1. Download and extract the [SelfSetup release](https://github.com/luewh/Video-Script/releases/latest)

2. Download and install Python 3.10 if you dont have.

3. Install dependencies

    ```shell
    pip install -r requirements.txt
    ```
 
4. Add tools to PATH

    Below tools are included in self setup release :

    [FFmpeg](https://www.gyan.dev/ffmpeg/builds/) full build for hardware acceleration.

    [Real-ESRGAN-ncnn-vulkan](https://github.com/xinntao/Real-ESRGAN-ncnn-vulkan/releases) for video upscaling.
    
    [Ifrnet-ncnn-vulkan](https://github.com/nihui/ifrnet-ncnn-vulkan/releases) for video frame interpolation.  
    
    <span style="color:orange">**Important**</span>  

    Make sure to add  

    - `<pathTo>\ffmpeg-full_build\bin`
    - `<pathTo>\Real-ESRGAN`
    - `<pathTo>\Ifrnet`

    in the environment variable *PATH* -->


<!-- 
### Usage

- VideoScripy.py

    Run the script on where videos are located and follow the command line indication

- VideoScripyWebUI.py

    Run the script, a web page should be opened automatically, select a process, select a path where videos are located, **SCAN** then **RUN**. The processed videos are under a folder of selected path example ./upscaled.
 -->


## Benchmarking

- ### x3 Faster FFprobe by running it "asynchronously"
![Fast FFprobe](./doc/faster_way_to_run_ffprobe.png)
(ffprobe on 64 ~2h long videos)




## Processes Description

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

This project relies on the following software and projects :
- [alive-progress](https://github.com/rsalmei/alive-progress)
- [Real-ESRGAN](https://github.com/xinntao/Real-ESRGAN)
- [IFRNet](https://github.com/ltkong218/IFRNet)
- [FFmpeg](https://www.ffmpeg.org/)
- [FFmpeg-python](https://github.com/kkroening/ffmpeg-python)
- [Dash](https://dash.plotly.com/)

Sounds come from :
- [Pixabay](https://pixabay.com/sound-effects/search/typewriter/)

<!-- 
## TODO list

- ✅ stdout to Dash
- ✅ alive-progress ANSI Escape Code "?25l" render problem
- ✅ License
- ✅ Favicon
- ✅ Embed release
- ✅ Stop upscale and interpolate process
- ✅ Get video walk optimize
- ✅ Arrange process select UI
- ✅ Better row height
- ✅ Select / Unselect all videos
- ✅ Sort video by properties
- ✅ Sort by name in WebUI and VS
- ✅ Skip video if "&" present in video path and name
- [N] Add FFmpeg visual quality metrics (PSNR, SSIM, VMAF)
- ✅ Better encoders parameters
- ✅ Remove empty folders
- [ ] Catch process error, and stop frame watch thread appropriately
- [ ] Check tools
- ✅ framesToVideo()
- [ ] Running disable all new button
- [ ] Separate repository for WebUI
- [ ] Better upscale recovery
- [ ] Gif to explain processes, tooltip on process dropdown
- [ ] Log ?
 -->

