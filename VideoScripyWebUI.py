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

vs = VideoScripy()
allVideoList = []

processes = [p.name for p in VideoProcess]
runningProcess = None

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
    "select":"info",
    "unselect":"dark",
}
videoSortBy = [
    "name",
    "width", "height", "w x h",
    "fps",
    "duration",
    "bitRate",
    "fileSize"
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

            # region process select UI
            dbc.Col(
                children=[

                    html.Div(
                        [

                            html.H6(
                                "Process :",
                                disable_n_clicks=True,
                                className="uni_text",
                                style={
                                    "height":"3vh",
                                    "marginBottom":"0vh",
                                }
                            ),
                            
                            dcc.Dropdown(
                                processes,
                                value=processes[0],
                                placeholder="Select a process ...",
                                id="dropdown_processes",
                                optionHeight=30,
                                searchable=False,
                                clearable=False,
                                style={
                                    "color": "black",
                                    "height":"5vh",
                                },
                            ),

                            html.Hr(
                                disable_n_clicks=True,
                                style={
                                    "marginTop":"2vh",
                                    "marginBottom":"2vh",
                                },
                            ),

                        ],
                        style={
                            "height":"12vh"
                        },
                    ),
                    
                    html.Div(
                        id="div_processParamUI",
                        disable_n_clicks=True,
                        style={
                            "width":"100%",
                            "height":"23vh",
                            "overflow-x": "hidden",
                        },
                    ),
                    
                    dbc.Stack(
                        [
                            dbc.Col(
                                dcc.Loading(
                                    html.Button(
                                        "RUN",
                                        id="button_runProcess",
                                        n_clicks=0,
                                        disabled=True,
                                        className="uni_width_height uni_text",
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
                                    className="uni_width_height uni_text",
                                ),
                            ),
                        ],
                        direction="horizontal",
                        gap=1,
                        style={
                            "height":"7vh",
                            "paddingTop":"1vh",
                            "paddingBottom":"1vh",
                        },
                    ),
                    
                    html.Div(
                        id="div_processRunning",
                        disable_n_clicks=True,
                        style={
                            "width":"100%",
                            "height":"54vh",
                            "white-space":"pre-wrap",
                            "overflow":"auto",
                            "display":"flex",
                            "flex-direction": "column-reverse",
                            "background":"black",
                            "padding":"5px",
                            "font-size":"10px",
                            "font-family":"monospace",
                            "border-radius": "3px",
                        },
                    ),
                    
                ],
                width=5,
                # md=5,
                style={
                    "paddingTop":"2vh",
                    "paddingRight":"10px",
                    "paddingBottom":"2vh",
                    "paddingLeft":"25px",
                },
                className="column_left",
            ),
            # endregion process select UI

            # region get files UI
            dbc.Col(
                children=[
                    
                    html.Div(
                        [

                            html.H6(
                                "Path :",
                                disable_n_clicks=True,
                                className="uni_text",
                                style={
                                    "height":"3vh",
                                    "marginBottom":"0vh",
                                }
                            ),

                            dbc.Stack(
                                [
                                    dbc.Col(
                                        dcc.Loading(
                                            html.Button(
                                                "SCAN",
                                                id="button_scanFiles",
                                                className="uni_width_height",
                                                style={"overflow": "clip"},
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
                                            className="uni_width_height",
                                        ),
                                        width=8,
                                    ),
                                    dbc.Col(
                                        html.Button(
                                            "EDIT",
                                            id="button_editPath",
                                            className="uni_width_height",
                                        ),
                                        width=1,
                                    ),
                                    dbc.Col(
                                        html.Button(
                                            "SELCT DIRECTORY",
                                            id="button_selectDir",
                                            className="uni_width_height uni_text",
                                        ),
                                        width=2,
                                    ),
                                ],
                                direction="horizontal",
                            ),
                            
                            html.Hr(
                                disable_n_clicks=True,
                                style={
                                    "marginTop":"2vh",
                                    "marginBottom":"2vh",
                                },
                            ),

                        ],
                        style={
                            "height":"12vh",
                        },
                    ),

                    dbc.Stack(
                        [
                            dbc.Col(
                                html.Button(
                                    "ALL",
                                    id="button_lvideo_all",
                                    className="uni_width_height",
                                    style={"overflow": "clip"},
                                ),
                                width=1
                            ),
                            dbc.Col(
                                html.Button(
                                    "NONE",
                                    id="button_lvideo_none",
                                    className="uni_width_height",
                                    style={"overflow": "clip"},
                                ),
                                width=1,
                            ),
                            dbc.Col(
                                html.Button(
                                    "↑↓",
                                    id="button_lvideo_revert",
                                    className="uni_width_height",
                                    style={"overflow": "clip"},
                                ),
                                width={"size": 1, "offset": 7},
                            ),
                            dbc.Col(
                                dcc.Dropdown(
                                    videoSortBy,
                                    placeholder="SORT",
                                    id="dropdown_lvideo_sort",
                                    searchable=False,
                                    clearable=False,
                                    style={
                                        "color": "black",
                                        "height":"5vh",
                                    },
                                ),
                                width=2,
                            ),
                        ],
                        direction="horizontal",
                        style={
                            "marginTop":"1vh",
                            "height":"5vh",
                        },

                    ),

                    dbc.ListGroup(
                        id="list_videos",
                        style={
                            "background":"rgba(0,0,0,0)",
                            "overflow-x": "hidden",
                            "overflow-y": "auto",
                            "height":"78vh",
                        },
                    ),

                ],
                width=7,
                # md=7,
                style={
                    "paddingTop":"2vh",
                    "paddingRight":"25px",
                    "paddingBottom":"2vh",
                    "paddingLeft":"10px",
                },
            )
            # endregion get files UI
        
        ],
    ),
    style={
        "overflow-x": "hidden",
    },
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
            className="uni_text",
            disable_n_clicks=True,
        ),
        dcc.Input(
            id={"type": "input", "id": "videoQuality"},
            type="number",
            value=3.0,
            min=0.1,
            max=9.9,
            step=0.1,
            persistence=True,
            className="uni_width_height",
            style={"width":"50px"},
        ),
    ]

