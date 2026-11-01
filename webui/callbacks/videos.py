import os
import subprocess
import sys
from tkinter import Tk, filedialog

from dash import ALL, MATCH, Input, Output, State, callback, ctx, dcc, html, no_update
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc

from VideoScripy import StreamInfo, VideoProcess
from .. import state
from ..state import VideoInfo, videoItemColor, videoSortBy, vs

# region video items callbacks



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
    if hasattr(os, "startfile"):
        os.startfile(vs.path)
    elif os.name == "nt":
        os.system(f'start "" "{vs.path}"')
    elif sys.platform == "darwin":
        subprocess.run(["open", vs.path], check=False)
    else:
        subprocess.run(["xdg-open", vs.path], check=False)

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
    video_data: dict[str, object] = dict(video)
    width_raw = video_data.get("width")
    height_raw = video_data.get("height")
    fps_raw = video_data.get("fps")
    duration_raw = video_data.get("duration")
    bitrate_raw = video_data.get("bitRate")
    quality_raw = video_data.get("quality")
    file_size_raw = video_data.get("fileSize")

    width = str(width_raw if width_raw is not None else "?").rjust(6)
    height = str(height_raw if height_raw is not None else "?").ljust(6)
    frameRate = (str(fps_raw if fps_raw is not None else "?")+" fps").rjust(10)
    duration = str(duration_raw if duration_raw is not None else "?").split(".")[0].rjust(8)
    bitRate = (f'{float(bitrate_raw) / 1_000:_.0f}' + " Kbits/s").rjust(16) if bitrate_raw is not None else "?".rjust(16)
    quality = str(quality_raw if quality_raw is not None else "?").rjust(5)
    fileSize = (f'{float(file_size_raw) / 1_024:_.0f}' + " Ko").rjust(13) if file_size_raw is not None else "?".rjust(13)
    videoInfoText = (
        f'|{width}x{height}|'
        f'{frameRate} |'
        f'{duration} |'
        f'{bitRate} |'
        f'{quality} Q |'
        f'{fileSize} |'
    )

    streams = video_data.get("streams") or []
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
    global vs
    if vs.getVideo():
        vs.getVideoInfo()

    # record scanned video, for selection and sort purpose
    state.allVideoList = vs.vList

    # add video select state
    for video in state.allVideoList:
        video["selected"] = True

    # generate list of video items
    videoItems = []
    for index, video in enumerate(state.allVideoList):
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
    global videoItemColor
    # invert and record slection switch
    id = ctx.triggered_id['index']
    state.allVideoList[id]['selected'] = not state.allVideoList[id]['selected']

    selectState = state.allVideoList[id]['selected']
    if selectState:
        print(f"Selected {state.allVideoList[id]['name']}")
    else:
        print(f"Unselected {state.allVideoList[id]['name']}")

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

    print(f'Select all video')

    for video in state.allVideoList:
        video["selected"] = True
    
    # generate list of video items
    videoItems = []
    for index, video in enumerate(state.allVideoList):
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

    print(f'Unselect all video')

    for video in state.allVideoList:
        video["selected"] = False
    
    # generate list of video items
    videoItems = []
    for index, video in enumerate(state.allVideoList):
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

    print(f'Invert the selection of all video')

    for video in state.allVideoList:
        video["selected"] = not video["selected"]
    
    # generate list of video items
    videoItems = []
    for index, video in enumerate(state.allVideoList):
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

    if state.allVideoList != []:
        state.allVideoList = state.allVideoList[::-1]

        # generate list of video items
        videoItems = []
        for index, video in enumerate(state.allVideoList):
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
    global videoSortBy
    # check dropdown validity
    if sortBy not in videoSortBy:
        print("Unknow sort selection")
        raise PreventUpdate
    
    # special sort
    if sortBy == "w x h":
        for index in range(len(state.allVideoList)):
            state.allVideoList[index]["w x h"] = (
                state.allVideoList[index]["width"] * state.allVideoList[index]["height"]
            )
        state.allVideoList.sort(key= lambda video: video['w x h'],)
    # normal sort
    else:
        state.allVideoList.sort(key= lambda video: video[sortBy],)
        
    # re generate list of video items
    videoItems = []
    for index, video in enumerate(state.allVideoList):
        videoItems.append(getVideoItem(video,index))
    
    print(f'Sort by {sortBy}')

    return videoItems, None

@callback(
    Output('list_videos', 'children', allow_duplicate=True),
    Input('button_runProcess', 'n_clicks'),
    prevent_initial_call=True,
)
def runSetVideoListPrefix(_):

    videoItems = []
    count = 0
    for index, video in enumerate(state.allVideoList):
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

    # avoid dynamic button creation click : None/[]
    if not any(clicks):
        raise PreventUpdate

    # get triggered id
    id = ctx.triggered_id['index']

    # if can not move up
    if id == 0:
        print(f'Can not move up "{state.allVideoList[id]["name"]}"')
        raise PreventUpdate
    
    # do move up
    print(f'Move up "{state.allVideoList[id]["name"]}"')
    state.allVideoList[id], state.allVideoList[id-1] = state.allVideoList[id-1], state.allVideoList[id]

    # generate list of video items
    videoItems = []
    for index, video in enumerate(state.allVideoList):
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

    # avoid dynamic button creation click : None/[]
    if not any(clicks):
        raise PreventUpdate

    # get triggered id
    id = ctx.triggered_id['index']

    # if can not move down
    if id == (len(state.allVideoList)-1):
        print(f'Can not move up "{state.allVideoList[id]["name"]}"')
        raise PreventUpdate
    
    # do move up
    print(f'Move down "{state.allVideoList[id]["name"]}"')
    state.allVideoList[id], state.allVideoList[id+1] = state.allVideoList[id+1], state.allVideoList[id]

    # generate list of video items
    videoItems = []
    for index, video in enumerate(state.allVideoList):
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
    global videoItemColor
    # invert and record slection switch
    indexVideo = ctx.triggered_id['indexVideo']
    indexStream = ctx.triggered_id['indexStream']
    state.allVideoList[indexVideo]["streams"][indexStream]["selected"] = (
        not state.allVideoList[indexVideo]["streams"][indexStream]["selected"]
    )
    
    selectStream = state.allVideoList[indexVideo]["streams"][indexStream]
    if selectStream["selected"]:
        print(f"Selected {state.allVideoList[indexVideo]['name']}'s stream {indexStream} : {selectStream['codec_type']}")
    else:
        print(f"Unselected {state.allVideoList[indexVideo]['name']}'s stream {indexStream} : {selectStream['codec_type']}")

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

    # avoid dynamic button creation click : None/[]
    if clicks is None:
        raise PreventUpdate

    for video in state.allVideoList:
        for stream in video["streams"]:
            if stream["codec_type"] == "video":
                stream["selected"] = not stream["selected"]
    
    # generate list of video items
    videoItems = []
    for index, video in enumerate(state.allVideoList):
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

    # avoid dynamic button creation click : None/[]
    if clicks is None:
        raise PreventUpdate

    for video in state.allVideoList:
        for stream in video["streams"]:
            if stream["codec_type"] == "audio":
                stream["selected"] = not stream["selected"]
    
    # generate list of video items
    videoItems = []
    for index, video in enumerate(state.allVideoList):
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

    # avoid dynamic button creation click : None/[]
    if clicks is None:
        raise PreventUpdate

    for video in state.allVideoList:
        for stream in video["streams"]:
            if stream["codec_type"] == "subtitle":
                stream["selected"] = not stream["selected"]
    
    # generate list of video items
    videoItems = []
    for index, video in enumerate(state.allVideoList):
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
