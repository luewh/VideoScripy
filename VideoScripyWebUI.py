# built-in
import os
from sys import stdout, stderr
from time import sleep, time
from datetime import timedelta
from webbrowser import open_new
from threading import Timer

# dependencies
from dash import Dash, dcc, html
from dash import no_update, ctx, callback, ALL, MATCH
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from tkinter import Tk, filedialog

# own class
from VideoScripy import *


addPath = []
addPath.append("./tools/ffmpeg-full_build/bin")
addPath.append("./tools/Real-ESRGAN")
addPath.append("./tools/Ifrnet")
addPath.append("./tools/NVEncC")
for index, path in enumerate(addPath):
    addPath[index] = os.path.abspath(path)
os.environ["PATH"] += os.pathsep.join(addPath)

IP = "localhost"
PORT = "8848"

# extend VideoInfo
class VideoInfo(VideoInfo):
    selected: bool

vs = VideoScripy()
allVideoList:list[VideoInfo] = []
processes = [p.name for p in VideoProcess]
videoSizesDict = [
    {"label":"240p/SD", "width":426, "height":240},
    {"label":"360p/SD", "width":640, "height":360},
    {"label":"480p/SD", "width":854, "height":480},
    {"label":"720p/HD", "width":1280, "height":720},
    {"label":"1080p/FHD", "width":1920, "height":1080},
    {"label":"1440p/2K", "width":2560, "height":1440},
    {"label":"2160p/4K", "width":3840, "height":2160},
    {"label":"4320p/8K", "width":7680, "height":4320},
]
videoQualityDict = [
    {"label":"low : 1", "value":1},
    {"label":"best : 3", "value":3},
    {"label":"ultra : 6", "value":6},
]
upscaleFactor = [2, 3, 4]
videoItemColor = {
    True:"info",
    False:"dark",
}
videoSortBy = [
    "name",
    "width", "height", "w x h",
    "fps",
    "duration",
    "bitRate",
    "fileSize"
]
langDict = [
    {"label": "Undifined | undifined",
     "value": "und"},
    {"label": "English | english",
     "value": "eng"},
    {"label": "Chinese | 中文",
     "value": "zho"}, #chi
    {"label": "Japanese | 日本語",
     "value": "jpn"},
    {"label": "Korean | 한국어",
     "value": "kor"},
    {"label": "Hindi | हिन्दी",
     "value": "hin"},
    {"label": "Spanish | español",
     "value": "spa"},
    {"label": "French | français",
     "value": "fra"}, #fre
    {"label": "Arabic | العربية",
     "value": "ara"},
    {"label": "Bengali | বাংলা",
     "value": "ben"},
    {"label": "Portuguese | português",
     "value": "por"},
    {"label": "Urdu | اُردُو",
     "value": "urd"},
    {"label": "Dutch | nederlands",
     "value": "nld"}, #dut
    {"label": "German | deutsch",
     "value": "deu"}, #ger
]
encoderDict = [
    {"label": "H265",
     "value": True},
    {"label": "H264",
     "value": False},
]


app = Dash(
    __name__,
    external_stylesheets=[],
    title="VS WebUI",
    update_title=None,
    # rescale layout for mobile device
    meta_tags=[{
        'name':'viewport',
        'content':'width=device-width, initial-scale=1.0',
    }],
    # not warn component Inputs, States, and Output not present in the layout
    suppress_callback_exceptions=True,
)

app.layout = html.Div(
    dbc.Row(
        children=[
            # hidden component
            html.Button(
                id="button_clientClose",
                hidden=True,
                n_clicks=0,
            ),
            dcc.Interval(
                id="interval_log",
                interval=1.0 * 1000,
                n_intervals=0,
                disabled=True,
            ),
            dbc.Tooltip(
                "SCAN atleast once to RUN",
                id="tooltip_run",
                target="button_runProcess",
                delay={"show": 500, "hide": 0},
            ),
            dbc.Tooltip(
                "let it empty will return to default path",
                target="input_path",
                delay={"show": 500, "hide": 0},
            ),
            # process select UI
            dbc.Col(
                children=[
                    # header
                    html.Div(
                        [
                            html.H6(
                                "Process :",
                                className="ch_h6_title",
                            ),
                            dbc.Stack(
                                [
                                    dbc.Col(
                                        dcc.Dropdown(
                                            processes,
                                            value=processes[0],
                                            placeholder="Select a process ...",
                                            id="dropdown_processes",
                                            maxHeight=233,
                                            optionHeight=28,
                                            searchable=True,
                                            clearable=False,
                                            className="dcc_dropdown",
                                            persistence_type="local",
                                            persistence=True,
                                        ),
                                        width=6,
                                    ),
                                    dbc.Tooltip(
                                        [
                                            html.Div("H265 has better compression but slower than H264."),
                                            html.Div("H264 video is playable on most of devices while H265 not."),
                                        ],
                                        target="dropdown_encoder",
                                        placement="left",
                                        delay={"show": 1500, "hide": 0},
                                    ),
                                    dbc.Col(
                                        dcc.Dropdown(
                                            encoderDict,
                                            value=vs.h265,
                                            placeholder="Select a enccoder ...",
                                            id="dropdown_encoder",
                                            maxHeight=233,
                                            optionHeight=20,
                                            searchable=True,
                                            clearable=False,
                                            style={
                                                "height":"5vh",
                                                "font-size":"10px",
                                                "color":"black",
                                            },
                                        ),
                                        width=2,
                                    ),
                                    dbc.Tooltip(
                                        [
                                            html.Div("GPU is fast but has lower quality than CPU."),
                                            html.Div("GPU is recommanded on AI process like upscale and interpolate."),
                                        ],
                                        target="dropdown_device",
                                        placement="left",
                                        delay={"show": 1500, "hide": 0},
                                    ),
                                    dbc.Col(
                                        dcc.Dropdown(
                                            [
                                                {
                                                    "label" : devices["name"],
                                                    "value" : devices["id"],
                                                } for devices in vs.devices
                                            ],
                                            value=vs.selectedDevice["id"],
                                            placeholder="Select a hardware ...",
                                            id="dropdown_device",
                                            maxHeight=233,
                                            optionHeight=20,
                                            searchable=True,
                                            clearable=False,
                                            style={
                                                "height":"5vh",
                                                "font-size":"10px",
                                                "color":"black",
                                            },
                                        ),
                                        width=4,
                                    )
                                ],
                                direction="horizontal",
                            ),
                            html.Hr(className="ch_hr"),
                        ],
                        className="ch_div_header"
                    ),
                    # param
                    html.Div(
                        id="div_processParamUI",
                        className="psu_div_param"
                    ),
                    # process buttons
                    dbc.Stack(
                        [
                            dbc.Col(
                                dcc.Loading(
                                    html.Button(
                                        "RUN",
                                        id="button_runProcess",
                                        n_clicks=0,
                                        disabled=True,
                                        className="html_button_big",
                                    ),
                                    color="white",
                                ),
                            ),
                            dbc.Col(
                                html.Button(
                                    "STOP",
                                    id="button_stopProcess",
                                    n_clicks=0,
                                    disabled=True,
                                    className="html_button_big",
                                ),
                            ),
                        ],
                        direction="horizontal",
                        className="psu_stack_process_buttons",
                    ),
                    # terminal
                    html.Div(
                        id="div_processRunning",
                        disable_n_clicks=True,
                        className="psu_div_terminal",
                    ),
                ],
                width=5,
                # md=5,
                className="psu",
            ),
            # video select UI
            dbc.Col(
                children=[
                    # header
                    html.Div(
                        [
                            html.H6(
                                "Path :",
                                disable_n_clicks=True,
                                className="ch_h6_title",
                            ),
                            dbc.Stack(
                                [
                                    dbc.Col(
                                        dcc.Loading(
                                            html.Button(
                                                "SCAN",
                                                id="button_scanFiles",
                                                className="html_button_big",
                                            ),
                                            color="white",
                                        ),
                                        width=1,
                                    ),
                                    dbc.Col(
                                        dcc.Input(
                                            id="input_path",
                                            type="text",
                                            value=vs.path,
                                            persistence_type="local",
                                            persistence=True,
                                            disabled=True,
                                            n_submit=0,
                                            className="dcc_input",
                                        ),
                                        width=8,
                                    ),
                                    dbc.Col(
                                        html.Button(
                                            "EDIT",
                                            id="button_editPath",
                                            className="html_button_big",
                                        ),
                                        width=1,
                                    ),
                                    dbc.Col(
                                        html.Button(
                                            "SELCT",
                                            id="button_selectDir",
                                            className="html_button_big",
                                        ),
                                        width=1,
                                    ),
                                    dbc.Col(
                                        html.Button(
                                            "OPEN",
                                            id="button_openDir",
                                            className="html_button_big",
                                        ),
                                        width=1,
                                    ),
                                ],
                                direction="horizontal",
                            ),
                            html.Hr(className="ch_hr"),
                        ],
                        className="ch_div_header"
                    ),
                    # select & sort buttons
                    dbc.Stack(
                        [
                            dbc.Col(
                                html.Button(
                                    "ALL",
                                    id="button_lvideo_all",
                                    className="html_button_big",
                                ),
                                width=1
                            ),
                            dbc.Col(
                                html.Button(
                                    "NONE",
                                    id="button_lvideo_none",
                                    className="html_button_big",
                                ),
                                width=1,
                            ),
                            dbc.Col(
                                html.Button(
                                    "INVERT",
                                    id="button_lvideo_invert",
                                    className="html_button_big",
                                ),
                                width=1,
                            ),
                            dbc.Col(
                                html.Button(
                                    "↑↓",
                                    id="button_lvideo_revert",
                                    className="html_button_big",
                                ),
                                width={"size": 1, "offset": 6},
                            ),
                            dbc.Col(
                                dcc.Dropdown(
                                    videoSortBy,
                                    placeholder="SORT",
                                    id="dropdown_lvideo_sort",
                                    maxHeight=233,
                                    optionHeight=28,
                                    searchable=False,
                                    clearable=False,
                                    className="dcc_dropdown",
                                ),
                                width=2,
                            ),
                        ],
                        direction="horizontal",
                        className="vsu_stack_buttons",
                    ),
                    # video item list
                    dbc.ListGroup(
                        id="list_videos",
                        className="vsu_list_group",
                    ),
                ],
                width=7,
                # md=7,
                className="vsu",
            )
        ],
    ),
    className="hp_div",
)



