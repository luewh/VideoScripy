import os
import sys
from threading import Timer
from webbrowser import open_new

from webui.app import app
from webui.state import IP, PORT, PORTABLE_MODE


if __name__ == "__main__":
    def open_browser():
        if (
            not os.environ.get("VIDEOSCRIPY_NO_BROWSER")
            and (PORTABLE_MODE or not os.environ.get("WERKZEUG_RUN_MAIN"))
        ):
            open_new(f"http://{IP}:{PORT}/")

    Timer(1, open_browser).start()

    app.run(
        host=IP,
        port=PORT,
        debug=not PORTABLE_MODE and not getattr(sys, "frozen", False),
        dev_tools_silence_routes_logging=True,
    )
