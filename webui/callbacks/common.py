from dash import Input, Output, callback
from dash.exceptions import PreventUpdate

from ..state import IP, PORT

@callback(
    Output('button_clientClose', 'children'),
    Input('button_clientClose', 'n_clicks'),
    prevent_initial_call=True,
)
def clientClose(_):
    global IP, PORT
    text = f"Dash is running on http://{IP}:{PORT}/"
    print("-"*(len(text)+4))
    print("| "+text+" |")
    print("-"*(len(text)+4))
    raise PreventUpdate