@callback(
    Output("button_clientClose", "children"),
    Input("button_clientClose", "n_clicks"),
    prevent_initial_call=True,
)
def clientClose(_):
    global IP, PORT
    text = f"Dash is running on http://{IP}:{PORT}/"
    print("-"*(len(text)+4))
    print("| "+text+" |")
    print("-"*(len(text)+4))
    raise PreventUpdate



@callback(
    Output("dropdown_encoder", 'value'),
    Input("dropdown_encoder", 'value'),
    Input("dropdown_device", 'value'),
    running=[(Output('interval_log', 'n_intervals'), 0, 0)],
    prevent_initial_call=True,
)
def setVideoEncoderOrDevice(encoder, device):
    global vs
    if ctx.triggered_id == "dropdown_encoder":

        if encoder is None:
            raise PreventUpdate

        vs.setEncoder(encoder)

        return vs.h265
    
    elif ctx.triggered_id == "dropdown_device":

        if device is None:
            raise PreventUpdate
        
        vs.selectDevice(device)

        return vs.h265



def qualityInputUI():
    global videoQualityDict
    return [
        html.Div(
            "video quality",
            # className="div_text_simple",
        ),
        dbc.Stack(
            [
                dcc.Input(
                    id={"type": "input", "id": "videoQuality"},
                    type="number",
                    value=3.0,
                    min=0.1,
                    max=9.9,
                    step=0.1,
                    persistence_type="local",
                    persistence=True,
                    className="dcc_input",
                    style={"width":"50px"},
                ),
                dbc.Tooltip(
                    "bitrate = width * height * quality",
                    target={"type": "spec", "id": "dropdown_videoQuality"},
                    delay={"show": 500, "hide": 0},
                ),
                dcc.Dropdown(
                    [videoQuality["label"] for videoQuality in videoQualityDict],
                    placeholder="STANDAR QUALITY",
                    id={"type": "spec", "id": "dropdown_videoQuality"},
                    searchable=False,
                    clearable=False,
                    maxHeight=70,
                    optionHeight=19,
                    className="dcc_dropdown",
                    style={"width":"180px"},
                ),
            ],
            direction="horizontal",
        ),
    ]

def resizeInputUI():
    global videoSizesDict
    return [
        html.Div(
            "width x height",
            className="div_text_simple",
            disable_n_clicks=True,
        ),
        dbc.Stack(
            [
                dcc.Input(
                    id={"type": "input", "id": "videoWidth"},
                    type="number",
                    value=1920,
                    persistence_type="local",
                    persistence=True,
                    min=-1,
                    max=8192,
                    step=1,
                    className="dcc_input",
                    style={"width":"65px"},
                ),
                html.Button(
                    "X",
                    id={"type": "spec", "id": "button_sizeSwitch"},
                    n_clicks=0,
                    className="html_button_big",
                    style={"width":"5vh"},
                ),
                dcc.Input(
                    id={"type": "input", "id": "videoHeight"},
                    type="number",
                    value=1080,
                    persistence_type="local",
                    persistence=True,
                    min=-1,
                    max=8192,
                    step=1,
                    className="dcc_input",
                    style={"width":"65px"},
                ),
                dcc.Dropdown(
                    [videoSizes["label"] for videoSizes in videoSizesDict],
                    placeholder="STANDAR SIZE",
                    id={"type": "spec", "id": "dropdown_videoSize"},
                    searchable=False,
                    clearable=False,
                    maxHeight=115,
                    optionHeight=19,
                    className="dcc_dropdown",
                    style={"width":"140px"},
                ),
            ],
            direction="horizontal",
        ),
    ]

