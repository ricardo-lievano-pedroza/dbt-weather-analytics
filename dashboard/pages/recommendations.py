import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from utils.db import forecast_upcoming, latest_conditions

CITY_COLORS = px.colors.qualitative.Safe

PRESETS = {
    "Custom":         None,
    "☀️ Beach Day":   dict(w_temp=0.50, w_rain=0.30, w_wind=0.20),
    "🥾 Hiking":      dict(w_temp=0.40, w_rain=0.35, w_wind=0.25),
    "🏙 City Walk":   dict(w_temp=0.35, w_rain=0.45, w_wind=0.20),
    "⛷ Skiing":       dict(w_temp=0.20, w_rain=0.45, w_wind=0.35),
}

SCORE_MEDAL = ["🥇", "🥈", "🥉"]


def _recompute_score(df: pd.DataFrame, w_temp: float, w_rain: float, w_wind: float) -> pd.Series:
    total = w_temp + w_rain + w_wind
    w_temp, w_rain, w_wind = w_temp / total, w_rain / total, w_wind / total
    return (
        w_temp * df["temp_comfort_score"].fillna(50)
        + w_rain * df["rain_score"].fillna(50)
        + w_wind * df["wind_score"].fillna(50)
    ).round(1)


def _leaderboard(ranked: pd.DataFrame) -> None:
    for i, (_, row) in enumerate(ranked.iterrows()):
        medal = SCORE_MEDAL[i] if i < 3 else f"#{i + 1}"
        score = row["composite_score"]
        bar_color = "#2ecc71" if score >= 70 else "#f39c12" if score >= 45 else "#e74c3c"
        cols = st.columns([1, 4, 3])
        with cols[0]:
            st.markdown(f"<div style='font-size:1.5rem;text-align:center'>{medal}</div>",
                        unsafe_allow_html=True)
        with cols[1]:
            st.markdown(f"**{row['city_name']}**  \n"
                        f"<small>{row.get('condition_label', '')}</small>",
                        unsafe_allow_html=True)
        with cols[2]:
            st.markdown(
                f"<div style='background:{bar_color};border-radius:4px;"
                f"padding:4px 10px;color:white;text-align:center;font-weight:700'>"
                f"{score:.0f} / 100</div>",
                unsafe_allow_html=True,
            )


def _score_breakdown(ranked: pd.DataFrame, w_temp: float, w_rain: float, w_wind: float) -> go.Figure:
    fig = go.Figure()
    total = w_temp + w_rain + w_wind
    w_t, w_r, w_w = w_temp / total, w_rain / total, w_wind / total

    cities = ranked["city_name"].tolist()

    fig.add_bar(name="Temp comfort",
                x=cities,
                y=(ranked["temp_comfort_score"].fillna(0) * w_t).round(1),
                marker_color="#ef4444")
    fig.add_bar(name="Low rain",
                x=cities,
                y=(ranked["rain_score"].fillna(0) * w_r).round(1),
                marker_color="#3b82f6")
    fig.add_bar(name="Low wind",
                x=cities,
                y=(ranked["wind_score"].fillna(0) * w_w).round(1),
                marker_color="#8b5cf6")

    fig.update_layout(
        barmode="stack",
        height=320,
        yaxis_title="Score (pts)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        margin=dict(l=40, r=20, t=40, b=40),
    )
    return fig


def _best_day_finder(fcst: pd.DataFrame, cities: list[str],
                     w_temp: float, w_rain: float, w_wind: float) -> None:
    st.subheader("Best day to visit each city")
    fcst = fcst.copy()
    fcst["composite_score"] = _recompute_score(fcst, w_temp, w_rain, w_wind)
    best = (
        fcst[fcst["city_name"].isin(cities)]
        .sort_values("composite_score", ascending=False)
        .groupby("city_name")
        .first()
        .reset_index()[["city_name", "date", "composite_score", "condition_label",
                         "fcst_temperature_2m_mean", "fcst_precipitation_sum",
                         "fcst_wind_speed_10m_max"]]
    )
    st.dataframe(
        best.rename(columns={
            "city_name": "City", "date": "Best Date",
            "composite_score": "Score",
            "condition_label": "Condition",
            "fcst_temperature_2m_mean": "Avg Temp (°C)",
            "fcst_precipitation_sum": "Precip (mm)",
            "fcst_wind_speed_10m_max": "Wind (km/h)",
        }),
        use_container_width=True,
        hide_index=True,
    )


def show():
    st.title("🏆 Recommendations")

    with st.spinner("Loading…"):
        fcst = forecast_upcoming()
        lc   = latest_conditions()

    if fcst.empty:
        st.warning("No forecast data found.")
        return

    cities_all = sorted(fcst["city_name"].unique().tolist())

    st.subheader("Preferences")

    preset_key = st.selectbox("Activity preset", list(PRESETS.keys()))
    preset = PRESETS[preset_key]

    col1, col2, col3 = st.columns(3)
    with col1:
        w_temp = st.slider(
            "Temperature weight", 0, 10,
            int((preset["w_temp"] if preset else 0.40) * 10),
            key="w_temp",
        )
    with col2:
        w_rain = st.slider(
            "Rain weight", 0, 10,
            int((preset["w_rain"] if preset else 0.35) * 10),
            key="w_rain",
        )
    with col3:
        w_wind = st.slider(
            "Wind weight", 0, 10,
            int((preset["w_wind"] if preset else 0.25) * 10),
            key="w_wind",
        )

    total_w = w_temp + w_rain + w_wind
    if total_w == 0:
        st.warning("At least one weight must be > 0.")
        return

    st.divider()
    st.subheader("Hard filters")
    f1, f2 = st.columns(2)
    with f1:
        max_rain = st.slider("Max precipitation (mm)", 0, 30, 30)
    with f2:
        temp_range = st.slider("Acceptable mean temp (°C)", -20, 50, (-5, 40))

    with st.expander("Select cities to compare"):
        selected_cities = st.multiselect("Cities", cities_all, key="recommendations_cities")

    if not selected_cities:
        st.info("Select at least one city.")
        return

    sub = fcst[fcst["city_name"].isin(selected_cities)].copy()

    sub = sub[
        (sub["fcst_precipitation_sum"].fillna(0) <= max_rain)
        & (sub["fcst_temperature_2m_mean"].fillna(20) >= temp_range[0])
        & (sub["fcst_temperature_2m_mean"].fillna(20) <= temp_range[1])
    ]

    if sub.empty:
        st.warning("All data filtered out — loosen the hard filters.")
        return

    sub["composite_score"] = _recompute_score(sub, w_temp, w_rain, w_wind)
    city_scores = (
        sub.groupby("city_name")[["composite_score", "temp_comfort_score", "rain_score", "wind_score"]]
        .mean()
        .round(1)
        .reset_index()
        .sort_values("composite_score", ascending=False)
    )
    condition_mode = (
        sub.groupby("city_name")["condition_label"]
        .agg(lambda x: x.mode().iloc[0] if not x.mode().empty else "")
        .reset_index()
    )
    city_scores = city_scores.merge(condition_mode, on="city_name", how="left")

    st.subheader("City Leaderboard")
    _leaderboard(city_scores)

    st.divider()
    col_l, col_r = st.columns(2)
    with col_l:
        st.subheader("Score breakdown")
        st.plotly_chart(
            _score_breakdown(city_scores, w_temp, w_rain, w_wind),
            use_container_width=True,
        )
    with col_r:
        _best_day_finder(
            fcst[fcst["city_name"].isin(selected_cities)],
            selected_cities,
            w_temp, w_rain, w_wind,
        )