def resizeInputUI():
    global videoSizesDict
    return [
        html.Div(
            "width x height",
            className="uni_text",
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
                    className="uni_width_height",
                    style={"width":"65px"},
                ),
                html.Button(
                    "X",
                    id={"type": "spec", "id": "button_sizeSwitch"},
                    n_clicks=0,
                    className="uni_width_height",
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
                    className="uni_width_height",
                    style={"width":"65px"},
                ),
                dcc.Dropdown(
                    [videoSizes["label"] for videoSizes in videoSizesDict],
                    placeholder="STANDAR SIZE",
                    id={"type": "spec", "id": "dropdown_videoSize"},
                    searchable=False,
                    clearable=False,
                    maxHeight=80,
                    optionHeight=20,
                    className="uni_width_height",
                    style={
                        "color": "black",
                        "height":"5vh",
                        "width":"140px",
                    },
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
            className="uni_text",
            disable_n_clicks=True,
        ),
        dcc.Dropdown(
            upscaleFactor,
            upscaleFactor[0],
            id={"type": "input", "id": "upscaleFactor"},
            persistence=True,
            searchable=False,
            clearable=False,
            optionHeight=20,
            className="uni_width_height",
            style={
                "color": "black",
                "width":"50px",
            },
        ),
    ]

def interpolateInputUI():
    return [
        html.Div(
            "video FPS",
            className="uni_text",
            disable_n_clicks=True,
        ),
        dcc.Input(
            id={"type": "input", "id": "videoFPS"},
            type="number",
            value=30.0,
            min=1.0,
            max=240.0,
            persistence=True,
            className="uni_width_height",
            style={"width":"65px"},
        ),
    ]

