from datetime import timedelta

from dash import ALL, MATCH, Input, Output, State, callback, ctx, dcc, html, no_update
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import plotly.graph_objects as go

from VideoScripy import GIF_DEFAULT_DITHER, GIF_DEFAULT_MAX_COLORS, GIF_DITHERS, VideoProcess
from .. import state
from ..state import (
    StreamInfo,
    langDict,
    videoQualityDict,
    videoSizesDict,
    upscaleFactor,
    vs,
    getEncoderOptions,
)



@callback(
    Output("dropdown_encoder", "options"),
    Output("dropdown_encoder", 'value'),
    Input("dropdown_encoder", 'value'),
    Input("dropdown_device", 'value'),
    running=[(Output('interval_log', 'n_intervals'), 0, 0)],
    prevent_initial_call=True,
)
def setVideoEncoderOrDevice(encoder, device):
    if ctx.triggered_id == "dropdown_encoder":

        if encoder is None:
            raise PreventUpdate

        vs.setEncoder(encoder)

        options = getEncoderOptions(
            vs.settedDevice["id"] if vs.settedDevice is not None else None
        )
        return options, vs.videoCodec
    
    elif ctx.triggered_id == "dropdown_device":

        if device is None:
            raise PreventUpdate
        
        vs.setDevice(device)

        options = getEncoderOptions(device)
        if vs.videoCodec not in {option["value"] for option in options}:
            if not options:
                raise PreventUpdate
            vs.setEncoder(options[0]["value"])

        return options, vs.videoCodec



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

def resizeInputUI(defaultWidth=1920, defaultHeight=1080):
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
                    value=defaultWidth,
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
                    value=defaultHeight,
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

