<div align="center">

# <img src="./assets/favicon.ico" alt="drawing" width="20px"/> VideoScripy

[**English**](./README.md) | **中文简体**

**画质无损，空间节省。**

视频压缩、流处理、AI放大 与 AI插帧 等 视频处理模块的合集。

![demo.gif](./doc/demo_upscale.gif)

</div>



## 目录

- [视频处理模块说明](#视频处理模块说明)
- [环境要求](#环境要求)
- [整合安装](#整合安装)
- [手动安装](#手动安装)
- [致谢](#致谢)



## 视频处理模块说明

- 压缩  
    降低视频码率，节省存储空间
    <details>
    <summary>点击展开</summary>
        处理后的视频将具有以下比特率：比特率 = 宽 × 高 × 质量。
        通常， 质量=3 是画质不会出现明显下降的最小值，质量3与6在人眼下无显著差异。 
    </details>
    
    ![demo_upscale_s](./doc/demo_compress_illus.png)

- 尺寸调整  
    降低视频的宽度和高度。
    
    ![demo_upscale_s](./doc/demo_resize_illus.png)

- GIF转换
    将视频转换为动态 GIF，可设置输出宽度、高度和帧率。默认保留原始尺寸并使用 10 FPS；宽度或高度设为 -1 时按原比例缩放。

    GIF 的每一帧都不做帧间压缩，因此长视频、高分辨率会得到很大的文件。
    影响体积的四个参数为：输出 `宽度 x 高度`、`帧率`、调色板 `最大颜色数`（2-256）和 `抖动`（dither）。
    在 1080x1920、时长 2 分钟的视频上实测：

    | 宽度 x 高度 | 帧率 | 最大颜色数 | 抖动 | 体积 |
    | --- | --- | --- | --- | --- |
    | 1080x1920（原始） | 10 | 256 | sierra2_4a | 约 800 MB |
    | 540x960 | 8 | 128 | bayer | 约 170 MB |
    | 360x640 | 8 | 64 | none | 约 45 MB |

- AI放大  
    使用 AI 将视频尺寸按2、3、4倍提升，同时增强画质。  
    支持从上次未完成的帧继续处理，如果 "_upscaledx?_frame" 文件夹未删除。
    <details>
    <summary>点击展开</summary>
        先将视频转为图像帧，逐帧放大后再重新合成为视频。 
    </details>
    
    <ins>原视频 : 266x200</ins>

    ![demo_upscale_s](./doc/demo.gif)

    <ins>2倍放大 : 532x400</ins>

    ![demo_upscale_b](./doc/demo_upscale_x2.gif)

    <ins>3倍放大 : 798x600</ins>
    
    ![demo_upscale_b](./doc/demo_upscale_x3.gif)

    <ins>4倍放大 1064x800</ins>
    
    ![demo_upscale_b](./doc/demo_upscale_x4.gif)
    
- AI插帧  
    提高视频帧率，使视频更流畅 
    <details>
    <summary>点击展开</summary>
        先将视频转为图像帧，在帧之间插入中间帧，最后重新合成为视频。
    </details>

    <ins>插帧：25帧 -> 60帧</ins>
    
    ![demo_upscale_s](./doc/demo.gif)
    ![demo_upscale_s](./doc/demo_interpolate_60fps.gif)
    
    由于 markdown 限制，60帧 动图可能会以0.5倍速播放，请使用合适播放器查看。

- 预览  
    生成图像网格预览

    <ins>2 分钟倒计时视频的 3x2 预览 </ins>
    
    ![demo_preview](./doc/demo_preview.png)
    
- 帧  
    绘制每一帧的比特率图

    <ins>266x200， 时长 10 秒的视频</ins>

    ![demo_preview](./doc/demo_frame.png)


- 视频流  
    合并多个视频的不同流（视频、音频、字幕）为一个文件。  
    并可修改标题、语言等元信息。  
    使用 PotPlayer 等播放器可切换音视频流。 

    ![demo_upscale_s](./doc/demo_stream_illus.png) 



## 环境要求

- Windows 操作系统
- NVIDIA 显卡（加速视频处理）
- 至少 50GB 硬盘空间用于AI放大处理 | AI插帧处理需 10GB
- Python 3.13（仅源码安装需要）
- [工具](#下载与安装-1)



## 整合安装

整合包已包含 Python 运行时、Python 依赖和工具，目标电脑无需安装 Python。
优点：**适合小白**

### 使用方式

从[最新版本](https://github.com/luewh/Video-Script/releases/latest)下载便携文件夹，然后运行其中的启动脚本。

运行 `Run VideoScripyWebUI.bat`，它会启动内置 Python 并打开 WebUI，不需要应用专用的 exe。使用 NVIDIA GPU 功能需要安装兼容的显卡驱动。

## 手动安装

需要下载源码、安装 Python 及其依赖，并将工具放入项目的 `tools` 文件夹。程序启动时会将本地工具目录加入自身进程的 PATH，无需修改系统 PATH。
优点：**自由**

### 下载与安装

1. 下载源码并解压。

2. 如果未安装 Python 3.13，请安装。

3. 安装依赖：
    ```shell
    pip install -r requirements.txt
    ```

4. 工具下载：

    [FFmpeg](https://www.gyan.dev/ffmpeg/builds/) 全功能版本用于硬件加速  
    [Real-ESRGAN-ncnn-vulkan](https://github.com/xinntao/Real-ESRGAN-ncnn-vulkan/releases) 用于视频放大  
    [Ifrnet-ncnn-vulkan](https://github.com/nihui/ifrnet-ncnn-vulkan/releases) 用于视频插帧  
    [NVEncC](https://github.com/rigaya/NVEnc) 用于检测 GPU 功能

5. 工具路径添加：

    创建 ”tools” 文件夹并放入所有工具，具体如下：
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
    │   └───NVEncC
    │   │   │   NVEncC64.exe
    |...
    ```

### 使用方式

运行 `python VideoScripyWebUI.py` 启动 Dash 网页界面。
直接运行 `python VideoScripy.py` 会初始化并扫描当前文件夹以便手动调试；
可在其 `__main__` 代码块中取消注释某个操作调用来执行相应操作。



## 致谢

本项目使用了以下开源工具和项目：
- [alive-progress](https://github.com/rsalmei/alive-progress)
- [Real-ESRGAN](https://github.com/xinntao/Real-ESRGAN)
- [IFRNet](https://github.com/ltkong218/IFRNet)
- [FFmpeg](https://www.ffmpeg.org/)
- [FFmpeg-python](https://github.com/kkroening/ffmpeg-python)
- [Dash](https://dash.plotly.com/)
- [NVEncC](https://github.com/rigaya/NVEnc)

音效素材来源：
- [Pixabay](https://pixabay.com/sound-effects/search/typewriter/)