def upscaleInputUI():
    global upscaleFactor
    return [
        html.Div(
            "upscale factor",
            className="div_text_simple",
            disable_n_clicks=True,
        ),
        dcc.Dropdown(
            upscaleFactor,
            upscaleFactor[0],
            id={"type": "input", "id": "upscaleFactor"},
            persistence_type="local",
            persistence=True,
            searchable=False,
            clearable=False,
            optionHeight=19,
            className="dcc_dropdown",
            style={"width":"50px"},
        ),
    ]

def interpolateInputUI():
    return [
        html.Div(
            "video FPS",
            className="div_text_simple",
            disable_n_clicks=True,
        ),
        dcc.Input(
            id={"type": "input", "id": "videoFPS"},
            type="number",
            value=30.0,
            min=1.0,
            max=240.0,
            persistence_type="local",
            persistence=True,
            className="dcc_input",
            style={"width":"65px"},
        ),
    ]

def previewInputUI():
    return [
        html.Div(
            "column x row",
            className="div_text_simple",
            disable_n_clicks=True,
        ),
        dbc.Stack(
            [
                dcc.Input(
                    id={"type": "input", "id": "previewCol"},
                    type="number",
                    value=3,
                    persistence_type="local",
                    persistence=True,
                    min=1,
                    max=10,
                    step=1,
                    className="dcc_input",
                    style={"width":"45px"},
                ),
                html.Button(
                    "X",
                    id={"type": "spec", "id": "button_previewSwitch"},
                    className="html_button_big",
                    style={"width":"5vh"},
                ),
                dcc.Input(
                    id={"type": "input", "id": "previewRow"},
                    type="number",
                    value=2,
                    persistence_type="local",
                    persistence=True,
                    min=1,
                    max=10,
                    step=1,
                    className="dcc_input",
                    style={"width":"45px"},
                ),
            ],
            direction="horizontal",
        ),
    ]

def getFrameResult() -> list:
    global allVideoList

    hasResult = False
    for video in allVideoList:
        if video["selected"] and "frameBytePerPacket" in video:
            hasResult = True
            break
    
    if not hasResult:
        return ["No result"]
    else:
        results = []
        for index, video in enumerate(allVideoList):
            if video["selected"] and "frameBytePerPacket" in video:
                results.append(
                    html.Button(
                        children=video["name"],
                        # use a forbidden character to avoid
                        # video name being id of another
                        id={'type':'spec_frame','id': f'{index} {video["name"]} *'},
                        className="psu_stream_button",
                    )
                )
        return results

def frameResultUI():

    return [
        html.Button(
            "REFRESH ⟳",
            id={"type": "spec", "id": "button_refreshFrame"},
            className="psu_stream_button",
            hidden=True,
        ),
        dcc.Loading(
            html.Div(
                getFrameResult(),
                id="div_frameInputUI",
                disable_n_clicks=True,
            ),
            color="white",
            overlay_style={"visibility":"visible","opacity":0.5},
        ),
        dbc.Modal(
            [
                dbc.ModalHeader(
                    dbc.ModalTitle(id="modal_frame_title"),
                    className="modal_head",
                ),
                dbc.ModalBody(
                    id="modal_frame_body",
                    className="modal_body",
                ),
                dbc.ModalFooter(
                    id="modal_frame_footer",
                    className="modal_foot",
                ),
            ],
            id="modal_frame",
            size="xl",
            scrollable=True,
            centered=True,
            is_open=False,
        ),
    ]

def getStreamInput(defaultTitle:int=0) -> list:
    """
    defaultTitle 0 | 1 | 2

    0 : ""
    1 : video["name"]
    2 : stream["title"]
    else : ""
    
    """
    global allVideoList

    hasVideo = False
    for video in allVideoList:
        if video["selected"]:
            hasVideo = True
            break
    
    if not hasVideo:
        return ["No video"]
    else:
        streamParam = []
        for index, video in enumerate(allVideoList):
            if video["selected"]:
                streamParam.append(html.Div(
                    video["name"],
                    className="div_text_simple",
                    disable_n_clicks=True,
                ))
                for stream in video["streams"]:
                    if not stream["selected"]:
                        continue

                    if defaultTitle == 0:
                        inputValue = ""
                    elif defaultTitle == 1:
                        inputValue = video["name"].replace(f'.{video["type"]}',"")
                    elif defaultTitle == 2:
                        inputValue = stream["title"]
                    else:
                        inputValue = ""
                    
                    streamParam.append(dbc.Stack(
                        [
                            dcc.Input(
                                id={"type": "input", "id": f"{index} {stream['index']} title"},
                                type="text",
                                value=inputValue,
                                placeholder=stream["title"],
                                className="psu_stream_input_title",
                            ),
                            dcc.Dropdown(
                                langDict,
                                placeholder=stream["language"],
                                optionHeight=15,
                                maxHeight=100,
                                clearable=True,
                                searchable=True,
                                className="psu_stream_dropdown_lang",
                                id={"type": "input", "id": f"{index} {stream['index']} language"},
                            ),
                            html.Div(
                                f" {str(stream['index']).rjust(2)} | {stream['codec_name']}",
                                className="psu_stream_input_txt",
                            ),
                        ],
                        direction="horizontal",
                    ))
        return streamParam

def streamInputUI():
    global allVideoList

    metaDataUI = []
    # add refresh and default button
    metaDataUI.append(dbc.Stack(
        [
            html.Button(
                "REFRESH ⟳",
                id={"type": "spec", "id": "button_refreshStream"},
                className="psu_stream_button",
                hidden=True,
            ),
            html.Button(
                children="DEFAULT TITLE",
                id={"type": "spec", "id": "button_defaultTitleStream"},
                className="psu_stream_button",
            ),
        ],
        direction="horizontal",
    ))
    # add sel/unsel all stream button
    metaDataUI.append(dbc.Stack(
        [
            html.Button(
                "VIDEO INVERT",
                id={"type": "spec", "id": "button_allVideoStream"},
                className="psu_stream_button",
            ),
            html.Button(
                "AUDIO INVERT",
                id={"type": "spec", "id": "button_allAudioStream"},
                className="psu_stream_button",
            ),
            html.Button(
                "SUB INVERT",
                id={"type": "spec", "id": "button_allSubtitleStream"},
                className="psu_stream_button",
            ),
        ],
        direction="horizontal",
    ))
    # add stream param
    metaDataUI.append(dcc.Loading(
        html.Div(
            getStreamInput(),
            id="div_streamInputUI",
            disable_n_clicks=True,
        ),
        color="white",
        overlay_style={"visibility":"visible","opacity":0.5},
    ))

    return metaDataUI

