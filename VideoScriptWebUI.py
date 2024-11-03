# dependencies
from dash import Dash, dcc, html
from dash import no_update, ctx, callback, ALL, MATCH
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import dash_daq as daq
from tkinter import Tk, filedialog

# built-in
import os
import sys
import psutil
from time import sleep
from webbrowser import open_new
from threading import Timer
from multiprocessing import Process
from threading import Thread
import subprocess

# own classes
from VideoScript import VideoScript



ip = "localhost"
port = "8848"

vs = VideoScript(__file__)
allVideoList = []

processes = ["optimize", "resize", "upscale", "interpolate", "merge"]
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
            html.Button(id="notifyClose",hidden=True),
            dcc.Interval(
                id="interval_log",
                interval=1 * 1000,
                n_intervals=0,
                disabled=True,
            ),
            # region process select UI
            dbc.Col(
                children=[
                    html.H6(
                        "Process :",
                        disable_n_clicks=True,
                        className="uni_text",
                        style={
                            "marginBottom":"5px",
                        }
                    ),
                    dcc.Dropdown(
                        processes,
                        value=processes[0],
                        placeholder="Select a process ...",
                        id="dropdown_processes",
                        searchable=False,
                        clearable=False,
                        className="uni_width_height",
                        style={
                            "color": "black"
                        },
                    ),
                    html.Hr(
                        disable_n_clicks=True,
                        style={
                            "marginTop":"20px",
                            "marginBottom":"20px",
                        }
                    ),
                    html.Div(
                        id="div_processParamUI",
                        disable_n_clicks=True,
                    ),
                    dcc.Loading(
                        html.Button(
                            "RUN",
                            id="button_runProcess",
                            n_clicks=0,
                            disabled=True,
                            className="uni_width_height uni_text",
                            style={
                                "marginTop":20,
                                "marginBottom":20,
                            },
                        ),
                        color="white",
                    ),
                    dbc.Tooltip(
                        "SCAN atleast once to RUN",
                        id="tooltip_run",
                        target="button_runProcess",
                        delay={"show": 500, "hide": 0},
                    ),
                    html.Button(
                        "STOP",
                        id="button_stopProcess",
                        n_clicks=0,
                        disabled=True,
                        className="uni_width_height uni_text",
                        style={
                            "marginBottom":20,
                        },
                    ),
                    html.Div(
                        id="div_processRunning",
                        style={
                            "width":"100%",
                            "height":"43vh",
                            "white-space":"pre-wrap",
                            "overflow":"auto",
                            "display":"flex",
                            "flex-direction": "column-reverse",
                            "background":"black",
                            "padding":"5px",
                            "font-size":"10px",
                            "font-family":"monospace",
                        },
                    ),
                ],
                width=5,
                style={"padding":"10px 15px 0px 25px"},
                className="column_left",
            ),
            # endregion process select UI

            # region get files UI
            dbc.Col(
                children=[
                    html.H6(
                        "Path :",
                        disable_n_clicks=True,
                        className="uni_text",
                        style={
                            "marginBottom":"5px",
                        }
                    ),
                    dbc.Row(
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
                        className="g-0",
                    ),
                    dbc.Tooltip(
                        "let it empty will return to default path",
                        target="input_path",
                        delay={"show": 500, "hide": 0},
                    ),
                    html.Hr(
                        disable_n_clicks=True,
                        style={
                            "marginTop":"20px",
                            "marginBottom":"20px",
                        },
                    ),
                    html.Div(
                        dbc.ListGroup(
                            id="list_videos",
                            style={
                                "background":"rgba(0,0,0,0)",
                                "height":"82vh",
                                "overflow-x": "hidden",
                                "overflow-y": "auto",
                            },
                        ),
                        disable_n_clicks=True,
                    ),
                ],
                width=7,
                style={"padding":"10px 25px 0px 15px"},
            )
            # endregion get files UI
        ],
        style={
            "height":"100vh",
            "overflow-x": "hidden",
            "overflow-y": "hidden",
        },
    ),
    style={
        "height":"100vh",
        "overflow-x": "hidden",
        "overflow-y": "hidden",
    },
    disable_n_clicks=True,
)



@callback(
    Output('interval_log', 'n_intervals', allow_duplicate=True),
    Input("notifyClose", "n_clicks"),
    prevent_initial_call=True,
)
def showURL(_):
    global ip, port
    text = f"Dash is running on http://{ip}:{port}/"
    print("-"*(len(text)+4))
    print("| "+text+" |")
    print("-"*(len(text)+4))
    return 0



