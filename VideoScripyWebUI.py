# built-in
import os
from sys import stdout, stderr
from time import sleep
from webbrowser import open_new
from threading import Timer

# dependencies
from dash import Dash, dcc, html
from dash import no_update, ctx, callback, ALL, MATCH
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import dash_daq as daq
from tkinter import Tk, filedialog

# own class
from VideoScripy import *


addPath = []
addPath.append("./tools/ffmpeg-full_build/bin")
addPath.append("./tools/Real-ESRGAN")
addPath.append("./tools/Ifrnet")
for index, path in enumerate(addPath):
    addPath[index] = os.path.abspath(path)
os.environ["PATH"] += os.pathsep.join(addPath)

ip = "localhost"
port = "8848"

# extend VideoInfo
class VideoInfo(VideoInfo):
    selected: bool

vs = VideoScripy()
allVideoList:list[VideoInfo] = []
processes = [p.name for p in VideoProcess]
videoSizesDict = [
    # {"label":"240p/SD", "width":426, "height":240},
    # {"label":"360p/SD", "width":640, "height":360},
    {"label":"480p/SD", "width":854, "height":480},
    {"label":"720p/HD", "width":1280, "height":720},
    {"label":"1080p/FHD", "width":1920, "height":1080},
    {"label":"1440p/2K", "width":2560, "height":1440},
    {"label":"2160p/4K", "width":3840, "height":2160},
    {"label":"4320p/8K", "width":7680, "height":4320},
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
                interval=0.5 * 1000,
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
                            dcc.Dropdown(
                                processes,
                                value=processes[-1],
                                placeholder="Select a process ...",
                                id="dropdown_processes",
                                maxHeight=233,
                                optionHeight=28,
                                searchable=True,
                                clearable=False,
                                className="dcc_dropdown",
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
                                            "SELCT DIRECTORY",
                                            id="button_selectDir",
                                            className="html_button_big",
                                        ),
                                        width=2,
                                    ),
                                ],
                                direction="horizontal",
                            ),
                            html.Hr(className="ch_hr"),
                        ],
                        className="ch_div_header"
                    ),
                    # select & sort button
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
                        className="vsu_list_group"
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
    global ip, port
    text = f"Dash is running on http://{ip}:{port}/"
    print("-"*(len(text)+4))
    print("| "+text+" |")
    print("-"*(len(text)+4))
    raise PreventUpdate



