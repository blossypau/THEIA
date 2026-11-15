from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

from config.settings import ROOT_DIR


def render_offline():
    st.subheader("Offline Mode")
    st.info("THEIA operates using local SQLite storage and local processing. No internet-dependent external services are required.")

    queue_path = ROOT_DIR / "data" / "processed" / "sync_queue.json"
    queue_path.parent.mkdir(parents=True, exist_ok=True)
    if not queue_path.exists():
        queue_path.write_text(json.dumps([], indent=2), encoding="utf-8")

    queue = json.loads(queue_path.read_text(encoding="utf-8"))
    st.write("### Synchronization queue")
    if queue:
        st.json(queue)
    else:
        st.success("Queue is empty. Local changes are ready for future sync when connectivity is available.")

    with st.form("queue_form"):
        task = st.text_input("Queue item")
        submitted = st.form_submit_button("Add to sync queue")
    if submitted and task:
        queue.append({"task": task, "status": "pending", "source": "LOCAL_DEVICE"})
        queue_path.write_text(json.dumps(queue, indent=2), encoding="utf-8")
        st.success("Queued for future synchronization.")