def setTooltip(children:list, target:str):
    return None
    # return dbc.Tooltip(
    #         children,
    #         target=target,
    #         delay={"show": 0, "hide": 0},
    #         fade=False,
    #     )

def qualityInputUI():
    return [
        html.Div("video quality",className="uni_text"),
        dcc.Input(
            id={"type": "input", "id": "videoQuality"},
            type="number",
            value=3.0,
            min=0.1,
            max=20.0,
            step=0.1,
            persistence=True,
            className="uni_width_height",
        ),
        setTooltip(
            [
                html.Div("w * h * quality = bit rate"),
                html.Div("default=3.0"),
            ],
            target="input_videoQuality"
        )
    ]

def sizeInputUI():
    global videoSizesDict
    return [
        html.Div("width x height",className="uni_text"),
        dbc.Row(
            [
                dbc.Col(
                    dcc.Input(
                        id={"type": "input", "id": "videoWidth"},
                        type="number",
                        value=1920,
                        persistence=True,
                        min=1,
                        step=1,
                        className="uni_width_height",
                    ),
                    width=3,
                ),
                dbc.Col(
                    html.Button(
                        "X",
                        id="button_sizeSwitch",
                        n_clicks=0,
                        className="uni_width_height",
                    ),
                    width=1,
                ),
                dbc.Col(
                    dcc.Input(
                        id={"type": "input", "id": "videoHeight"},
                        type="number",
                        value=1080,
                        persistence=True,
                        min=1,
                        step=1,
                        className="uni_width_height",
                    ),
                    width=3,
                ),
                dbc.Col(
                    dcc.Dropdown(
                        [videoSizes["label"] for videoSizes in videoSizesDict],
                        value=[videoSizes["label"] for videoSizes in videoSizesDict][2],
                        id="dropdown_videoSize",
                        persistence=True,
                        searchable=False,
                        clearable=False,
                        className="uni_width_height",
                        style={
                            "color": "black",
                        },
                    ),
                    width=5,
                ),
            ],
            className="g-0",
        ),
        setTooltip(
            html.Div("switch the width and height"),
            target="button_sizeSwitch"
        ),
        setTooltip(
            html.Div("select predifined video size"),
            target="dropdown_videoSize"
        )
    ]

def upscaleInputUI():
    global upscaleFactor
    return [
        html.Div("upscale factor",className="uni_text"),
        dcc.Dropdown(
            upscaleFactor,
            upscaleFactor[0],
            id={"type": "input", "id": "upscaleFactor"},
            persistence=True,
            searchable=False,
            clearable=False,
            className="uni_width_height",
            style={
                "color": "black"
            },
        ),
        setTooltip(
            html.Div("new video size = w*factor x h*factor"),
            target="input_upscaleFactor"
        )
    ]

def interpolateInputUI():
    return [
        html.Div("video FPS",className="uni_text"),
        dcc.Input(
            id={"type": "input", "id": "videoFPS"},
            type="number",
            value=30.0,
            min=1.0,
            max=240.0,
            persistence=True,
            className="uni_width_height",
        ),
    ]

def mergeInputUI():
    return [dbc.Row([
        dbc.Col(
            daq.BooleanSwitch(
                label="All video",
                labelPosition="top",
                vertical=True,
                id={"type": "input", "id": "allVideo"},
                on=True,
                persistence=True,
                style={"white-space":"nowrap"},
            )
        ),
        dbc.Col(
            daq.BooleanSwitch(
                label="All audio",
                labelPosition="top",
                vertical=True,
                id={"type": "input", "id": "allAudio"},
                on=False,
                persistence=True,
                style={"white-space":"nowrap"},
            )
        ),
        dbc.Col(
            daq.BooleanSwitch(
                label="All subtitle",
                labelPosition="top",
                vertical=True,
                id={"type": "input", "id": "allSubtitle"},
                on=False,
                persistence=True,
                style={"white-space":"nowrap"},
            )
        ),
    ])]