@callback(
    Output('div_processParamUI', 'children'),
    Input('dropdown_processes', 'value'),
)
def update_div_processParamUI(selectedProcess:str):

    if selectedProcess is None:
        raise PreventUpdate

    processParamUI = [
        html.H6(
            f"{selectedProcess.capitalize()} parameters :",
            disable_n_clicks=True,
            className="ch_h6_title",
        ),
    ]
    if selectedProcess == VideoProcess.compress.name:
        processParamUI.extend([
            *qualityInputUI(),
        ])
    elif selectedProcess == VideoProcess.resize.name:
        processParamUI.extend([
            *resizeInputUI(),
            *qualityInputUI(),
        ])
    elif selectedProcess == VideoProcess.upscale.name:
        processParamUI.extend([
            *upscaleInputUI(),
            *qualityInputUI(),
        ])
    elif selectedProcess == VideoProcess.interpolate.name:
        processParamUI.extend([
            *interpolateInputUI(),
            *qualityInputUI(),
        ])
    elif selectedProcess == VideoProcess.preview.name:
        processParamUI.extend([
            *previewInputUI(),
        ])
    elif selectedProcess == VideoProcess.frame.name:
        processParamUI = [
            html.H6(
                f"{selectedProcess.capitalize()} results :",
                disable_n_clicks=True,
                className="ch_h6_title",
            ),
        ]
        processParamUI.extend([
            *frameResultUI(),
        ])
    elif selectedProcess == VideoProcess.stream.name:
        processParamUI = streamInputUI()
    else:
        print(f'Not configured process : "{selectedProcess}"')
        raise PreventUpdate
    
    return processParamUI

@callback(
    Output('div_streamInputUI', 'children'),
    Input({"type": "spec", "id": "button_refreshStream"}, 'n_clicks'),
    prevent_initial_call=True,
)
def update_div_streamInputUI(clicks):

    # avoid dynamic button creation click : None/[]
    if clicks is None:
        raise PreventUpdate
    
    return getStreamInput()

@callback(
    Output('div_frameInputUI', 'children'),
    Input({"type": "spec", "id": "button_refreshFrame"}, 'n_clicks'),
    prevent_initial_call=True,
)
def update_div_FrameResultUI(clicks):

    # avoid dynamic button creation click : None/[]
    if clicks is None:
        raise PreventUpdate
    
    return getFrameResult()


def getFrameModalBody(videoIndex):
    global allVideoList

    scatterProp = {
        # "fill":"tozeroy", #slow
        "opacity":0.5,
        "mode":"lines+markers",
        "marker":{"size":3},
    }

    fig = go.Figure(
        data=[
            go.Scattergl(
                x=allVideoList[videoIndex]["frameBytePerPacket"]["pts_time"],
                y=allVideoList[videoIndex]["frameBytePerPacket"]["size"],
                name="Per Packet",
                **scatterProp,
            ),
            go.Scattergl(
                x=allVideoList[videoIndex]["frameBytePerSecond"]["pts_time"],
                y=allVideoList[videoIndex]["frameBytePerSecond"]["size"],
                name="Per Second",
                **scatterProp,
            ),
        ],
        layout={
            "hovermode":"x",
            "autosize":True,
            "margin":go.layout.Margin(t=30,b=30,r=30),
            "dragmode":"pan",
            "legend":{
                "yanchor":"top",
                "y":0.99,
                "xanchor":"left",
                "x":0.01
            },
        },
    )
    fig.update_xaxes(title_text="picture timestamp (time)")
    fig.update_xaxes(showspikes=True, spikecolor="grey", spikemode="across", spikethickness=1)

    duration = allVideoList[videoIndex]["duration"]
    if duration < timedelta(hours=1):
        fig.update_xaxes(tickformat="%M:%S.%f")
    elif duration < timedelta(days=1):
        fig.update_xaxes(tickformat="%H:%M:%S.%f")
    else:
        pass

    fig.update_yaxes(title_text="size (byte)")
    fig.update_yaxes(tickformat=",.0f")
    fig.update_layout(separators="*_.*")

    videoBitrate = allVideoList[videoIndex]["bitRate"]/8
    fig.add_hline(
        y=videoBitrate,
        line_dash="dash",
        line_color="green",
        annotation_text=f'bitrate: {videoBitrate:_.0f} byte/s',
    )
    return dcc.Graph(
        id="graph",
        figure=fig,
        className="modal_body_fig",
        config={
            "displaylogo":False,
            "scrollZoom":True,
            "modeBarButtonsToRemove":["select","zoomIn","zoomOut","resetScale","lasso2d"],
        },
    )


@callback(
    Output('modal_frame', 'is_open'),
    Output('modal_frame_title', 'children'),
    Output('modal_frame_body', 'children'),
    Output('modal_frame_footer', 'children'),
    Input({'type':'spec_frame','id': ALL}, 'n_clicks'),
    prevent_initial_call=True,
)
def openFrameModal(n_clicks):
    global allVideoList
    # avoid dynamic button creation click : None/[]
    for click in n_clicks:
        if click is not None:
            videoIndex = int(ctx.triggered_id["id"].split(" ")[0])
            videoName = allVideoList[videoIndex]["name"]
            return True, videoName, getFrameModalBody(videoIndex), ""
    
    raise PreventUpdate


@callback(
    Output({"type": "input", "id": "videoQuality"}, 'value'),
    Output({"type": "spec", "id": "dropdown_videoQuality"}, 'value'),
    Input({"type": "spec", "id": "dropdown_videoQuality"}, 'value'),
    prevent_initial_call=True,
)
def setVideoQuality(selectedVideoQuality):
    global videoQualityDict
    for videoQuality in videoQualityDict:
        if videoQuality["label"] == selectedVideoQuality:
            return videoQuality["value"], None
    raise PreventUpdate



@callback(
    Output({"type": "input", "id": "videoWidth"}, 'value'),
    Output({"type": "input", "id": "videoHeight"}, 'value'),
    Output({"type": "spec", "id": "dropdown_videoSize"}, 'value'),
    Input({"type": "spec", "id": "dropdown_videoSize"}, 'value'),
    prevent_initial_call=True,
)
def setVideoSize(selectedVideoSize):
    global videoSizesDict
    for videoSize in videoSizesDict:
        if videoSize["label"] == selectedVideoSize:
            return videoSize["width"], videoSize["height"], None
    raise PreventUpdate

@callback(
    Output({"type": "input", "id": "videoWidth"}, 'value', allow_duplicate=True),
    Output({"type": "input", "id": "videoHeight"}, 'value', allow_duplicate=True),
    Input({"type": "spec", "id": "button_sizeSwitch"}, 'n_clicks'),
    State({"type": "input", "id": "videoWidth"}, 'value'),
    State({"type": "input", "id": "videoHeight"}, 'value'),
    prevent_initial_call=True,
)
def switchVideoSize(_, width, height):
    return height, width



@callback(
    Output({"type": "input", "id": "previewCol"}, 'value'),
    Output({"type": "input", "id": "previewRow"}, 'value'),
    Input({"type": "spec", "id": "button_previewSwitch"}, 'n_clicks'),
    State({"type": "input", "id": "previewCol"}, 'value'),
    State({"type": "input", "id": "previewRow"}, 'value'),
    prevent_initial_call=True,
)
def switchPreviewColRow(_, col, row):
    return row, col



@callback(
    Output('input_path', 'disabled'),
    Output('button_editPath', 'disabled'),
    Input('button_editPath', 'n_clicks'),
    prevent_initial_call=True,
)
def editPath(_):
    return False, True

@callback(
    Output('input_path', 'value', allow_duplicate=True),
    Output('input_path', 'n_submit'),
    Input('button_selectDir', 'n_clicks'),
    running=[(Output('button_selectDir', 'disabled'), True, False)],
    prevent_initial_call=True,
)
def selectDir(_):
    window = Tk()
    window.wm_attributes('-topmost', True)
    window.withdraw()
    selectedPath = filedialog.askdirectory()
    window.destroy()
    return selectedPath, 0

