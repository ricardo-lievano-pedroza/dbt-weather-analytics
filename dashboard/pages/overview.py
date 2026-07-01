import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from utils.db import latest_conditions, forecast_upcoming

CONDITION_ICON = {
    "Comfortable": "😊",
    "Hot": "🔥",
    "Rainy": "🌧",
    "Windy": "💨",
    "Freezing": "🥶",
    "Snowy": "❄️",
    "Mixed": "⛅",
}

SCORE_COLOR = {
    "high": "#2ecc71",
    "mid": "#f39c12",
    "low": "#e74c3c",
}

def _score_color(score):
    if score is None:
        return "#888"
    if score >= 70:
        return SCORE_COLOR["high"]
    if score >= 45:
        return SCORE_COLOR["mid"]
    return SCORE_COLOR["low"]

def _temp_color(temp):
    if temp is None:
        return "#888"
    if temp >= 32:
        return "#e74c3c"
    if temp >= 22:
        return "#f39c12"
    if temp >= 10:
        return "#2ecc71"
    return "#3498db"


def _kpi_card(city: str, row: pd.Series, forecast_df: pd.DataFrame):
    condition = row.get("condition_label", "Mixed")
    icon = CONDITION_ICON.get(condition, "⛅")
    obs_max = row.get("obs_temp_max")
    obs_min = row.get("obs_temp_min")
    obs_mean = row.get("obs_temp_mean")
    precip = row.get("obs_precip", 0) or 0
    wind = row.get("obs_wind", 0) or 0
    score = row.get("visit_score")

    with st.container(border=True):
        col_icon, col_main = st.columns([1, 3])
        with col_icon:
            st.markdown(f"<h1 style='font-size:2.5rem;margin:0'>{icon}</h1>", unsafe_allow_html=True)
        with col_main:
            st.markdown(f"**{city}**")
            if obs_max is not None:
                st.markdown(
                    f"<span style='color:{_temp_color(obs_max)};font-size:1.6rem;font-weight:700'>"
                    f"{obs_max:.1f}°C</span>",
                    unsafe_allow_html=True,
                )
            st.caption(condition)

        cols = st.columns(3)
        with cols[0]:
            if obs_max is not None and obs_min is not None:
                st.metric("High / Low", f"{obs_max:.0f}° / {obs_min:.0f}°")
        with cols[1]:
            st.metric("Precip", f"{precip:.1f} mm")
        with cols[2]:
            st.metric("Wind", f"{wind:.0f} km/h")

        if obs_mean is not None:
            st.caption(f"Feels-like avg: {obs_mean:.1f}°C")

        if pd.notna(score):
            st.progress(int(score), text=f"Visit Score: {score:.0f}/100")

        city_fcst = forecast_df[forecast_df["city_name"] == city].sort_values("date")
        if not city_fcst.empty:
            sparkline = go.Figure(
                go.Scatter(
                    x=city_fcst["date"],
                    y=city_fcst["fcst_temperature_2m_max"],
                    mode="lines",
                    line=dict(color=_temp_color(obs_max or 20), width=2),
                    fill="tozeroy",
                    fillcolor="rgba(52,152,219,0.08)",
                    name="Max °C",
                )
            )
            sparkline.update_layout(
                height=80,
                margin=dict(l=0, r=0, t=0, b=0),
                xaxis=dict(visible=False),
                yaxis=dict(visible=False, range=[
                    city_fcst["fcst_temperature_2m_min"].min() - 2,
                    city_fcst["fcst_temperature_2m_max"].max() + 2,
                ]),
                showlegend=False,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(sparkline, use_container_width=True, config={"displayModeBar": False})


def show():
    st.title("🌤 Overview — At a Glance")

    with st.spinner("Loading current conditions…"):
        lc = latest_conditions()
        fcst = forecast_upcoming()

    if lc.empty:
        st.warning("No data available. Run `dbt run` to build the mart models.")
        return

    top = lc.sort_values("visit_score", ascending=False).iloc[0]
    top_icon = CONDITION_ICON.get(top.get("condition_label", "Mixed"), "⛅")
    score = top.get("visit_score")
    reason = top.get("recommendation_reason", "")

    with st.container(border=True):
        col_a, col_b = st.columns([1, 3])
        with col_a:
            st.markdown(f"<div style='font-size:4rem;text-align:center'>{top_icon}</div>",
                        unsafe_allow_html=True)
        with col_b:
            st.markdown("### 🏆 Top Pick Right Now")
            st.markdown(
                f"<span style='font-size:1.8rem;font-weight:700'>{top['city_name']}</span>  "
                f"<span style='color:{_score_color(score)};font-size:1.2rem'>"
                f"Score {score:.0f}/100</span>" if score else f"**{top['city_name']}**",
                unsafe_allow_html=True,
            )
            st.caption(f"*{reason}*" if reason else "")

    st.divider()
    st.subheader("Current Conditions by City")
    st.caption("Cards show latest observed day · sparkline = next 7-day high temp trend")

    N_COLS = 4
    cities = list(lc.iterrows())
    for row_start in range(0, len(cities), N_COLS):
        cols = st.columns(N_COLS)
        for col, (_, row) in zip(cols, cities[row_start : row_start + N_COLS]):
            with col:
                _kpi_card(row["city_name"], row, fcst)
