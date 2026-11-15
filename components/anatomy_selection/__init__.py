from pathlib import Path

import streamlit.components.v1 as components

_component = components.declare_component(
    "theia_anatomy_selection",
    path=str(Path(__file__).resolve().parent / "frontend"),
)


def anatomy_selection_component(key: str | None = None, default=None, viewer_url="http://127.0.0.1:3004/"):
    return _component(key=key, default=default, viewer_url=viewer_url)