@callback(
    Input('button_openDir', 'n_clicks'),
    running=[(Output('button_openDir', 'disabled'), True, False)],
    prevent_initial_call=True,
)
def openDir(_):
    global vs
    os.startfile(vs.path)

@callback(
    Output('input_path', 'disabled', allow_duplicate=True),
    Output('input_path', 'value', allow_duplicate=True),
    Output('button_editPath', 'disabled', allow_duplicate=True),
    Output('tooltip_run', 'children', allow_duplicate=True),
    Output('button_scanFiles', 'n_clicks'),
    Input('input_path', 'n_submit'),
    State('input_path', 'value'),
    running=[(Output('interval_log', 'n_intervals'), 0, 0)],
    prevent_initial_call=True,
)
def setPath(_, enteredPath):
    global vs
    if vs.setPath(enteredPath):
        return True, vs.path, False, "SCAN atleast once to RUN", 0
    else:
        raise PreventUpdate



def getVideoItem(video:VideoInfo, index:int, prefix:str=""):
    global videoItemColor
    width = str(video["width"]).rjust(6)
    height = str(video["height"]).ljust(6)
    frameRate = (str(video["fps"])+" fps").rjust(10)
    duration = str(video["duration"]).split(".")[0].rjust(8)
    bitRate = (f'{video["bitRate"]/1_000:_.0f}'+" Kbits/s").rjust(16)
    fileSize = (f'{video["fileSize"]/1_024:_.0f}'+" Ko").rjust(13)
    videoInfoText = (
        f'|{width}x{height}|'
        f'{frameRate} |'
        f'{duration} |'
        f'{bitRate} |'
        f'{fileSize} |'
    )

    streams = video["streams"]
    # sort by codec type
    streamInfo = {
        "video": {key:[] for key in StreamInfo.__annotations__.keys()},
        "audio": {key:[] for key in StreamInfo.__annotations__.keys()},
        "subtitle": {key:[] for key in StreamInfo.__annotations__.keys()},
        "other": {key:[] for key in StreamInfo.__annotations__.keys()},
    }
    for stream in streams:
        for info in StreamInfo.__annotations__.keys():
            if info in ["codec_type"]:
                continue
            try:
                streamInfo[stream["codec_type"]][info].append(stream[info])
            except:
                streamInfo["other"][info].append(stream[info])

    # generate UI for each type
    def getStreamUI(sType:str, stream:StreamInfo):

        listGroupItem = []
        for indexStream, name, sel, lang, title in zip(
            stream["index"], stream["codec_name"],
            stream["selected"], stream["language"],
            stream["title"]
        ):
            listGroupItem.append(dbc.ListGroupItem(
                f" {str(indexStream).rjust(2)} | {name}",
                id={
                    "indexVideo":index,
                    "indexStream":indexStream
                },
                action=True,
                color=videoItemColor[sel],
                className="vsu_list_group_item_stream_list_group_item",
            ))

            listGroupItem.append(dbc.Tooltip(
                [
                    html.Div(
                        f'title: {title}',
                        className="vsu_list_group_item_stream_list_group_item_tooltip",
                    ),
                    html.Div(
                        f'lang: {lang}',
                        className="vsu_list_group_item_stream_list_group_item_tooltip",
                    ),
                ],
                target={
                    "indexVideo":index,
                    "indexStream":indexStream
                },
                delay={"show": 500, "hide": 0},
            ))

        return dbc.Col([
            html.Div(
                children=sType,
                className="vsu_list_group_item_stream_name",
            ),
            dbc.ListGroup(
                children=listGroupItem,
                class_name="vsu_list_group_item_stream_list_group",
            ),
        ])
    
    streamInfoUI = []
    for sType, sValue in streamInfo.items():
        streamInfoUI.append(getStreamUI(sType, sValue))
    
    return dcc.Loading(
        dbc.Stack(
            [
                # up down button
                dbc.Stack(
                    [
                        html.Button(
                            "▲",
                            id={"type":"button_up", "index":index},
                            className="vsu_list_group_item_updown_button",
                        ),
                        html.Button(
                            "▼",
                            id={"type":"button_down", "index":index},
                            className="vsu_list_group_item_updown_button",
                        ),
                    ],
                    className="vsu_list_group_item_updown",
                ),
                # video info
                dbc.ListGroupItem(
                    children=[
                        html.H6(
                            f'{prefix}{video["name"]}',
                            className="vsu_list_group_item_video_name",
                        ),
                        html.Hr(className="vsu_list_group_item_video_hr"),
                        html.Div(
                            videoInfoText,
                            className="vsu_list_group_item_video_info",
                        ),
                        dbc.Tooltip(
                            [
                                html.Div(f'{width}x{height}',className="vsu_list_group_item_video_tooltip"),
                                html.Div(f'{frameRate}',className="vsu_list_group_item_video_tooltip"),
                                html.Div(f'{duration}',className="vsu_list_group_item_video_tooltip"),
                                html.Div(f'{bitRate}',className="vsu_list_group_item_video_tooltip"),
                                html.Div(f'{fileSize}',className="vsu_list_group_item_video_tooltip"),
                            ],
                            target={"type":"video", "index":index},
                            delay={"show": 1000, "hide": 0},
                        ),
                    ],
                    id={"type":"video", "index":index},
                    action=True,
                    color=videoItemColor[video["selected"]],
                    className="vsu_list_group_item_video",
                ),
                
                # streams info
                dbc.Stack(
                    streamInfoUI,
                    direction="horizontal",
                    className="vsu_list_group_item_stream",
                ),
            ],
            direction="horizontal",
            className="vsu_list_group_item",
        ),
        color="white",
        overlay_style={"visibility":"visible","opacity":0.5},
    )

@callback(
    Output('button_runProcess', 'disabled', allow_duplicate=True),
    Output('button_scanFiles', 'children', allow_duplicate=True),
    Output('tooltip_run', 'children', allow_duplicate=True),
    Output('list_videos', 'children', allow_duplicate=True),
    Input('button_scanFiles', 'n_clicks'),
    running=[
        (Output('list_videos', 'children'), None, None),
        (Output('interval_log', 'n_intervals'), 0, 0),

        (Output({"type": "spec", "id": "button_refreshStream"}, 'n_clicks'), 0, 0),
        (Output({"type": "spec", "id": "button_refreshFrame"}, 'n_clicks'), 0, 0),
        
        (Output({"type": "spec", "id": "button_defaultTitleStream"}, 'n_clicks'), 0, 0),
    ],
    prevent_initial_call=True,
)
def scanFiles(_):
    global vs, allVideoList
    
    if vs.getVideo():
        vs.getVideoInfo()

    # record scanned video, for selection and sort purpose
    allVideoList = vs.vList

    # add video select state
    for video in allVideoList:
        video["selected"] = True

    # generate list of video items
    videoItems = []
    for index, video in enumerate(allVideoList):
        videoItems.append(getVideoItem(video,index))

    return False, no_update, "Ready to RUN", videoItems

