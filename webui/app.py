from pathlib import Path

from dash import Dash

from .layout import create_layout

PROJECT_ROOT = Path(__file__).resolve().parent.parent
app = Dash(
    __name__,
    assets_folder=str(PROJECT_ROOT / "assets"),
    external_stylesheets=[],
    title="VS WebUI",
    update_title="VS WebUI",
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1.0"}],
    suppress_callback_exceptions=True,
)
app.layout = create_layout()

# Import callback modules to register their callbacks with Dash.
from . import callbacks  # noqa: E402,F401
