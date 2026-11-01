from dash import ALL, Input, Output, State, callback, ctx
from dash.exceptions import PreventUpdate

from VideoScripy import VideoProcess
from .. import state
from ..state import vs

@callback(
    Output('button_runProcess', 'children'),
    Output({'type':'video','index': ALL}, 'children'),
    Input('button_runProcess', 'n_clicks'),
    State('dropdown_processes', 'value'),
    State({'type':'input','id': ALL}, 'value'),
    running=[
        (Output('button_runProcess', 'disabled'), True, False),
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
    if not state.process_lock.acquire(blocking=False):
        print("A video process is already running")
        raise PreventUpdate

    try:
        _runProcess(selectedProcess, inputValues)
    finally:
        state.process_lock.release()


def _runProcess(selectedProcess, inputValues):
    global vs
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
                    state.allVideoList[vIndex]["streams"][sIndex][metaData] = value["value"]
            except:
                pass
    
    # get selected video in order
    vs.vList = []
    for video in state.allVideoList:
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