@callback(
    Output({'type':'video', 'index': MATCH}, 'color'),
    Input({'type':'video', 'index': MATCH}, 'n_clicks'),
    running=[
        (Output('interval_log', 'n_intervals'), 0, 0),

        (Output({"type": "spec", "id": "button_refreshStream"}, 'n_clicks'), 0, 0),
        (Output({"type": "spec", "id": "button_refreshFrame"}, 'n_clicks'), 0, 0),
    ],
    prevent_initial_call=True,
)
def switchVideoSelection(_):
    global allVideoList, videoItemColor

    # invert and record slection switch
    id = ctx.triggered_id['index']
    allVideoList[id]['selected'] = not allVideoList[id]['selected']

    selectState = allVideoList[id]['selected']
    if selectState:
        print(f"Selected {allVideoList[id]['name']}")
    else:
        print(f"Unselected {allVideoList[id]['name']}")

    return f"{videoItemColor[selectState]}"

@callback(
    Output('list_videos', 'children', allow_duplicate=True),
    Input('button_lvideo_all', 'n_clicks'),
    running=[
        (Output('interval_log', 'n_intervals'), 0, 0),
        (Input('button_lvideo_all', 'disabled'), True, False),

        (Output({"type": "spec", "id": "button_refreshStream"}, 'n_clicks'), 0, 0),
        (Output({"type": "spec", "id": "button_refreshFrame"}, 'n_clicks'), 0, 0),
    ],
    prevent_initial_call=True,
)
def videoSelectionALL(_):
    global allVideoList

    print(f'Select all video')

    for video in allVideoList:
        video["selected"] = True
    
    # generate list of video items
    videoItems = []
    for index, video in enumerate(allVideoList):
        videoItems.append(getVideoItem(video,index))

    return videoItems

@callback(
    Output('list_videos', 'children', allow_duplicate=True),
    Input('button_lvideo_none', 'n_clicks'),
    running=[
        (Output('interval_log', 'n_intervals'), 0, 0),
        (Input('button_lvideo_none', 'disabled'), True, False),

        (Output({"type": "spec", "id": "button_refreshStream"}, 'n_clicks'), 0, 0),
        (Output({"type": "spec", "id": "button_refreshFrame"}, 'n_clicks'), 0, 0),
    ],
    prevent_initial_call=True,
)
def videoSelectionNONE(_):
    global allVideoList

    print(f'Unselect all video')

    for video in allVideoList:
        video["selected"] = False
    
    # generate list of video items
    videoItems = []
    for index, video in enumerate(allVideoList):
        videoItems.append(getVideoItem(video,index))

    return videoItems

@callback(
    Output('list_videos', 'children', allow_duplicate=True),
    Input('button_lvideo_invert', 'n_clicks'),
    running=[
        (Output('interval_log', 'n_intervals'), 0, 0),
        (Input('button_lvideo_invert', 'disabled'), True, False),

        (Output({"type": "spec", "id": "button_refreshStream"}, 'n_clicks'), 0, 0),
        (Output({"type": "spec", "id": "button_refreshFrame"}, 'n_clicks'), 0, 0),
    ],
    prevent_initial_call=True,
)
def videoSelectionInvert(_):
    global allVideoList

    print(f'Invert the selection of all video')

    for video in allVideoList:
        video["selected"] = not video["selected"]
    
    # generate list of video items
    videoItems = []
    for index, video in enumerate(allVideoList):
        videoItems.append(getVideoItem(video,index))

    return videoItems

@callback(
    Output('list_videos', 'children', allow_duplicate=True),
    Input('button_lvideo_revert', 'n_clicks'),
    running=[
        (Output('interval_log', 'n_intervals'), 0, 0),
        (Output('button_lvideo_revert', 'disabled'), True, False),

        (Output({"type": "spec", "id": "button_refreshStream"}, 'n_clicks'), 0, 0),
        (Output({"type": "spec", "id": "button_refreshFrame"}, 'n_clicks'), 0, 0),
    ],
    prevent_initial_call=True,
)
def reverseVideoList(_):
    global allVideoList

    if allVideoList != []:
        allVideoList = allVideoList[::-1]

        # generate list of video items
        videoItems = []
        for index, video in enumerate(allVideoList):
            videoItems.append(getVideoItem(video,index))

        print("Reverse video list")

        return videoItems
    
    else:
        raise PreventUpdate

@callback(
    Output('list_videos', 'children', allow_duplicate=True),
    Output('dropdown_lvideo_sort', 'value'),
    Input('dropdown_lvideo_sort', 'value'),
    running=[
        (Output('interval_log', 'n_intervals'), 0, 0),
        (Output('dropdown_lvideo_sort', 'disabled'), True, False),

        (Output({"type": "spec", "id": "button_refreshStream"}, 'n_clicks'), 0, 0),
        (Output({"type": "spec", "id": "button_refreshFrame"}, 'n_clicks'), 0, 0),
    ],
    prevent_initial_call=True,
)
def sortVideoList(sortBy):
    global allVideoList, videoSortBy

    # check dropdown validity
    if sortBy not in videoSortBy:
        print("Unknow sort selection")
        raise PreventUpdate
    
    # special sort
    if sortBy == "w x h":
        for index in range(len(allVideoList)):
            allVideoList[index]["w x h"] = (
                allVideoList[index]["width"] * allVideoList[index]["height"]
            )
        allVideoList.sort(key= lambda video: video['w x h'],)
    # normal sort
    else:
        allVideoList.sort(key= lambda video: video[sortBy],)
        
    # re generate list of video items
    videoItems = []
    for index, video in enumerate(allVideoList):
        videoItems.append(getVideoItem(video,index))
    
    print(f'Sort by {sortBy}')

    return videoItems, None

@callback(
    Output('list_videos', 'children', allow_duplicate=True),
    Input('button_runProcess', 'n_clicks'),
    prevent_initial_call=True,
)
def runSetVideoListPrefix(_):
    global allVideoList
    
    videoItems = []
    count = 0
    for index, video in enumerate(allVideoList):
        if video['selected']:
            count += 1
            prefix = f'{count}. '
        else:
            prefix = ""

        videoItems.append(getVideoItem(video,index,prefix=prefix))
    
    return videoItems



@callback(
    Output('list_videos', 'children', allow_duplicate=True),
    Input({'type':'button_up', 'index': ALL}, 'n_clicks'),
    running=[
        (Output('interval_log', 'n_intervals'), 0, 0),

        (Output({"type": "spec", "id": "button_refreshStream"}, 'n_clicks'), 0, 0),
        (Output({"type": "spec", "id": "button_refreshFrame"}, 'n_clicks'), 0, 0),
    ],
    prevent_initial_call=True,
)
def moveUpVideo(clicks):
    global allVideoList

    # avoid dynamic button creation click : None/[]
    if not any(clicks):
        raise PreventUpdate

    # get triggered id
    id = ctx.triggered_id['index']

    # if can not move up
    if id == 0:
        print(f'Can not move up "{allVideoList[id]["name"]}"')
        raise PreventUpdate
    
    # do move up
    print(f'Move up "{allVideoList[id]["name"]}"')
    allVideoList[id], allVideoList[id-1] = allVideoList[id-1], allVideoList[id]

    # generate list of video items
    videoItems = []
    for index, video in enumerate(allVideoList):
        videoItems.append(getVideoItem(video,index))

    return videoItems