@callback(
    Output('div_processParamUI', 'children'),
    Input('dropdown_processes', 'value'),
)
def update_div_processParamUI(selectedProcess):
    if selectedProcess == "optimize":
        return [
            html.H6(
                "Optimize parameters :",
                className="uni_text",
            ),
            *qualityInputUI(),
        ]
    elif selectedProcess == "resize":
        return [
            html.H6(
                "Resize parameters :",
                className="uni_text",
            ),
            *sizeInputUI(),
            *qualityInputUI(),
        ]
    elif selectedProcess == "upscale":
        return [
            html.H6(
                "Upscale parameters :",
                className="uni_text",
            ),
            *upscaleInputUI(),
            *qualityInputUI(),
        ]
    elif selectedProcess == "interpolate":
        return [
            html.H6(
                "Interpolate parameters :",
                className="uni_text",
            ),
            *interpolateInputUI(),
            *qualityInputUI(),
        ]
    elif selectedProcess == "merge":
        return [
            html.H6(
                "Merge parameters :",
                className="uni_text",
            ),
            *mergeInputUI(),
        ]
    else:
        raise PreventUpdate



@callback(
    Output({"type": "input", "id": "videoWidth"}, 'value'),
    Output({"type": "input", "id": "videoHeight"}, 'value'),
    Input('dropdown_videoSize', 'value'),
    prevent_initial_call=True,
)
def setVideoSize(selectedVideoSize):
    global videoSizesDict
    for videoSize in videoSizesDict:
        if videoSize["label"] == selectedVideoSize:
            return videoSize["width"], videoSize["height"]
    raise PreventUpdate

@callback(
    Output({"type": "input", "id": "videoWidth"}, 'value', allow_duplicate=True),
    Output({"type": "input", "id": "videoHeight"}, 'value', allow_duplicate=True),
    Input('button_sizeSwitch', 'n_clicks'),
    State({"type": "input", "id": "videoWidth"}, 'value'),
    State({"type": "input", "id": "videoHeight"}, 'value'),
    prevent_initial_call=True,
)
def switchVideoSize(_, width, height):
    return height, width



@callback(
    Output('input_path', 'disabled'),
    Output('input_path', 'n_submit', allow_duplicate=True),
    Input('button_editPath', 'n_clicks'),
    prevent_initial_call=True,
)
def editPath(n_clicks):
    if n_clicks%2 == 0:
        return True, 0
    else:
        return False, no_update

@callback(
    Output('input_path', 'value'),
    Output('input_path', 'n_submit'),
    Input('button_selectDir', 'n_clicks'),
    running=[Output('button_selectDir', 'disabled'), True, False],
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
    Output('button_runProcess', 'disabled'),
    Output('tooltip_run', 'children'),
    Output('button_editPath', 'n_clicks'),
    Output('interval_log', 'n_intervals', allow_duplicate=True),
    Input('input_path', 'n_submit'),
    State('input_path', 'value'),
    prevent_initial_call=True,
)
def setPath(_, enteredPath):
    global vs, dashLoggerHandler
    if vs.setPath(enteredPath):
        return True, vs.path, True, "SCAN atleast once to RUN", 0, 0
    else:
        return False, no_update, True, "SCAN atleast once to RUN", 0, 0



