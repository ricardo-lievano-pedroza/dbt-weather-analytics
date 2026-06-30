import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from utils.db import forecast_upcoming, latest_conditions, weather_history

CONDITION_ICON = {
    "Comfortable": "😊", "Hot": "🔥", "Rainy": "🌧",
    "Windy": "💨", "Freezing": "🥶", "Snowy": "❄️", "Mixed": "⛅",
}

AQI_BAND_COLOR = {
    "good": "#22c55e", "fair": "#84cc16",
    "moderate": "#f59e0b", "poor": "#f97316",
    "very poor": "#ef4444", "extremely poor": "#7f1d1d",
}


def _conditions_panel(row: pd.Series) -> None:
    icon = CONDITION_ICON.get(row.get("condition_label", "Mixed"), "⛅")
    cols = st.columns(5)
    with cols[0]:
        st.markdown(f"<div style='font-size:3.5rem;text-align:center'>{icon}</div>",
                    unsafe_allow_html=True)
        st.caption(row.get("condition_label", ""))
    with cols[1]:
        st.metric("High", f"{row.get('obs_temp_max', 'N/A'):.1f}°C" if pd.notna(row.get("obs_temp_max")) else "N/A")
        st.metric("Low",  f"{row.get('obs_temp_min', 'N/A'):.1f}°C" if pd.notna(row.get("obs_temp_min")) else "N/A")
    with cols[2]:
        st.metric("Mean Temp",   f"{row.get('obs_temp_mean', 'N/A'):.1f}°C" if pd.notna(row.get("obs_temp_mean")) else "N/A")
        st.metric("Precip",      f"{row.get('obs_precip', 0) or 0:.1f} mm")
    with cols[3]:
        st.metric("Wind",        f"{row.get('obs_wind', 0) or 0:.0f} km/h")
        band = row.get("european_aqi_band") or "—"
        band_color = AQI_BAND_COLOR.get((band or "").lower(), "#888")
        st.markdown(
            f"<b>AQI band</b>: <span style='color:{band_color}'>{band}</span>",
            unsafe_allow_html=True,
        )
    with cols[4]:
        score = row.get("visit_score")
        st.metric("Visit Score", f"{score:.0f}/100" if pd.notna(score) else "N/A")
        st.caption(row.get("recommendation_reason", ""))


def _forecast_cards(fcst_city: pd.DataFrame) -> None:
    cols = st.columns(len(fcst_city))
    for col, (_, day) in zip(cols, fcst_city.iterrows()):
        icon = CONDITION_ICON.get(day.get("condition_label", "Mixed"), "⛅")
        with col:
            with st.container(border=True):
                st.caption(str(day["date"]))
                st.markdown(f"<div style='font-size:1.6rem;text-align:center'>{icon}</div>",
                            unsafe_allow_html=True)
                mx = day.get("fcst_temperature_2m_max")
                mn = day.get("fcst_temperature_2m_min")
                pr = day.get("fcst_precipitation_sum", 0) or 0
                if pd.notna(mx):
                    st.markdown(f"**{mx:.0f}°** / {mn:.0f}°" if pd.notna(mn) else f"**{mx:.0f}°**")
                st.caption(f"🌧 {pr:.1f} mm" if pr > 0 else "☀️ Dry")
                score = day.get("visit_score")
                if pd.notna(score):
                    st.caption(f"Score: {score:.0f}")


def _line_chart(df: pd.DataFrame, y: str, title: str, color: str = "#3b82f6") -> go.Figure:
    fig = go.Figure(go.Scatter(
        x=df["date"], y=df[y],
        mode="lines+markers",
        line=dict(color=color, width=2),
        marker=dict(size=6),
        hovertemplate="%{x}: %{y:.1f}<extra></extra>",
    ))
    today = str(pd.Timestamp.today().date())
    fig.add_vline(x=today, line_dash="dot", line_color="gray",
                  annotation_text="Today")
    fig.update_layout(
        title=title, height=250,
        margin=dict(l=40, r=20, t=40, b=30),
    )
    return fig