@callback(
    Output('list_videos', 'children', allow_duplicate=True),
    Input({'type':'button_down', 'index': ALL}, 'n_clicks'),
    running=[
        (Output('interval_log', 'n_intervals'), 0, 0),

        (Output({"type": "spec", "id": "button_refreshStream"}, 'n_clicks'), 0, 0),
        (Output({"type": "spec", "id": "button_refreshFrame"}, 'n_clicks'), 0, 0),
    ],
    prevent_initial_call=True,
)
def moveDownVideo(clicks):
    global allVideoList

    # avoid dynamic button creation click : None/[]
    if not any(clicks):
        raise PreventUpdate

    # get triggered id
    id = ctx.triggered_id['index']

    # if can not move down
    if id == (len(allVideoList)-1):
        print(f'Can not move up "{allVideoList[id]["name"]}"')
        raise PreventUpdate
    
    # do move up
    print(f'Move down "{allVideoList[id]["name"]}"')
    allVideoList[id], allVideoList[id+1] = allVideoList[id+1], allVideoList[id]

    # generate list of video items
    videoItems = []
    for index, video in enumerate(allVideoList):
        videoItems.append(getVideoItem(video,index))

    return videoItems



@callback(
    Output({'indexVideo':MATCH, 'indexStream': MATCH}, 'color'),
    Input({'indexVideo':MATCH, 'indexStream': MATCH}, 'n_clicks'),
    running=[
        (Output({"type": "spec", "id": "button_refreshStream"}, 'n_clicks'), 0, 0),
    ],
    prevent_initial_call=True,
)
def switchStreamSelection(_):
    global allVideoList, videoItemColor

    # invert and record slection switch
    indexVideo = ctx.triggered_id['indexVideo']
    indexStream = ctx.triggered_id['indexStream']
    allVideoList[indexVideo]["streams"][indexStream]["selected"] = (
        not allVideoList[indexVideo]["streams"][indexStream]["selected"]
    )
    
    selectStream = allVideoList[indexVideo]["streams"][indexStream]
    if selectStream["selected"]:
        print(f"Selected {allVideoList[indexVideo]['name']}'s stream {indexStream} : {selectStream['codec_type']}")
    else:
        print(f"Unselected {allVideoList[indexVideo]['name']}'s stream {indexStream} : {selectStream['codec_type']}")

    return f"{videoItemColor[selectStream['selected']]}"

@callback(
    Output('list_videos', 'children', allow_duplicate=True),
    Output({"type": "spec", "id": "button_refreshStream"}, 'n_clicks', allow_duplicate=True),
    Input({"type": "spec", "id": "button_allVideoStream"}, 'n_clicks'),
    running=[
        (Output({"type": "spec", "id": "button_allVideoStream"}, 'disabled'), True, False)
    ],
    prevent_initial_call=True,
)
def videoStreamInvert(clicks):
    global allVideoList

    # avoid dynamic button creation click : None/[]
    if clicks is None:
        raise PreventUpdate

    for video in allVideoList:
        for stream in video["streams"]:
            if stream["codec_type"] == "video":
                stream["selected"] = not stream["selected"]
    
    # generate list of video items
    videoItems = []
    for index, video in enumerate(allVideoList):
        videoItems.append(getVideoItem(video,index))

    return videoItems, 0

@callback(
    Output('list_videos', 'children', allow_duplicate=True),
    Output({"type": "spec", "id": "button_refreshStream"}, 'n_clicks', allow_duplicate=True),
    Input({"type": "spec", "id": "button_allAudioStream"}, 'n_clicks'),
    running=[
        (Output({"type": "spec", "id": "button_allAudioStream"}, 'disabled'), True, False)
    ],
    prevent_initial_call=True,
)
def audioStreamInvert(clicks):
    global allVideoList

    # avoid dynamic button creation click : None/[]
    if clicks is None:
        raise PreventUpdate

    for video in allVideoList:
        for stream in video["streams"]:
            if stream["codec_type"] == "audio":
                stream["selected"] = not stream["selected"]
    
    # generate list of video items
    videoItems = []
    for index, video in enumerate(allVideoList):
        videoItems.append(getVideoItem(video,index))

    return videoItems, 0

@callback(
    Output('list_videos', 'children', allow_duplicate=True),
    Output({"type": "spec", "id": "button_refreshStream"}, 'n_clicks', allow_duplicate=True),
    Input({"type": "spec", "id": "button_allSubtitleStream"}, 'n_clicks'),
    running=[
        (Output({"type": "spec", "id": "button_allSubtitleStream"}, 'disabled'), True, False)
    ],
    prevent_initial_call=True,
)
def subtitleStreamInvert(clicks):
    global allVideoList

    # avoid dynamic button creation click : None/[]
    if clicks is None:
        raise PreventUpdate

    for video in allVideoList:
        for stream in video["streams"]:
            if stream["codec_type"] == "subtitle":
                stream["selected"] = not stream["selected"]
    
    # generate list of video items
    videoItems = []
    for index, video in enumerate(allVideoList):
        videoItems.append(getVideoItem(video,index))

    return videoItems, 0

@callback(
    Output('div_streamInputUI', 'children', allow_duplicate=True),
    Output({"type": "spec", "id": "button_defaultTitleStream"}, 'children'),
    Input({"type": "spec", "id": "button_defaultTitleStream"}, 'n_clicks'),
    running=[
        (Output({"type": "spec", "id": "button_defaultTitleStream"}, 'disabled'), True, False)
    ],
    prevent_initial_call=True,
)
def setTitleToDefault(n_clicks):

    # avoid dynamic button creation click : None/[]
    if n_clicks is None:
        raise PreventUpdate
    
    # defaultTitle = 0 | 1 | 2
    return getStreamInput(defaultTitle=n_clicks%3), f"DEFAULT TITLE ({n_clicks%3})"



