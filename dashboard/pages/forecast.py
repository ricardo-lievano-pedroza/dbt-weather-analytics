import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from utils.db import forecast_upcoming, weather_history

VARIABLES = {
    "Max Temperature (°C)":  "fcst_temperature_2m_max",
    "Min Temperature (°C)":  "fcst_temperature_2m_min",
    "Mean Temperature (°C)": "fcst_temperature_2m_mean",
    "Precipitation (mm)":    "fcst_precipitation_sum",
    "Wind Speed (km/h)":     "fcst_wind_speed_10m_max",
    "Visit Score":           "visit_score",
}

CITY_COLORS = px.colors.qualitative.Safe


def _multi_line(df: pd.DataFrame, y_col: str, var_label: str, cities: list[str]) -> go.Figure:
    fig = go.Figure()
    today = pd.Timestamp.today().normalize()

    for i, city in enumerate(cities):
        cdf = df[df["city_name"] == city].sort_values("date")
        color = CITY_COLORS[i % len(CITY_COLORS)]
        fig.add_trace(go.Scatter(
            x=cdf["date"], y=cdf[y_col],
            mode="lines+markers",
            name=city,
            line=dict(color=color, width=2),
            marker=dict(size=6),
        ))

        if "Temperature" in var_label and "fcst_temperature_2m_min" in df.columns and y_col == "fcst_temperature_2m_max":
            fig.add_trace(go.Scatter(
                x=pd.concat([cdf["date"], cdf["date"].iloc[::-1]]),
                y=pd.concat([cdf["fcst_temperature_2m_max"], cdf["fcst_temperature_2m_min"].iloc[::-1]]),
                fill="toself",
                fillcolor=color.replace("rgb", "rgba").replace(")", ",0.12)") if color.startswith("rgb") else color,
                line=dict(color="rgba(255,255,255,0)"),
                showlegend=False,
                hoverinfo="skip",
            ))

    fig.add_vline(x=str(today.date()), line_dash="dot", line_color="gray",
                  annotation_text="Today", annotation_position="top right")

    fig.update_layout(
        height=420,
        xaxis_title="Date",
        yaxis_title=var_label,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=40, r=20, t=40, b=40),
        hovermode="x unified",
    )
    return fig


def _small_multiples(df: pd.DataFrame, cities: list[str]) -> None:
    var_items = list(VARIABLES.items())
    cols_per_row = 3
    for row_start in range(0, len(var_items), cols_per_row):
        row_vars = var_items[row_start:row_start + cols_per_row]
        cols = st.columns(len(row_vars))
        for col, (label, field) in zip(cols, row_vars):
            if field not in df.columns:
                continue
            with col:
                fig = go.Figure()
                for i, city in enumerate(cities):
                    cdf = df[df["city_name"] == city].sort_values("date")
                    fig.add_trace(go.Scatter(
                        x=cdf["date"], y=cdf[field],
                        mode="lines", name=city,
                        line=dict(color=CITY_COLORS[i % len(CITY_COLORS)], width=2),
                        showlegend=(row_start == 0),
                    ))
                fig.update_layout(
                    title=label, height=220,
                    margin=dict(l=20, r=10, t=30, b=20),
                    showlegend=False,
                )
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def show():
    st.title("📈 Forecast & Trends")

    with st.spinner("Loading…"):
        fcst = forecast_upcoming()

    if fcst.empty:
        st.warning("No forecast data found.")
        return

    cities = sorted(fcst["city_name"].unique().tolist())

    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        selected_cities = st.multiselect("Cities", cities, default=cities, key="forecast_cities")
    with col2:
        var_label = st.selectbox("Variable", list(VARIABLES.keys()))
    with col3:
        small_mult = st.toggle("Small multiples")

    if not selected_cities:
        st.info("Select at least one city.")
        return

    filtered = fcst[fcst["city_name"].isin(selected_cities)]
    y_col = VARIABLES[var_label]

    if small_mult:
        st.subheader("All variables at once")
        _small_multiples(filtered, selected_cities)
    else:
        fig = _multi_line(filtered, y_col, var_label, selected_cities)
        st.plotly_chart(fig, use_container_width=True)

    if "Temperature" in var_label and not small_mult:
        st.caption("Shaded band = daily high–low range.")

    st.divider()
    st.subheader("Forecast data table")
    disp_cols = ["city_name", "date", "fcst_temperature_2m_max", "fcst_temperature_2m_min",
                 "fcst_precipitation_sum", "fcst_wind_speed_10m_max", "visit_score", "condition_label"]
    disp_cols = [c for c in disp_cols if c in filtered.columns]
    st.dataframe(
        filtered[filtered["city_name"].isin(selected_cities)][disp_cols],
        use_container_width=True, hide_index=True,
    )