def getVideoItem(video:dict, index:int):

    width = str(video["width"]).rjust(7)
    height = str(video["height"]).ljust(7)
    frameRate = (str(video["r_frame_rate"])+" fps").rjust(10)
    duration = str(video["duration"]).split(".")[0].rjust(10)
    bitRate = (f'{video["bitRate"]/1_000:_.0f}'+" Kbits/s").rjust(16)
    videoInfoText = (
        f'|{width}x{height}|'+
        f'{frameRate}  |'+
        f'{duration}  |'+
        f'{bitRate}  |'
    )

    return dcc.Loading(
        dbc.ListGroupItem(
            children=[
                html.H6(
                    f'{index+1}. {video["name"]}',
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
            ],
            id={"type":"video", "index":index},
            action=True,
            color="info",
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
    Output('interval_log', 'n_intervals', allow_duplicate=True),
    Output('list_videos', 'children'),
    Input('button_scanFiles', 'n_clicks'),
    prevent_initial_call=True,
)
def scanFiles(_):

    global vs, allVideoList
    
    vs.getVideo()
    vs.getVideoInfo()

    # record scanned video, for video selection purpose
    allVideoList = vs.vList

    # generate list of video items
    videoItems = []
    for index, video in enumerate(vs.vList):
        videoItems.append(getVideoItem(video,index))

    return False, no_update, "Ready to RUN", 0, videoItems

@callback(
    Output({'type':'video', 'index': MATCH}, 'color'),
    Input({'type':'video', 'index': MATCH}, 'n_clicks'),
    State({'type':'video', 'index': MATCH}, 'color'),
    State({'type':'video', 'index': ALL}, 'color'),
    prevent_initial_call=True,
)
def switchVideoColor(_, color, colorAll):
    global vs, allVideoList

    id = ctx.triggered_id['index']

    vs.vList = []
    for index, video in enumerate(allVideoList):
        if index == id:
            if colorAll[index] == "dark":
                vs.vList.append(video)
        else:
            if colorAll[index] == "info":
                vs.vList.append(video)

    if color == "info":
        return "dark"
    else:
        return "info"



@callback(
    Output('button_runProcess', 'children'),
    Output({'type':'video','index': ALL}, 'children'),
    Input('button_runProcess', 'n_clicks'),
    State('dropdown_processes', 'value'),
    State({'type':'input','id': ALL}, 'value'),
    State({'type':'input','id': ALL}, 'on'),
    running=[
        (Output('button_stopProcess', 'disabled'), False, True),
        (Output('button_scanFiles', 'disabled'), True, False),
        (Output('button_editPath', 'disabled'), True, False),
        (Output('button_selectDir', 'disabled'), True, False),
        (Output('input_path', 'disabled'), True, True),
        (Output('interval_log', 'disabled'), False, True),
        (Output('interval_log', 'n_intervals'), 0, 0),
    ],
    prevent_initial_call=True,
)
def runProcess(_, selectedProcess, inputValues, inputOns):
    global vs, runningProcess

    if selectedProcess == "optimize":
        vs.optimize(*inputValues)
        # runningProcess = Process(target=vs.optimize, args=(inputValues))
        
    elif selectedProcess == "resize":
        vs.resize(*inputValues)
        # runningProcess = Process(target=vs.resize, args=(inputValues))

    elif selectedProcess == "upscale":
        vs.upscale(*inputValues)
        # runningProcess = Process(target=vs.upscale, args=(inputValues))

    elif selectedProcess == "interpolate":
        vs.interpolate(*inputValues)
        # runningProcess = Process(target=vs.interpolate, args=(inputValues))

    elif selectedProcess == "merge":
        vs.merge(*inputOns)
        # runningProcess = Process(target=vs.merge, args=(inputOns))
    
    # runningProcess.start()
    # runningProcess.join()
    print(f"Process {selectedProcess} END")
    raise PreventUpdate

@callback(
    Input('button_stopProcess', 'n_clicks'),
    running=[(Output('button_stopProcess', 'disabled'), True, False)],
    prevent_initial_call=True,
)
def stopProcess(_):
    # global runningProcess
    # parent = psutil.Process(runningProcess.pid)
    # for child in parent.children(recursive=True):
    #     print(child)
    #     child.kill()
    # parent.kill()

    # vs.stopProcess()

    # pid = os.getpid()
    # proc = psutil.Process(pid)
    # children = proc.children(recursive=True)
    # print("pid :", pid)
    # print("proc :", proc)
    # print("children :", children)
    # for child in children:
    #     try:
    #         child.kill()
    #         print(f"Killed {child}")
    #     except:
    #         print(f"Can not kill {child}")
    #         pass
    # # proc.kill()

    # print("Stopped")
    print("Currently not supported")



class StdoutIntercept(object):
    def __init__(self):
        self.stdoutW = sys.stdout.write
        self.stderrW = sys.stderr.write
        sys.stdout.write = self.write
        sys.stderr.write = self.write
        self.queue = []
        self.carriage = False

    def __del__(self):
        sys.stdout.write = self.stdoutW
        sys.stderr.write = self.stderrW

    def write(self, msg):
        self.stdoutW(msg)

        if msg == "\r":
            # init carriage line
            if not self.carriage:
                # alive-progress remove ANSI Escape Code (hide the cursor on terminal)
                if "\x1b" in self.queue[-1]:
                    self.queue[-1] = self.queue[-1].replace("\x1b", "")
                else:
                    self.queue.append("")
            # rewrite carriage line
            else:
                self.queue[-1] = ""
            
            self.carriage = True
            return
        
        # stop carriage
        if msg == "\n":
            self.carriage = False
            # alive-progress remove ANSI clears line from cursor
            if "\x1b[K" in self.queue[-1]:
                self.queue[-1] = self.queue[-1].replace("\x1b[K", "")

        # append carriage line
        if self.carriage:
            self.queue[-1] += msg
        # append line
        else:
            self.queue.append(msg)

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
        debug=False,
        dev_tools_silence_routes_logging=True,
    )
    