@callback(
    Output('button_runProcess', 'children'),
    Output({'type':'video','index': ALL}, 'children'),
    Input('button_runProcess', 'n_clicks'),
    State('dropdown_processes', 'value'),
    State({'type':'input','id': ALL}, 'value'),
    running=[
        (Output('button_stopProcess', 'disabled'), False, True),

        (Output('dropdown_processes', 'disabled'), True, False),
        (Output('dropdown_encoder', 'disabled'), True, False),
        (Output('dropdown_device', 'disabled'), True, False),

        (Output({'type':'input','id': ALL}, 'disabled'), True, False),
        (Output({'type':'spec','id': ALL}, 'disabled'), True, False),

        (Output('button_scanFiles', 'disabled'), True, False),
        (Output('input_path', 'disabled'), True, True),
        (Output('button_editPath', 'disabled'), True, False),
        (Output('button_selectDir', 'disabled'), True, False),
        (Output('button_openDir', 'disabled'), True, False),

        (Output('button_lvideo_all', 'disabled'), True, False),
        (Output('button_lvideo_none', 'disabled'), True, False),
        (Output('button_lvideo_invert', 'disabled'), True, False),
        (Output('button_lvideo_revert', 'disabled'), True, False),
        (Output('dropdown_lvideo_sort', 'disabled'), True, False),

        (Output('interval_log', 'disabled'), False, True),
        (Output('interval_log', 'n_intervals'), 0, 0),

        (Output('div_frameInputUI', 'children'), None, None),
        (Output({"type": "spec", "id": "button_refreshFrame"}, 'n_clicks'), 0, 0),
    ],
    prevent_initial_call=True,
)
def runProcess(_, selectedProcess, inputValues):
    global vs, allVideoList

    # get inputs values
    values = ctx.states_list[1]
    
    for value in values:
        if value["id"]["id"] == "videoQuality":
            videoQuality = value["value"]
        elif value["id"]["id"] == "videoWidth":
            videoWidth = value["value"]
        elif value["id"]["id"] == "videoHeight":
            videoHeight = value["value"]
        elif value["id"]["id"] == "upscaleFactor":
            upscaleFactor = value["value"]
        elif value["id"]["id"] == "videoFPS":
            videoFPS = value["value"]
        elif value["id"]["id"] == "previewCol":
            previewCol = value["value"]
        elif value["id"]["id"] == "previewRow":
            previewRow = value["value"]
        # set stream metadata for stream process
        elif len(value["id"]["id"].split(" ")) == 3:
            [vIndex, sIndex, metaData] = value["id"]["id"].split(" ")
            vIndex = int(vIndex)
            sIndex = int(sIndex)
            # set if has value
            try:
                if value["value"] != "":
                    value["value"] = value["value"].strip()
                    allVideoList[vIndex]["streams"][sIndex][metaData] = value["value"]
            except:
                pass
    
    # get selected video in order
    vs.vList = []
    for video in allVideoList:
        if video['selected']:
            vs.vList.append(video)
    
    # run process
    if selectedProcess == VideoProcess.compress.name:
        vs.compress(videoQuality)
    elif selectedProcess == VideoProcess.resize.name:
        vs.resize(videoWidth, videoHeight, videoQuality)
    elif selectedProcess == VideoProcess.upscale.name:
        vs.upscale(upscaleFactor, videoQuality)
    elif selectedProcess == VideoProcess.interpolate.name:
        vs.interpolate(videoFPS, videoQuality)
    elif selectedProcess == VideoProcess.preview.name:
        vs.preview(previewCol, previewRow)
    elif selectedProcess == VideoProcess.frame.name:
        vs.frame()
    elif selectedProcess == VideoProcess.stream.name:
        vs.stream()
    else:
        print(f'Not configured process : "{selectedProcess}"')
        raise PreventUpdate

    raise PreventUpdate

@callback(
    Input('button_stopProcess', 'n_clicks'),
    running=[(Output('button_stopProcess', 'disabled'), True, False)],
    prevent_initial_call=True,
)
def stopProcess(_):
    global vs
    vs.killProc()



class StdoutIntercept(object):
    """
    alive-progress stdout :

    'Remain to progress : 2002/3673'
    '\n'
    '\x1b[?25l'
    '\r'
    '|██████████████████▎                     |'
    ' '
    '▁▃▅'
    ' '
    '1671/3673 [45%] '
    'in 0s '
    '(~0s, 0.0/s) '
    ''
    '\r'
    '|██████████████████▎                     |'
    ' '
    '▂▄▆'
    ' '
    '1671/3673 [45%] '
    'in 0s '
    '(~0s, 0.0/s) '
    ''
    '\x1b[2K\r'
    '\x1b[J'
    'on 1673: Took : 0:00:04.991'
    '\n'
    '\x1b[2K\r'
    '\x1b[J'
    'on 1671: \x1b[31mProcess stoped\x1b[0m'
    '\n'
    '\r'
    '|██████████████████▎                     |'
    ' '
    '▂▂▄'
    ' '
    '1671/3673 [45%] '
    'in 1s '
    '(~0s, 0.0/s) '
    ''
    '\x1b[?25h'
    '\x1b[J'
    '\r'
    '|██████████████████▎⚠︎                    |'
    ' '
    '(!) 1671/3673 [45%] '
    'in 1.5s '
    '(0.00/s) '
    '\x1b[K'
    ''
    '\n'
    'SUMMARY :'
    ''
    '\n------------------------------------'

    """
    def __init__(self):
        self.stdoutW = stdout.write
        self.stderrW = stderr.write
        stdout.write = self.write
        stderr.write = self.write

        self.queueLines = ['']
        self.QUEUE_LIMIT = 512
        # min
        if self.QUEUE_LIMIT < 256:
            self.QUEUE_LIMIT = 256

        self.AP_ANSI_ESCAPE_CODE = [
            '\x1b[?25l',
            # it appears as '\x1b[2K\r' before 'on xxxx:' line
            '\x1b[2K',
            '\x1b[J',
            '\x1b[?25h',
            '\x1b[K',
        ]

    def __del__(self):
        stdout.write = self.stdoutW
        stderr.write = self.stderrW

    def write(self, msg:str):
        self.stdoutW(msg)

        # skip ANSI Escape Code
        if msg in self.AP_ANSI_ESCAPE_CODE:
            return
        
        self.queueLines[-1] += msg

        if msg == '\n':
            self.queueLines.append('')
        elif msg == '\r':
            self.queueLines[-1] = ''
        # elif ('\n' in msg) and ('\r' in msg):
        # elif '\n' in msg:
        elif '\r' in msg:
            self.queueLines[-1] = msg.split('\r')[-1]
        
        # limit queue size
        if len(self.queueLines) > self.QUEUE_LIMIT:
            # remove first 50 element
            del self.queueLines[:50]
        
stdout = StdoutIntercept()

@callback(
    Output('div_processRunning', 'children'),
    Input('interval_log', 'n_intervals'),
)
def logConsole(_):
    global stdout, colorAnsi

    # skip if no stdout
    if stdout.queueLines == ['']:
        raise PreventUpdate
    
    children = []
    queueLines = stdout.queueLines
    
    # represent queue line
    for queueLine in queueLines[::-1]:
        hasAnsiColor = False
        # check if has ansi color code
        for color, ansi in colorAnsi.items():
            if ansi in queueLine:
                hasAnsiColor = True
                # remove ansi color code
                queueLine = queueLine.replace(ansi, "")
                if color != "reset":
                    children.append(html.Span(
                        queueLine,
                        style={"color":color}
                    ))
        # no color append
        if not hasAnsiColor:
            children.append(html.Span(queueLine))

    return children



@callback(
    Output('input_path', 'value'),
    Input('interval_log', 'disabled'),
)
def loadPageRefresh(_):
    global vs
    return vs.path




if __name__ == '__main__':

    def open_browser():
        if not os.environ.get("WERKZEUG_RUN_MAIN"):
            open_new(f'http://{IP}:{PORT}/')

    Timer(1, open_browser).start()

    app.run(
        host=IP,
        port=PORT,
        debug=True,
        dev_tools_silence_routes_logging=True,
    )
    


