import streamlit as st
import pydeck as pdk
import pandas as pd
import numpy as np
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from utils.db import forecast_upcoming, dim_location

VARIABLES = {
    "Temperature (max °C)":      ("fcst_temperature_2m_max",  0,  45, "Reds"),
    "Temperature (mean °C)":     ("fcst_temperature_2m_mean", -5, 40, "RdBu_r"),
    "Precipitation (mm)":        ("fcst_precipitation_sum",    0,  20, "Blues"),
    "Wind speed (km/h)":         ("fcst_wind_speed_10m_max",   0,  80, "Purples"),
    "Visit Score":               ("visit_score",               0, 100, "Greens"),
}

def _lerp_color(t: float, low=(59, 130, 246), high=(239, 68, 68)) -> list[int]:
    t = max(0.0, min(1.0, t))
    return [int(low[i] + (high[i] - low[i]) * t) for i in range(3)] + [200]


def _color_scale(value, vmin, vmax, label):
    if value is None or pd.isna(value):
        return [150, 150, 150, 150]
    t = (value - vmin) / max(vmax - vmin, 1e-9)
    if "Precipitation" in label:
        return _lerp_color(t, low=(230, 247, 255), high=(8, 48, 107))
    if "Wind" in label:
        return _lerp_color(t, low=(243, 232, 255), high=(88, 28, 135))
    if "Visit" in label:
        return _lerp_color(t, low=(220, 252, 231), high=(22, 101, 52))
    return _lerp_color(t, low=(59, 130, 246), high=(239, 68, 68))


def show():
    st.title("🗺 Geographic / Map View")

    with st.spinner("Loading forecast data…"):
        fcst = forecast_upcoming()
        locs = dim_location()

    if fcst.empty:
        st.warning("No forecast data found.")
        return

    col1, col2 = st.columns([2, 2])
    with col1:
        var_label = st.selectbox("Variable", list(VARIABLES.keys()))
    with col2:
        dates = sorted(fcst["date"].unique())
        date_idx = st.slider("Forecast date", 0, len(dates) - 1, 0,
                             )
        selected_date = dates[date_idx]

    col_field, vmin, vmax, _ = VARIABLES[var_label]
    day_data = fcst[fcst["date"] == selected_date].copy()

    if day_data.empty:
        st.info("No forecast data for selected date.")
        return

    day_data["color"] = day_data[col_field].apply(
        lambda v: _color_scale(v, vmin, vmax, var_label)
    )
    day_data["value_label"] = day_data[col_field].apply(
        lambda v: f"{v:.1f}" if pd.notna(v) else "N/A"
    )

    max_val = day_data[col_field].max() or 1
    day_data["radius"] = (
        day_data[col_field].fillna(0) / max_val * 120_000 + 40_000
    ).clip(40_000, 180_000)

    layer = pdk.Layer(
        "ScatterplotLayer",
        data=day_data,
        get_position=["longitude", "latitude"],
        get_radius="radius",
        get_fill_color="color",
        get_line_color=[255, 255, 255],
        line_width_min_pixels=2,
        pickable=True,
    )

    midlat = locs["latitude"].mean()
    midlon = locs["longitude"].mean()

    view = pdk.ViewState(
        latitude=midlat,
        longitude=midlon,
        zoom=3.5,
        pitch=0,
    )

    tooltip = {
        "html": (
            "<b>{city_name}</b><br/>"
            f"{var_label}: {{value_label}}<br/>"
            "Condition: {condition_label}"
        ),
        "style": {"backgroundColor": "#1e293b", "color": "white"},
    }

    st.pydeck_chart(pdk.Deck(
        layers=[layer],
        initial_view_state=view,
        tooltip=tooltip,
        map_style="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
    ))

    st.caption(f"Showing **{var_label}** for **{selected_date}**. "
               "Bubble size and color scale with the variable value. "
               "Click a bubble for details.")

    st.subheader("Values on selected date")
    display_cols = ["city_name", "country", col_field, "condition_label",
                    "latitude", "longitude"]
    display_cols = [c for c in display_cols if c in day_data.columns]
    st.dataframe(
        day_data[display_cols].rename(columns={col_field: var_label})
        .sort_values(var_label, ascending=False),
        use_container_width=True,
        hide_index=True,
    )
