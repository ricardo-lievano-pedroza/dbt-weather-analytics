import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from utils.db import forecast_upcoming, latest_conditions

METRICS = {
    "Avg Temp (°C)":    "fcst_temperature_2m_mean",
    "Max Temp (°C)":    "fcst_temperature_2m_max",
    "Min Temp (°C)":    "fcst_temperature_2m_min",
    "Precip (mm)":      "fcst_precipitation_sum",
    "Wind (km/h)":      "fcst_wind_speed_10m_max",
    "Visit Score":      "visit_score",
}

RADAR_NORMALIZE = {
    "Avg Temp (°C)":  (lambda v: np.clip((v + 5) / 45 * 100, 0, 100)),
    "Max Temp (°C)":  (lambda v: np.clip(v / 45 * 100, 0, 100)),
    "Min Temp (°C)":  (lambda v: np.clip((v + 10) / 50 * 100, 0, 100)),
    "Precip (mm)":    (lambda v: np.clip((1 - v / 20) * 100, 0, 100)),
    "Wind (km/h)":    (lambda v: np.clip((1 - v / 80) * 100, 0, 100)),
    "Visit Score":    (lambda v: v),
}

CITY_COLORS = px.colors.qualitative.Safe


def _heatmap(pivot: pd.DataFrame, metric_labels: list[str]) -> go.Figure:
    z = pivot.values.astype(float)
    fig = go.Figure(go.Heatmap(
        z=z,
        x=metric_labels,
        y=pivot.index.tolist(),
        colorscale="RdYlGn",
        text=np.round(z, 1),
        texttemplate="%{text}",
        hovertemplate="%{y} · %{x}: %{z:.1f}<extra></extra>",
        showscale=True,
    ))
    fig.update_layout(
        height=350,
        margin=dict(l=120, r=20, t=30, b=80),
        xaxis=dict(tickangle=-30),
    )
    return fig


def _radar(city_values: dict[str, list[float]], metric_labels: list[str]) -> go.Figure:
    fig = go.Figure()
    theta = metric_labels + [metric_labels[0]]
    for i, (city, vals) in enumerate(city_values.items()):
        r = vals + [vals[0]]
        fig.add_trace(go.Scatterpolar(
            r=r, theta=theta, fill="toself",
            name=city,
            line=dict(color=CITY_COLORS[i % len(CITY_COLORS)]),
            opacity=0.75,
        ))
    fig.update_layout(
        polar=dict(radialaxis=dict(range=[0, 100], tickfont_size=10)),
        height=420,
        legend=dict(orientation="h", yanchor="bottom", y=-0.25),
        margin=dict(l=40, r=40, t=40, b=80),
    )
    return fig


def _bar_ranking(df: pd.DataFrame, col: str, label: str) -> go.Figure:
    sdf = df.sort_values(col, ascending=True)
    fig = go.Figure(go.Bar(
        x=sdf[col], y=sdf["city_name"],
        orientation="h",
        marker_color=CITY_COLORS[:len(sdf)],
    ))
    fig.update_layout(
        title=label, height=250,
        margin=dict(l=100, r=20, t=40, b=20),
        xaxis_title=label,
    )
    return fig


def show():
    st.title("⚖ Comparison")

    with st.spinner("Loading…"):
        fcst = forecast_upcoming()
        lc   = latest_conditions()

    if fcst.empty:
        st.warning("No data found.")
        return

    cities = sorted(fcst["city_name"].unique().tolist())
    scope_opts = ["7-day average", "Today only", "Tomorrow only"]
    col1, col2 = st.columns(2)
    with col1:
        scope = st.selectbox("Scope", scope_opts)
    with col2:
        selected_cities = st.multiselect("Cities", cities, key="comparison_cities")

    if not selected_cities:
        st.info("Select at least one city.")
        return

    sub = fcst[fcst["city_name"].isin(selected_cities)].copy()
    dates = sorted(sub["date"].unique())

    if scope == "Today only" and len(dates) > 0:
        sub = sub[sub["date"] == dates[0]]
    elif scope == "Tomorrow only" and len(dates) > 1:
        sub = sub[sub["date"] == dates[1]]

    agg = (
        sub.groupby("city_name")[list(METRICS.values())]
        .mean()
        .reindex(selected_cities)
        .round(1)
    )

    st.subheader("Heatmap — all metrics at a glance")
    valid_cols = [c for c in METRICS.values() if c in agg.columns]
    valid_labels = [k for k, v in METRICS.items() if v in agg.columns]
    if valid_cols:
        fig_hm = _heatmap(agg[valid_cols], valid_labels)
        st.plotly_chart(fig_hm, use_container_width=True)

    col_left, col_right = st.columns(2)
    with col_left:
        st.subheader("Radar / Profile chart")
        radar_data = {}
        for city in selected_cities:
            if city not in agg.index:
                continue
            vals = []
            for label, col in METRICS.items():
                if col in agg.columns:
                    norm_fn = RADAR_NORMALIZE.get(label, lambda v: v)
                    raw = agg.loc[city, col]
                    vals.append(float(norm_fn(raw)) if pd.notna(raw) else 0.0)
            radar_data[city] = vals
        if radar_data:
            st.plotly_chart(_radar(radar_data, valid_labels), use_container_width=True)

    with col_right:
        st.subheader("Ranking bars")
        rank_col = st.selectbox("Rank by", valid_labels, index=min(5, len(valid_labels) - 1))
        rank_field = METRICS[rank_col]
        rank_df = agg[[rank_field]].reset_index().dropna()
        if not rank_df.empty:
            st.plotly_chart(_bar_ranking(rank_df, rank_field, rank_col), use_container_width=True)

    st.divider()
    st.subheader("Summary table")
    display = agg[valid_cols].copy()
    display.columns = valid_labels
    st.dataframe(display, use_container_width=True)
