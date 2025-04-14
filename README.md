# <img src="./assets/favicon.ico" alt="drawing" width="20px"/> VideoScripy & WebUI 

VideoScripy is a collection of video processes including video **Upscale** and video frame **Interpolation**, it uses Python to generate **FFmpeg**, **Real-ESRGAN** and **IFRNet** command line script and performes serial processing on scanned **mp4** videos with **hardware acceleration**.

VideoScripyWebUI is a local web user interface developed with **Dash**, it has the goal of enhancing user experience.
![demo.gif](./doc/demo_upscale.gif)

<!-- > <span style="color:red">**⚠ Currently only compatible with Windows users who have Nvidia cards.**</span>  -->



## Table of contents

- [Requirements](#requirements)
- [Embedded version](#embedded-version)
- [Self setup version](#self-setup-version)
- [Processes Description](#processes-description)
- [Benchmarking](#benchmarking)
- [Credits](#credits)



## Requirements

- Windows OS
- NVIDIA GPU for faster video process
- Atleast 50 Go disk space free for Upscale process | 10 Go for Interpolate process
- Python 3.10
- [Tools](#installation-1)


## Embedded version

Simplest. Python, Tools are already setup.  
Advantage : **Beginner-friendly**

### Installation

Download and extract the [Embedded release](https://github.com/luewh/Video-Script/releases/latest)

### Usage

Run the `VideoScripyWebUI.bat`



## Self setup version

Need to download the source codes, install Python and its dependencies, download tools and include them to tools folder or add them to PATH.    
Advantage : **Freedom**

### Installation

1. Download the source code and extract.

1. Download and install Python 3.10 if you dont have.

2. Install dependencies
    ```shell
    pip install -r requirements.txt
    ```
 
3. Download tools

    [FFmpeg](https://www.gyan.dev/ffmpeg/builds/) full build for hardware acceleration.  
    [Real-ESRGAN-ncnn-vulkan](https://github.com/xinntao/Real-ESRGAN-ncnn-vulkan/releases) for video upscaling.  
    [Ifrnet-ncnn-vulkan](https://github.com/nihui/ifrnet-ncnn-vulkan/releases) for video frame interpolation.  
    [NVEncC](https://github.com/rigaya/NVEnc) for GPU feature detection.  

4. Include tools
    
    Create a "tools" folder and place tools in like this:
    ```
    VideoScripy
    │   ...
    │   VideoScripyWebUI.py 
    └───tools
    │   └───ffmpeg-full_build
    │   │   │   ...
    │   │   └───bin
    │   │       │   ffmpeg.exe
    │   │       │   ffprobe.exe
    │   └───Real-ESRGAN
    │   │   │   ...
    │   │   │   realesrgan-ncnn-vulkan.exe
    │   └───Ifrnet
    │   │   │   ...
    │   │   │   ifrnet-ncnn-vulkan.exe
    |...
    ```

    Or add them in the environment variable *PATH*
    - `<pathTo>\ffmpeg-full_build\bin`
    - `<pathTo>\Real-ESRGAN`
    - `<pathTo>\Ifrnet`
    - `<pathTo>\NVEnc`

### Usage

Run the `VideoScripyWebUI.py`



## Processes Description

- optimize  
    Reduce the video biteRate in order to gain storage space.  
    <details>
    <summary>expand more</summary>
        The processed videos will have a bitRate = width * height * quality, quality=3 is generally the lowest value before appearance of artifacts (bad images, blurry...). In other words, humain wont notice the visual difference between video of quality 3 and 6.
    </details>

- resize  
    Reduce the video width and height.

- upscale  
    Increase video size by factor of 2,3 or 4 with AI, enhance video quality.  
    <details>
    <summary>expand more</summary>
        Begin with a transformation of video to image frames, then upscale each frames, finally reassemble to video.  
        It has the ability to start from last upscal progress if the "_upscaledx?_frame" wasn't deleted.
    </details>

    From 266x200 to 1064x800  
    ![demo_upscale_s](./doc/demo_upscale_small.png)
    ![demo_upscale_b](./doc/demo_upscale_big.png)

- interpolate  
    Increase video frame rate (FPS), smooth video.  
    <details>
    <summary>expand more</summary>
        Begin with a transformation of video to image frames, then interpolate between frames, finally reassemble to video.
    </details>

- preview  
    Generate a grid of images.  
    3x2 grid of 2min countdown video :
    ![demo_preview](./doc/demo_preview.png)

- stream  
    Merge selected stream of multiple videos into one video.  
    And also modify metadata as tile and language.  
    Then use media player as PotPlayer to switch between video/audio/subtitle.



## Benchmarking

- ### x3 Faster FFprobe by running it "asynchronously"
    ffprobe on 64 videos, ~2h long each  
    ![Fast FFprobe](./doc/faster_way_to_run_ffprobe.png)



## Credits

This project relies on the following software and projects :
- [alive-progress](https://github.com/rsalmei/alive-progress)
- [Real-ESRGAN](https://github.com/xinntao/Real-ESRGAN)
- [IFRNet](https://github.com/ltkong218/IFRNet)
- [FFmpeg](https://www.ffmpeg.org/)
- [FFmpeg-python](https://github.com/kkroening/ffmpeg-python)
- [Dash](https://dash.plotly.com/)
- [NVEncC](https://github.com/rigaya/NVEnc)

Sounds come from :
- [Pixabay](https://pixabay.com/sound-effects/search/typewriter/)