def gifInputUI():
    return [
        html.Div(
            "GIF FPS",
            className="div_text_simple",
            disable_n_clicks=True,
        ),
        dcc.Input(
            id={"type": "input", "id": "gifFPS"},
            type="number",
            value=10.0,
            min=0.1,
            max=60.0,
            step=0.1,
            persistence_type="local",
            persistence=True,
            className="dcc_input",
            style={"width":"65px"},
        ),
        html.Div(
            "colors",
            className="div_text_simple",
            disable_n_clicks=True,
        ),
        dcc.Input(
            id={"type": "input", "id": "gifMaxColors"},
            type="number",
            value=GIF_DEFAULT_MAX_COLORS,
            min=2,
            max=256,
            step=1,
            persistence_type="local",
            persistence=True,
            className="dcc_input",
            style={"width":"65px"},
        ),
        html.Div(
            "dither",
            className="div_text_simple",
            disable_n_clicks=True,
        ),
        dcc.Dropdown(
            list(GIF_DITHERS),
            GIF_DEFAULT_DITHER,
            id={"type": "input", "id": "gifDither"},
            persistence_type="local",
            persistence=True,
            searchable=False,
            clearable=False,
            optionHeight=19,
            className="dcc_dropdown",
            style={"width":"130px"},
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

    hasFrameResult = False
    for video in state.allVideoList:
        if video["selected"] and "frameBytePerPacket" in video:
            hasFrameResult = True
            break
    
    if not hasFrameResult:
        state.hasFrameResult = []
        return ["No result"]
    else:
        results = []
        state.hasFrameResult = []
        for index, video in enumerate(state.allVideoList):
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
                state.hasFrameResult.append(index)
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

    hasVideo = False
    for video in state.allVideoList:
        if video["selected"]:
            hasVideo = True
            break
    
    if not hasVideo:
        return ["No video"]
    else:
        streamParam = []
        for index, video in enumerate(state.allVideoList):
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
    elif selectedProcess == VideoProcess.gif.name:
        processParamUI.extend([
            *resizeInputUI(defaultWidth=-1, defaultHeight=-1),
            *gifInputUI(),
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

def getFrameModalFooter(videoIndex:int) -> html.Div:
    try:
        currentIndex = state.hasFrameResult.index(videoIndex)
    except ValueError:
        print("Incorrect videoIndex, not in hasFrameResult")
        return html.Div("Incorrect videoIndex, not in hasFrameResult")

    hasPrev = currentIndex > 0
    hasNext = currentIndex < len(state.hasFrameResult) - 1

    return html.Div([
        dbc.Stack(
            [
                dbc.Col(
                    html.Button(
                        state.allVideoList[state.hasFrameResult[currentIndex-1]]["name"] if hasPrev else "None", 
                        id={
                            'type':'spec_frame_nav',
                            'id': f'{state.hasFrameResult[currentIndex-1] if hasPrev else None} prev'
                        },
                        disabled=not hasPrev,
                        className="html_button_big",
                    ),
                    width=6,
                ),
                dbc.Col(
                    html.Button(
                        state.allVideoList[state.hasFrameResult[currentIndex+1]]["name"] if hasNext else "None", 
                        id={
                            'type':'spec_frame_nav',
                            'id': f'{state.hasFrameResult[currentIndex+1] if hasNext else None} next'
                        },
                        disabled=not hasNext,
                        className="html_button_big",
                    ),
                width=6,
                ),
            ],
            direction="horizontal",
        )
    ],
    className="modal_foot",
    )

def getFrameModalBody(videoIndex):

    scatterProp = {
        # "fill":"tozeroy", #slow
        "opacity":0.5,
        "mode":"lines+markers",
        "marker":{"size":3},
    }

    fig = go.Figure(
        data=[
            go.Scattergl(
                x=state.allVideoList[videoIndex]["frameBytePerPacket"]["pts_time"],
                y=state.allVideoList[videoIndex]["frameBytePerPacket"]["size"],
                name="Per Packet",
                **scatterProp,
            ),
            go.Scattergl(
                x=state.allVideoList[videoIndex]["frameBytePerSecond"]["pts_time"],
                y=state.allVideoList[videoIndex]["frameBytePerSecond"]["size"],
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

    duration = state.allVideoList[videoIndex]["duration"]
    if duration < timedelta(hours=1):
        fig.update_xaxes(tickformat="%M:%S.%f")
    elif duration < timedelta(days=1):
        fig.update_xaxes(tickformat="%H:%M:%S.%f")
    else:
        pass

    fig.update_yaxes(title_text="size (byte)")
    fig.update_yaxes(tickformat=",.0f")
    fig.update_layout(separators="*_.*")

    videoBitrate = state.allVideoList[videoIndex]["bitRate"]/8
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

    # avoid dynamic button creation click : None/[]
    for click in n_clicks:
        if click is not None:
            videoIndex = int(ctx.triggered_id["id"].split(" ")[0])
            videoName = state.allVideoList[videoIndex]["name"]
            return True, videoName, getFrameModalBody(videoIndex), getFrameModalFooter(videoIndex)
    raise PreventUpdate

@callback(
    Output('modal_frame', 'is_open', allow_duplicate=True),
    Output('modal_frame_title', 'children', allow_duplicate=True),
    Output('modal_frame_body', 'children', allow_duplicate=True),
    Output('modal_frame_footer', 'children', allow_duplicate=True),
    Input({'type':'spec_frame_nav','id': ALL}, 'n_clicks'),
    Input({'type':'spec_frame_nav','id': ALL}, 'n_clicks'),
    prevent_initial_call=True,
)
def navFrameModal(n_clicks_prev, n_clicks_next):

    # avoid dynamic button creation click : None/[]
    for click in n_clicks_prev + n_clicks_next:
        if click is not None:
            videoIndex = int(ctx.triggered_id["id"].split(" ")[0])
            prevNext = ctx.triggered_id["id"].split(" ")[1]
            if prevNext == "prev":
                videoName = state.allVideoList[videoIndex]["name"]
                return True, videoName, getFrameModalBody(videoIndex), getFrameModalFooter(videoIndex)
            elif prevNext == "next":
                videoName = state.allVideoList[videoIndex]["name"]
                return True, videoName, getFrameModalBody(videoIndex), getFrameModalFooter(videoIndex)
    
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