def qualityInputUI():
    return [
        html.Div(
            "video quality",
            # className="div_text_simple",
        ),
        dcc.Input(
            id={"type": "input", "id": "videoQuality"},
            type="number",
            value=3.0,
            min=0.1,
            max=9.9,
            step=0.1,
            persistence=True,
            className="dcc_input",
            style={"width":"50px"},
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
                    maxHeight=120,
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

def getStreamParam(defaultTitle=False):
    global allVideoList

    if allVideoList == []:
        return "No video"
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
                    streamParam.append(dbc.Stack(
                        [
                            dcc.Input(
                                id={"type": "input", "id": f"{index} {stream['index']} title"},
                                type="text",
                                value=video["name"] if defaultTitle else "",
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
    # add refresh button
    metaDataUI.append(dbc.Stack(
        [
            html.Button(
                "REFRESH ⟳",
                id={"type": "spec", "id": "button_refreshStream"},
                className="psu_stream_button",
            ),
            html.Button(
                "DEFAULT TITLE",
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
            getStreamParam(),
            id="div_streamParamUI",
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

    processParamUI = [
        html.H6(
            f"{selectedProcess.capitalize()} parameters :",
            disable_n_clicks=True,
            className="ch_h6_title",
        ),
    ]
    if selectedProcess == VideoProcess.optimize.name:
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
    elif selectedProcess == VideoProcess.stream.name:
        processParamUI = streamInputUI()
    else:
        print(f'Not configured process : "{selectedProcess}"')
        raise PreventUpdate
    
    return processParamUI

@callback(
    Output('div_streamParamUI', 'children'),
    Input({"type": "spec", "id": "button_refreshStream"}, 'n_clicks'),
    prevent_initial_call=True,
)
def update_div_streamParamUI(_):
    return getStreamParam()



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
    Output('input_path', 'value'),
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
                className="ssu_list_group_item",
            ))

            listGroupItem.append(dbc.Tooltip(
                [
                    html.Div(
                        f'title: {title}',
                        className="ssu_list_group_item_tooltip",
                    ),
                    html.Div(
                        f'lang: {lang}',
                        className="ssu_list_group_item_tooltip",
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
                className="ssu_list_group_name",
            ),
            dbc.ListGroup(
                children=listGroupItem,
                class_name="ssu_list_group",
            ),
        ])
    
    streamInfoUI = []
    for sType, sValue in streamInfo.items():
        streamInfoUI.append(getStreamUI(sType, sValue))
    
    return dcc.Loading(
        dbc.Stack(
            [
                # video info
                dbc.Col(
                    dbc.ListGroupItem(
                        children=[
                            html.H6(
                                f'{prefix}{video["name"]}',
                                className="vsu_list_group_item_name",
                            ),
                            html.Hr(className="vsu_list_group_item_hr"),
                            html.Div(
                                videoInfoText,
                                className="vsu_list_group_item_info",
                            ),
                            dbc.Tooltip(
                                [
                                    html.Div(f'{width}x{height}',className="vsu_list_group_item_tooltip"),
                                    html.Div(f'{frameRate}',className="vsu_list_group_item_tooltip"),
                                    html.Div(f'{duration}',className="vsu_list_group_item_tooltip"),
                                    html.Div(f'{bitRate}',className="vsu_list_group_item_tooltip"),
                                    html.Div(f'{fileSize}',className="vsu_list_group_item_tooltip"),
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
                    width=7,
                    className="vsu_list_group_item_video",
                ),
                
                # streams info
                dbc.Col(
                    dbc.Stack(
                        streamInfoUI,
                        direction="horizontal",
                    ),
                    width=5,
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
    Output('list_videos', 'children'),
    Input('button_scanFiles', 'n_clicks'),
    running=[
        (Output('list_videos', 'children'), None, None),
        (Output('interval_log', 'n_intervals'), 0, 0),

        (Output({"type": "spec", "id": "button_refreshStream"}, 'n_clicks'), 0, 0),
    ],
    prevent_initial_call=True,
)
def scanFiles(_):
    global vs, allVideoList
    
    vs.getVideo()
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
def videoStreamInvert(_):
    global allVideoList

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
def audioStreamInvert(_):
    global allVideoList

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
def subtitleStreamInvert(_):
    global allVideoList

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
    Output('div_streamParamUI', 'children', allow_duplicate=True),
    Input({"type": "spec", "id": "button_defaultTitleStream"}, 'n_clicks'),
    running=[
        (Output({"type": "spec", "id": "button_defaultTitleStream"}, 'disabled'), True, False)
    ],
    prevent_initial_call=True,
)
def setTitleToDefault(n_clicks):
    if n_clicks%2 != 0:
        return getStreamParam(defaultTitle=True)
    else:
        return getStreamParam(defaultTitle=False)



@callback(
    Output('button_runProcess', 'children'),
    Output({'type':'video','index': ALL}, 'children'),
    Input('button_runProcess', 'n_clicks'),
    State('dropdown_processes', 'value'),
    State({'type':'input','id': ALL}, 'value'),
    running=[
        (Output('button_stopProcess', 'disabled'), False, True),

        (Output('dropdown_processes', 'disabled'), True, False),

        (Output({'type':'input','id': ALL}, 'disabled'), True, False),
        (Output({'type':'spec','id': ALL}, 'disabled'), True, False),

        (Output('button_scanFiles', 'disabled'), True, False),
        (Output('button_editPath', 'disabled'), True, False),
        (Output('button_selectDir', 'disabled'), True, False),
        (Output('input_path', 'disabled'), True, True),

        (Output('button_lvideo_all', 'disabled'), True, False),
        (Output('button_lvideo_none', 'disabled'), True, False),
        (Output('button_lvideo_invert', 'disabled'), True, False),
        (Output('button_lvideo_revert', 'disabled'), True, False),
        (Output('dropdown_lvideo_sort', 'disabled'), True, False),

        (Output('interval_log', 'disabled'), False, True),
        (Output('interval_log', 'n_intervals'), 0, 0),
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
                allVideoList[vIndex]["streams"][sIndex][metaData] = value["value"]
            except:
                pass
    
    # get selected video in order
    vs.vList = []
    for video in allVideoList:
        if video['selected']:
            vs.vList.append(video)
    
    # run process
    if selectedProcess == VideoProcess.optimize.name:
        vs.optimize(videoQuality)
    elif selectedProcess == VideoProcess.resize.name:
        vs.resize(videoWidth, videoHeight, videoQuality)
    elif selectedProcess == VideoProcess.upscale.name:
        vs.upscale(upscaleFactor, videoQuality)
    elif selectedProcess == VideoProcess.interpolate.name:
        vs.interpolate(videoFPS, videoQuality)
    elif selectedProcess == VideoProcess.preview.name:
        vs.preview(previewCol, previewRow)
    elif selectedProcess == VideoProcess.stream.name:
        vs.stream()
    else:
        print(f'Not configured process : "{selectedProcess}"')
        raise PreventUpdate

    if vs.killed:
        print(f"Process {selectedProcess} STOP")
    else:
        print(f"Process {selectedProcess} END")

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
    def __init__(self):
        self.stdoutW = stdout.write
        self.stderrW = stderr.write
        stdout.write = self.write
        stderr.write = self.write
        self.queue = []
        self.QUEUE_LIMIT = 1000
        self.carriage = False

    def __del__(self):
        stdout.write = self.stdoutW
        stderr.write = self.stderrW

    def write(self, msg:str):
        self.stdoutW(msg)
        
        if "\x1b[2K\x1b[J" in msg:
            msg.replace("\x1b[2K\x1b[J", "")

        if msg == "\r":
            # init carriage line
            if not self.carriage:
                # alive-progress remove ANSI Escape Code (hide the cursor on terminal)
                if "\x1b[?25l" in self.queue[-1]:
                    self.queue[-1] = self.queue[-1].replace("\x1b[?25l", "")
                if "\x1b[?25h" in self.queue[-1]:
                    self.queue[-1] = self.queue[-1].replace("\x1b[?25h", "")
                else:
                    self.queue.append("")
            # rewrite carriage line
            else:
                self.queue[-1] = ""
            
            self.carriage = True
            return
        
        if msg == "\n":
            # stop carriage
            if self.carriage:
                self.carriage = False
                # alive-progress remove ANSI clears line from cursor
                if "\x1b[K" in self.queue[-1]:
                    self.queue[-1] = self.queue[-1].replace("\x1b[K", "")

        # append carriage line
        if self.carriage:
            # for print during bar progress
            if "on " in msg:
                self.queue[-1] = msg
            else:
                if "\x1b[\x1b[J" in msg:
                    msg.replace("\x1b[\x1b[J", "")
                self.queue[-1] += msg
        # append line
        else:
            self.queue.append(msg)
        
        # limit queue size
        if len(self.queue) > self.QUEUE_LIMIT:
            self.queue = self.queue[-self.QUEUE_LIMIT:]
stdout = StdoutIntercept()
@callback(
    Output('div_processRunning', 'children'),
    Input('interval_log', 'n_intervals'),
)
def logConsole(_):
    global stdout, colorAnsi

    # skip if not stdout
    if stdout.queue == []:
        raise PreventUpdate
    
    msgs = ''.join(stdout.queue).split("\n")
    children = []
    for msg in msgs[::-1]:
        hasAnsiColor = False
        # check if has ansi color code
        for color, ansi in colorAnsi.items():
            if ansi in msg:
                hasAnsiColor = True
                # remove ansi color code
                msg = msg.replace(ansi, "")
                if color != "reset":
                    children.append(html.Span(
                        msg,
                        style={"color":color}
                    ))
        # no color append
        if not hasAnsiColor:
            children.append(html.Span(msg))

    return children



if __name__ == '__main__':

    def open_browser():
        if not os.environ.get("WERKZEUG_RUN_MAIN"):
            open_new(f'http://{ip}:{port}/')

    Timer(1, open_browser).start()

    app.run(
        host=ip,
        port=port,
        debug=True,
        dev_tools_silence_routes_logging=True,
    )
    


