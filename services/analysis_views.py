"""Reusable view models and Plotly charts, independent from Streamlit state."""
import plotly.graph_objects as go
from database.measurements import measurement_frame
from intelligence.engine import analyze


def metric_view(session, astronaut_id, metric, start=None, end=None):
    analysis = analyze(session, astronaut_id, start, end)
    return {"analysis": analysis, "history": measurement_frame(session, astronaut_id, metric, start, end),
            "baselines": [v for v in analysis["metrics"].values() if v["metric"] == metric]}


def history_figure(view):
    figure = go.Figure()
    frame = view["history"]
    for source, rows in frame.groupby("source"):
        figure.add_trace(go.Scatter(x=rows.timestamp, y=rows.value, mode="lines+markers", name=source))
    for baseline in view["baselines"]:
        figure.add_hline(y=baseline["mean"], line_dash="dot", annotation_text=f"Mean ({baseline['cohort']})")
        flags = baseline["anomalies"]
        if flags:
            figure.add_trace(go.Scatter(x=[r["timestamp"] for r in flags], y=[r["value"] for r in flags], mode="markers", name=f"Outliers ({baseline['cohort']})", marker=dict(color="#fb7185", size=12, symbol="x")))
    figure.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                         xaxis_title="UTC", yaxis_title=frame.unit.iloc[0] if not frame.empty else "Value", legend=dict(orientation="h"))
    return figure


def render_analysis(session, astronaut_id, metric, key, start=None, end=None):
    import streamlit as st
    view = metric_view(session, astronaut_id, metric, start, end)
    if view["history"].empty:
        st.info("No measurements in this period.")
        return view
    st.plotly_chart(history_figure(view), key=f"history_{key}", width="stretch")
    if view["baselines"]:
        st.dataframe([{k: v for k, v in item.items() if k in {"metric", "cohort", "samples", "unit", "mean", "median", "std", "slope_per_day", "recent_change", "status"}} for item in view["baselines"]], hide_index=True)
        for item in view["baselines"]:
            st.caption(f"{item['cohort']}: {item['status']}; {len(item['anomalies'])} statistical flags. {item['explanation']}")
    else:
        st.warning("Records exist but none pass validation for analysis.")
    st.caption(view["analysis"]["limitations"])
    return view
