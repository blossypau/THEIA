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
            figure.add_trace(go.Scatter(x=[r["timestamp"] for r in flags], y=[r["value"] for r in flags], mode="markers", name=f"Outliers ({baseline['cohort']})", marker=dict(color="#F4B860", size=10, symbol="x")))
    figure.update_traces(line=dict(width=2),selector=dict(type='scatter',mode='lines+markers'))
    figure.update_layout(colorway=['#45E0F5','#9C78FF','#38D9A9','#438BFF'], height=330, margin=dict(l=15,r=15,t=55,b=45), font=dict(family='sans-serif',color='#9eb5c8',size=11), hovermode='x unified', clickmode='event+select', template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                         xaxis_title="UTC", yaxis_title=frame.unit.iloc[0] if not frame.empty else "Value", legend=dict(orientation="h",x=0,y=1.12,xanchor="left",yanchor="bottom",font=dict(size=10)))
    figure.update_xaxes(showgrid=False,zeroline=False,automargin=True)
    figure.update_yaxes(automargin=True,gridcolor="rgba(96,166,201,.12)",zeroline=False)
    return figure


def render_analysis(session, astronaut_id, metric, key, start=None, end=None):
    import streamlit as st
    view = metric_view(session, astronaut_id, metric, start, end)
    if view["history"].empty:
        st.info("No measurements in this period.")
        return view
    selection = st.plotly_chart(history_figure(view), key=f"history_{key}", width="stretch", on_select="rerun", selection_mode=("points","box","lasso"))
    if selection.selection.points:
        st.caption(f"{len(selection.selection.points)} chart points selected. Selection changes the inspection view only.")
        st.dataframe([{'timestamp':point.get('x'),'value':point.get('y')} for point in selection.selection.points],hide_index=True)
    if view["baselines"]:
        st.dataframe([{k: v for k, v in item.items() if k in {"metric", "cohort", "samples", "unit", "mean", "median", "std", "slope_per_day", "recent_change", "status"}} for item in view["baselines"]], hide_index=True)
        for item in view["baselines"]:
            st.caption(f"{item['cohort']}: {item['status']}; {len(item['anomalies'])} statistical flags. {item['explanation']}")
    else:
        st.warning("Records exist but none pass validation for analysis.")
    st.caption(view["analysis"]["limitations"])
    return view
