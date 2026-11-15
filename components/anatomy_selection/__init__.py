from pathlib import Path

import streamlit.components.v1 as components

_component = components.declare_component(
    "theia_anatomy_selection",
    path=str(Path(__file__).resolve().parent / "frontend"),
)


def anatomy_selection_component(key: str | None = None, default=None):
    return _component(key=key, default=default)