def _history_vs_forecast(hist_city: pd.DataFrame, fcst_city: pd.DataFrame, y_hist: str,
                          y_fcst: str, title: str) -> go.Figure:
    fig = go.Figure()
    if not hist_city.empty:
        fig.add_trace(go.Scatter(
            x=hist_city["date"], y=hist_city[y_hist],
            mode="lines", name="Observed",
            line=dict(color="#10b981", width=2),
        ))
    if not fcst_city.empty:
        fig.add_trace(go.Scatter(
            x=fcst_city["date"], y=fcst_city[y_fcst],
            mode="lines+markers", name="Forecast",
            line=dict(color="#6366f1", width=2, dash="dash"),
            marker=dict(size=5),
        ))
    today = str(pd.Timestamp.today().date())
    fig.add_vline(x=today, line_dash="dot", line_color="#6b7280",
                  annotation_text="Today")
    fig.update_layout(
        title=title, height=280,
        legend=dict(orientation="h"),
        margin=dict(l=40, r=20, t=40, b=30),
        hovermode="x unified",
    )
    return fig


def show():
    st.title("🏙 City Detail")

    with st.spinner("Loading…"):
        lc   = latest_conditions()
        fcst = forecast_upcoming()
        hist = weather_history(days=30)

    if lc.empty:
        st.warning("No data available.")
        return

    cities = sorted(lc["city_name"].unique().tolist())
    city = st.selectbox("Select a city", cities)

    lc_row  = lc[lc["city_name"] == city].iloc[0]
    fcst_c  = fcst[fcst["city_name"] == city].sort_values("date").head(7)
    hist_c  = hist[hist["city_name"] == city].sort_values("date")

    st.subheader(f"Current conditions — {city}")
    st.caption(f"Latest observation: {lc_row.get('last_observed_date', 'unknown')}")
    _conditions_panel(lc_row)

    st.divider()
    st.subheader("7-day forecast")
    if not fcst_c.empty:
        _forecast_cards(fcst_c)
    else:
        st.info("No upcoming forecast data.")

    st.divider()
    st.subheader("Temperature: observed vs forecast")
    if not hist_c.empty or not fcst_c.empty:
        fig_temp = _history_vs_forecast(
            hist_c, fcst_c,
            "temperature_2m_max", "fcst_temperature_2m_max",
            "Max Temperature (°C)",
        )
        st.plotly_chart(fig_temp, use_container_width=True)

    col_l, col_r = st.columns(2)
    with col_l:
        if not fcst_c.empty:
            st.plotly_chart(
                _line_chart(fcst_c, "fcst_precipitation_sum", "Precipitation forecast (mm)", "#3b82f6"),
                use_container_width=True,
            )
    with col_r:
        if not fcst_c.empty:
            st.plotly_chart(
                _line_chart(fcst_c, "fcst_wind_speed_10m_max", "Wind speed forecast (km/h)", "#8b5cf6"),
                use_container_width=True,
            )

    st.divider()
    st.subheader("Visit score trend (forecast horizon)")
    if not fcst_c.empty and "visit_score" in fcst_c.columns:
        st.plotly_chart(
            _line_chart(fcst_c, "visit_score", "Visit Score / day", "#22c55e"),
            use_container_width=True,
        )

    st.divider()
    st.subheader("Location info")
    info_cols = st.columns(4)
    info_map = {
        "Country":   lc_row.get("country", ""),
        "Latitude":  f"{lc_row.get('latitude', 0):.4f}°",
        "Longitude": f"{lc_row.get('longitude', 0):.4f}°",
        "Elevation": f"{lc_row.get('elevation', 0):.0f} m" if pd.notna(lc_row.get("elevation")) else "N/A",
    }
    for col, (k, v) in zip(info_cols, info_map.items()):
        col.metric(k, v)