def mergeInputUI():
    return [
        dbc.Stack(
            [
                daq.BooleanSwitch(
                    label="All video",
                    labelPosition="top",
                    vertical=True,
                    id={"type": "input", "id": "allVideo"},
                    on=True,
                    persistence=True,
                    className="column_left",
                    style={
                        "white-space":"nowrap",
                        "width":"70px",
                    },
                ),
                daq.BooleanSwitch(
                    label="All audio",
                    labelPosition="top",
                    vertical=True,
                    id={"type": "input", "id": "allAudio"},
                    on=False,
                    persistence=True,
                    className="column_left",
                    style={
                        "white-space":"nowrap",
                        "width":"68px",
                    },
                ),
                daq.BooleanSwitch(
                    label="All subtitle",
                    labelPosition="top",
                    vertical=True,
                    id={"type": "input", "id": "allSubtitle"},
                    on=False,
                    persistence=True,
                    style={
                        "white-space":"nowrap",
                        "width":"72px",
                    },
                ),
            ],
            direction="horizontal"
        )
    ]

def previewInputUI():
    return [
        html.Div(
            "column x row",
            className="uni_text",
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
                    className="uni_width_height",
                    style={"width":"45px"},
                ),
                html.Button(
                    "X",
                    id={"type": "spec", "id": "button_sizeSwitch"},
                    disabled=True,
                    className="uni_width_height",
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
                    className="uni_width_height",
                    style={"width":"45px"},
                ),
            ],
            direction="horizontal",
        ),
    ]

