from typing import Any

from dash import ALL, Input, Output, State, callback, ctx
from dash.exceptions import PreventUpdate

from VideoScripy import (
    GIF_DEFAULT_DITHER,
    GIF_DEFAULT_MAX_COLORS,
    VideoProcess,
)
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
    processInputs: dict[str, Any] = {}
    
    for value in values:
        inputId = value["id"]["id"]
        if inputId in {
            "videoQuality",
            "videoWidth",
            "videoHeight",
            "upscaleFactor",
            "videoFPS",
            "gifFPS",
            "gifMaxColors",
            "gifDither",
            "previewCol",
            "previewRow",
        }:
            processInputs[inputId] = value["value"]
        # set stream metadata for stream process
        elif len(inputId.split(" ")) == 3:
            [vIndex, sIndex, metaData] = inputId.split(" ")
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
        if "videoQuality" not in processInputs:
            raise PreventUpdate
        vs.compress(processInputs["videoQuality"])
    elif selectedProcess == VideoProcess.resize.name:
        if not {"videoWidth", "videoHeight", "videoQuality"} <= processInputs.keys():
            raise PreventUpdate
        vs.resize(
            processInputs["videoWidth"],
            processInputs["videoHeight"],
            processInputs["videoQuality"],
        )
    elif selectedProcess == VideoProcess.gif.name:
        if not {
            "videoWidth",
            "videoHeight",
            "gifFPS",
            "gifMaxColors",
            "gifDither",
        } <= processInputs.keys():
            raise PreventUpdate
        vs.convertToGif(
            processInputs["videoWidth"],
            processInputs["videoHeight"],
            processInputs["gifFPS"],
            processInputs["gifMaxColors"] or GIF_DEFAULT_MAX_COLORS,
            processInputs["gifDither"] or GIF_DEFAULT_DITHER,
        )
    elif selectedProcess == VideoProcess.upscale.name:
        if not {"upscaleFactor", "videoQuality"} <= processInputs.keys():
            raise PreventUpdate
        vs.upscale(processInputs["upscaleFactor"], processInputs["videoQuality"])
    elif selectedProcess == VideoProcess.interpolate.name:
        if not {"videoFPS", "videoQuality"} <= processInputs.keys():
            raise PreventUpdate
        vs.interpolate(processInputs["videoFPS"], processInputs["videoQuality"])
    elif selectedProcess == VideoProcess.preview.name:
        if not {"previewCol", "previewRow"} <= processInputs.keys():
            raise PreventUpdate
        vs.preview(processInputs["previewCol"], processInputs["previewRow"])
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
