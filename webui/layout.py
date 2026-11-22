from dash import dcc, html
import dash_bootstrap_components as dbc

from .state import encoderDict, processes, videoSortBy, vs


def create_layout():
    return html.Div(
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
                                                persistence=False,
                                            ),
                                            width=5,
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
                                                value=vs.settedDevice["id"] if vs.settedDevice is not None else None,
                                                placeholder="Select a hardware ...",
                                                id="dropdown_device",
                                                maxHeight=233,
                                                optionHeight=32,
                                                searchable=True,
                                                clearable=False,
                                                className="dcc_dropdown dcc_dropdown_device",
                                                persistence_type="local",
                                                persistence=False,
                                            ),
                                            width=5,
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
                                                value=vs.videoCodec,
                                                placeholder="Select an encoder ...",
                                                id="dropdown_encoder",
                                                maxHeight=233,
                                                optionHeight=28,
                                                searchable=True,
                                                clearable=False,
                                                className="dcc_dropdown",
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
                                                "SELECT",
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