@callback(
    Output('div_processParamUI', 'children'),
    Input('dropdown_processes', 'value'),
)
def update_div_processParamUI(selectedProcess:str):

    processParamUI = [
        html.H6(
            f"{selectedProcess.capitalize()} parameters :",
            disable_n_clicks=True,
            className="uni_text",
            style={
                "height":"3vh",
                "marginBottom":"0vh",
            }
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
    elif selectedProcess == VideoProcess.merge.name:
        processParamUI.extend([
            *mergeInputUI(),
        ])
    elif selectedProcess == VideoProcess.preview.name:
        processParamUI.extend([
            *previewInputUI(),
        ])
    else:
        print('Not configured process : "{}"')
        raise PreventUpdate
    
    return processParamUI



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



def getVideoItem(video:VideoInfo, index:int, color:str, prefix:str=""):

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

    return dcc.Loading(
        dbc.ListGroupItem(
            children=[
                html.H6(
                    f'{prefix}{video["name"]}',
                    className="uni_text",
                ),
                html.Hr(style={"marginTop":-15, "marginBottom":-0}),
                html.Div(
                    videoInfoText,
                    style={
                        "color":"grey",
                        "font-size":"10px",
                        "white-space":"pre",
                        "font-family":"monospace",
                    },
                ),
                dbc.Tooltip(
                    [
                        html.Div(f'{width}x{height}',className="uni_text"),
                        html.Div(f'{frameRate}',className="uni_text"),
                        html.Div(f'{duration}',className="uni_text"),
                        html.Div(f'{bitRate}',className="uni_text"),
                        html.Div(f'{fileSize}',className="uni_text"),
                    ],
                    target={"type":"video", "index":index},
                    delay={"show": 1000, "hide": 0},
                ),
            ],
            id={"type":"video", "index":index},
            action=True,
            color=color,
            style={
                "border":"1px solid black",
                "border-radius":8,
                "padding":"15px 30px 0px 30px",
            },
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
    ],
    prevent_initial_call=True,
)
def scanFiles(_):

    global vs, allVideoList, videoItemColor
    
    vs.getVideo()
    vs.getVideoInfo()

    # record scanned video, for video selection purpose
    allVideoList = vs.vList

    # generate list of video items
    videoItems = []
    for index, video in enumerate(allVideoList):
        videoItems.append(getVideoItem(video,index,videoItemColor["select"]))

    return False, no_update, "Ready to RUN", videoItems

@callback(
    Output({'type':'video', 'index': MATCH}, 'color'),
    Input({'type':'video', 'index': MATCH}, 'n_clicks'),
    State({'type':'video', 'index': MATCH}, 'color'),
    State({'type':'video', 'index': ALL}, 'color'),
    running=[(Output('interval_log', 'n_intervals'), 0, 0)],
    prevent_initial_call=True,
)
def switchVideoSelection(_, color, colorAll):
    global vs, allVideoList, videoItemColor

    id = ctx.triggered_id['index']

    # remove or add video
    vs.vList = []
    for index, video in enumerate(allVideoList):
        # clicked
        if index == id:
            if colorAll[index] == f"{videoItemColor['unselect']}":
                vs.vList.append(video)
                print(f'Select "{video["name"]}"')
            else:
                print(f'Unselect "{video["name"]}"')
        # others
        else:
            if colorAll[index] == f"{videoItemColor['select']}":
                vs.vList.append(video)

    # invert color
    if color == f"{videoItemColor['select']}":
        return f"{videoItemColor['unselect']}"
    else:
        return f"{videoItemColor['select']}"

@callback(
    Output('list_videos', 'children', allow_duplicate=True),
    Input('button_lvideo_all', 'n_clicks'),
    running=[
        (Output('interval_log', 'n_intervals'), 0, 0),
        (Input('button_lvideo_all', 'disabled'), True, False),
    ],
    prevent_initial_call=True,
)
def videoSelectionALL(_):
    global vs, allVideoList, videoItemColor

    vs.vList = allVideoList

    # generate list of video items
    videoItems = []
    for index, video in enumerate(allVideoList):
        videoItems.append(getVideoItem(video,index,videoItemColor["select"]))

    print(f'Select all video')

    return videoItems

@callback(
    Output('list_videos', 'children', allow_duplicate=True),
    Input('button_lvideo_none', 'n_clicks'),
    running=[
        (Output('interval_log', 'n_intervals'), 0, 0),
        (Input('button_lvideo_none', 'disabled'), True, False),
    ],
    prevent_initial_call=True,
)
def videoSelectionNONE(_):
    global vs, allVideoList, videoItemColor

    vs.vList = []

    # generate list of video items
    videoItems = []
    for index, video in enumerate(allVideoList):
        videoItems.append(getVideoItem(video,index,videoItemColor["unselect"]))
    
    print(f'Unselect all video')

    return videoItems

@callback(
    Output('list_videos', 'children', allow_duplicate=True),
    Input('button_lvideo_revert', 'n_clicks'),
    State('list_videos', 'children'),
    State({'type':'video', 'index': ALL}, 'color'),
    running=[
        (Output('interval_log', 'n_intervals'), 0, 0),
        (Output('button_lvideo_revert', 'disabled'), True, False)
    ],
    prevent_initial_call=True,
)
def reverseVideoList(_, listVideo, colorALL):

    global vs, allVideoList

    if listVideo is not None:
        vs.vList = vs.vList[::-1]
        allVideoList = allVideoList[::-1]
        colorALL = colorALL[::-1]

        # generate list of video items
        videoItems = []
        for index, video in enumerate(allVideoList):
            videoItems.append(getVideoItem(video,index,colorALL[index]))

        print("Reverse video list")

        return videoItems
    
    else:
        raise PreventUpdate

@callback(
    Output('list_videos', 'children', allow_duplicate=True),
    Output('dropdown_lvideo_sort', 'value'),
    Input('dropdown_lvideo_sort', 'value'),
    State({'type':'video', 'index': ALL}, 'color'),
    running=[
        (Output('interval_log', 'n_intervals'), 0, 0),
        (Output('dropdown_lvideo_sort', 'disabled'), True, False)
    ],
    prevent_initial_call=True,
)
def sortVideoList(sortBy, allColor):

    global vs, allVideoList, videoItemColor, videoSortBy

    # check dropdown validity
    if sortBy not in videoSortBy:
        print("Unknow sort selection")
        raise PreventUpdate
    
    # add color to allVideoList
    for index in range(len(allVideoList)):
        allVideoList[index]["color"] = allColor[index]
    
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
    vs.vList = []
    for index, video in enumerate(allVideoList):

        if allVideoList[index]["color"] == f"{videoItemColor['select']}":
            vs.vList.append(video)
        
        videoItems.append(getVideoItem(video,index,allVideoList[index]["color"]))
    
    print(f'Sort by {sortBy}')

    return videoItems, None

@callback(
    Output('list_videos', 'children', allow_duplicate=True),
    Input('button_runProcess', 'n_clicks'),
    State({'type':'video', 'index': ALL}, 'color'),
    prevent_initial_call=True,
)
def runSetVideoListPrefix(_, allColor):
    global allVideoList, videoItemColor
    
    videoItems = []
    count = 0
    for index, video in enumerate(allVideoList):
        if allColor[index] == videoItemColor["select"]:
            count += 1
            prefix = f'{count}. '
        else:
            prefix = ""

        videoItems.append(
            getVideoItem(
                video,
                index,
                allColor[index],
                prefix=prefix
            )
        )
    
    return videoItems



@callback(
    Output('button_runProcess', 'children'),
    Output({'type':'video','index': ALL}, 'children'),
    Input('button_runProcess', 'n_clicks'),
    State('dropdown_processes', 'value'),
    State({'type':'input','id': ALL}, 'value'),
    State({'type':'input','id': ALL}, 'on'),
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
        (Output('button_lvideo_revert', 'disabled'), True, False),
        (Output('dropdown_lvideo_sort', 'disabled'), True, False),

        (Output('interval_log', 'disabled'), False, True),
        (Output('interval_log', 'n_intervals'), 0, 0),
    ],
    prevent_initial_call=True,
)
def runProcess(_, selectedProcess, inputValues, inputOns):
    global vs
    
    values = ctx.states_list[1]
    ons = ctx.states_list[2]

    # get inputs values
    for value in values:
        if value["id"]["id"] == "videoQuality":
            videoQuality = value["value"]
        if value["id"]["id"] == "videoWidth":
            videoWidth = value["value"]
        if value["id"]["id"] == "videoHeight":
            videoHeight = value["value"]
        if value["id"]["id"] == "upscaleFactor":
            upscaleFactor = value["value"]
        if value["id"]["id"] == "videoFPS":
            videoFPS = value["value"]
        if value["id"]["id"] == "previewCol":
            previewCol = value["value"]
        if value["id"]["id"] == "previewRow":
            previewRow = value["value"]
    for on in ons:
        if on["id"]["id"] == "allVideo":
            allVideo = on["value"]
        if on["id"]["id"] == "allAudio":
            allAudio = on["value"]
        if on["id"]["id"] == "allSubtitle":
            allSubtitle = on["value"]

    # run process
    if selectedProcess == VideoProcess.optimize.name:
        vs.optimize(videoQuality)
    elif selectedProcess == VideoProcess.resize.name:
        vs.resize(videoWidth, videoHeight, videoQuality)
    elif selectedProcess == VideoProcess.upscale.name:
        vs.upscale(upscaleFactor, videoQuality)
    elif selectedProcess == VideoProcess.interpolate.name:
        vs.interpolate(videoFPS, videoQuality)
    elif selectedProcess == VideoProcess.merge.name:
        vs.merge(allVideo, allAudio, allSubtitle)
    elif selectedProcess == VideoProcess.preview.name:
        vs.preview(previewCol, previewRow)
    
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
        self.queueLimit = 1000
        self.carriage = False
        self.ansiColor = [
            "\x1b[0m", # reset
            "\x1b[31m", # red
            "\x1b[32m", # green
            "\x1b[33m", # yellow
            "\x1b[34m", # red
        ]

    def __del__(self):
        stdout.write = self.stdoutW
        stderr.write = self.stderrW

    def write(self, msg:str):
        self.stdoutW(msg)

        # remove ansi color
        for ansiColor in self.ansiColor:
            if ansiColor in msg:
                msg = msg.replace(ansiColor, "")

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
        if len(self.queue) > self.queueLimit:
            self.queue = self.queue[-self.queueLimit:]
stdout = StdoutIntercept()
@callback(
    Output('div_processRunning', 'children'),
    Input('interval_log', 'n_intervals'),
)
def logConsole(_):
    global stdout
    return ''.join(stdout.queue)


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
    


