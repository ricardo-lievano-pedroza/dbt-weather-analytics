import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from utils.db import forecast_upcoming, latest_conditions, weather_history
from utils import theme as rv

# variable -> (observed column in history, forecast column, axis title)
TREND_VARS = {
    "Temperature": ("temperature_2m_max", "fcst_temperature_2m_max", "Max temperature (°C)"),
    "Precipitation": ("precipitation_sum", "fcst_precipitation_sum", "Precipitation (mm)"),
    "Wind": ("wind_speed_10m_max", "fcst_wind_speed_10m_max", "Wind speed (km/h)"),
    "Visit score": ("visit_score", "visit_score", "Visit score"),
}

# air-quality band -> (light bg, text) pill colors
AQI_COLORS = {
    "good": ("#e1f5ee", "#0f6e56"),
    "fair": ("#eaf3de", "#3b6d11"),
    "moderate": ("#faeeda", "#854f0b"),
    "poor": ("#faece7", "#993c1d"),
    "very poor": ("#fceaea", "#a32d2d"),
    "extremely poor": ("#fbeaf0", "#72243e"),
}


def _segmented(label, options, key):
    if hasattr(st, "segmented_control"):
        return st.segmented_control(label, options, default=options[0], key=key) or options[0]
    return st.radio(label, options, horizontal=True, key=key)


def _num(v, suffix="", dec=0):
    return "—" if v is None or (isinstance(v, float) and pd.isna(v)) else f"{v:.{dec}f}{suffix}"


def _aqi_pill(band):
    if not band:
        return "<span style='color:var(--rv-faint)'>—</span>"
    bg, tx = AQI_COLORS.get(str(band).lower(), ("var(--rv-track)", "var(--rv-faint)"))
    return f"<span class='rv-pill' style='background:{bg};color:{tx}'>{band}</span>"


def _tile(label, value_html):
    return (
        "<div style='flex:1;min-width:130px;background:var(--rv-surface);border:1px solid var(--rv-hairline);"
        "border-radius:16px;padding:13px 16px'>"
        f"<div style='font-size:11px;color:var(--rv-faint)'>{label}</div>"
        "<div style='font-family:\"Space Grotesk\",\"Inter\",sans-serif;font-size:22px;font-weight:500;"
        f"color:var(--rv-text);margin-top:4px'>{value_html}</div></div>"
    )


def _hero_html(row, city):
    score = row.get("visit_score")
    reason = row.get("recommendation_reason") or ""
    last_obs = row.get("last_observed_date")
    eyebrow = "Current conditions" + (f" · {last_obs}" if last_obs is not None and pd.notna(last_obs) else "")
    score_inner = (f"{score:.0f}<span class='rv-hero-max'>/100</span>"
                   if pd.notna(score) else "—")
    return (
        "<div class='rv-hero'><div>"
        f"<div class='rv-eyebrow'>{eyebrow}</div>"
        f"<div class='rv-hero-city'>{city}</div>"
        f"<div class='rv-hero-sub'>{reason}</div></div>"
        "<div style='text-align:right'>"
        f"<div class='rv-hero-score'>{score_inner}</div>"
        "<div class='rv-eyebrow'>visit score</div></div></div>"
    )


def _stat_row(row):
    hi, lo = row.get("obs_temp_max"), row.get("obs_temp_min")
    hilo = f"{_num(hi)}° / {_num(lo)}°" if pd.notna(hi) or pd.notna(lo) else "—"
    tiles = [
        _tile("Condition", rv.condition_pill(row.get("condition_label"))),
        _tile("High / Low", hilo),
        _tile("Mean temp", _num(row.get("obs_temp_mean"), "°", 1)),
        _tile("Precipitation", _num(row.get("obs_precip") or 0, " mm", 1)),
        _tile("Wind", _num(row.get("obs_wind") or 0, " km/h")),
        _tile("Air quality", _aqi_pill(row.get("european_aqi_band"))),
    ]
    return f"<div style='display:flex;gap:12px;flex-wrap:wrap;margin-top:14px'>{''.join(tiles)}</div>"


def _forecast_cards_html(fcst_c):
    cards = []
    for _, d in fcst_c.iterrows():
        date = pd.to_datetime(d["date"]).strftime("%b %d")
        mx, mn = d.get("fcst_temperature_2m_max"), d.get("fcst_temperature_2m_min")
        temp = _num(mx) + "°" if pd.notna(mx) else "—"
        low = f"<span style='font-size:12px;color:var(--rv-faint)'> / {_num(mn)}°</span>" if pd.notna(mn) else ""
        pr = d.get("fcst_precipitation_sum") or 0
        cards.append(
            "<div style='background:var(--rv-surface);border:1px solid var(--rv-hairline);border-radius:16px;padding:12px 13px'>"
            f"<div style='font-size:11px;color:var(--rv-faint)'>{date}</div>"
            f"<div style='margin:7px 0'>{rv.condition_pill(d.get('condition_label'))}</div>"
            "<div style='font-family:\"Space Grotesk\",\"Inter\",sans-serif;font-size:20px;font-weight:500;"
            f"color:var(--rv-text)'>{temp}{low}</div>"
            f"<div style='font-size:11px;color:var(--rv-faint);margin:4px 0 8px'>{_num(pr, ' mm', 1)}</div>"
            f"{rv.score_bar(d.get('visit_score'))}</div>"
        )
    return ("<div style='display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));"
            f"gap:10px;margin-top:6px'>{''.join(cards)}</div>")


def _trend_chart(hist_c, fcst_c, obs_col, fcst_col, axis_title, theme):
    t = rv.THEMES[theme]
    fig = go.Figure()
    if obs_col in hist_c.columns and not hist_c.empty:
        fig.add_trace(go.Scatter(
            x=hist_c["date"], y=hist_c[obs_col], mode="lines", name="Observed",
            line=dict(color="#00a87e", width=2), hovertemplate="%{y:.1f}<extra>Observed</extra>",
        ))
    if fcst_col in fcst_c.columns and not fcst_c.empty:
        fig.add_trace(go.Scatter(
            x=fcst_c["date"], y=fcst_c[fcst_col], mode="lines+markers", name="Forecast",
            line=dict(color=t["spark"], width=2.5, dash="dash"), marker=dict(size=6, color=t["spark"]),
            hovertemplate="%{y:.1f}<extra>Forecast</extra>",
        ))
    today = pd.Timestamp.today().normalize()
    fig.add_shape(type="line", x0=today, x1=today, y0=0, y1=1, xref="x", yref="paper",
                  line=dict(color=t["faint"], dash="dot", width=1))
    fig.add_annotation(x=today, y=1, xref="x", yref="paper", text="Today", showarrow=False,
                       font=dict(color=t["faint"], size=11), xanchor="left", yanchor="bottom")
    fig.update_layout(
        height=420, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, system-ui, sans-serif", color=t["faint"], size=12),
        margin=dict(l=55, r=20, t=50, b=40), hovermode="x unified",
        hoverlabel=dict(bgcolor=t["surface"], bordercolor=t["hairline"],
                        font=dict(color=t["text"], family="Inter, system-ui, sans-serif")),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0,
                    font=dict(color=t["text"], size=12), bgcolor="rgba(0,0,0,0)"),
        xaxis=dict(showgrid=False, zeroline=False, linecolor=t["divider"]),
        yaxis=dict(title=axis_title, showgrid=True, gridcolor=t["divider"], zeroline=False),
    )
    return fig


def _location_row(row):
    lat, lon, elev = row.get("latitude"), row.get("longitude"), row.get("elevation")
    tiles = [
        _tile("Country", row.get("country") or "—"),
        _tile("Latitude", f"{lat:.4f}°" if pd.notna(lat) else "—"),
        _tile("Longitude", f"{lon:.4f}°" if pd.notna(lon) else "—"),
        _tile("Elevation", _num(elev, " m") if pd.notna(elev) else "—"),
    ]
    return f"<div style='display:flex;gap:12px;flex-wrap:wrap'>{''.join(tiles)}</div>"


def show():
    theme = st.session_state.get("theme", "light")

    with st.spinner("Loading city data…"):
        lc = latest_conditions()
        fcst = forecast_upcoming()
        hist = weather_history(days=30)

    if lc.empty:
        st.warning("No data available. Run `dbt build` to build the mart models.")
        return

    cities = sorted(lc["city_name"].unique().tolist())
    sel_col, _ = st.columns([3, 9])
    city = sel_col.selectbox("City", cities, key="cd_city")

    row = lc[lc["city_name"] == city].iloc[0]
    fcst_c = fcst[fcst["city_name"] == city].copy().sort_values("date").head(7)
    hist_c = hist[hist["city_name"] == city].copy().sort_values("date")
    for frame in (fcst_c, hist_c):
        if not frame.empty:
            frame["date"] = pd.to_datetime(frame["date"])

    st.markdown(_hero_html(row, city) + _stat_row(row), unsafe_allow_html=True)

    st.markdown('<div class="rv-section">7-day forecast</div>', unsafe_allow_html=True)
    if fcst_c.empty:
        st.info("No upcoming forecast data.")
    else:
        st.markdown(_forecast_cards_html(fcst_c), unsafe_allow_html=True)

    with st.container(border=True):
        st.markdown('<div class="rv-cardtitle">Trends</div>'
                    '<div class="rv-cardsub">Observed history and the 7-day forecast.</div>',
                    unsafe_allow_html=True)
        var = _segmented("Variable", list(TREND_VARS.keys()), "cd_var")
        obs_col, fcst_col, axis_title = TREND_VARS[var]
        if hist_c.empty and fcst_c.empty:
            st.info("No trend data for this city.")
        else:
            st.plotly_chart(_trend_chart(hist_c, fcst_c, obs_col, fcst_col, axis_title, theme),
                            use_container_width=True, config={"displayModeBar": False})

    st.markdown('<div class="rv-section">Location</div>', unsafe_allow_html=True)
    st.markdown(_location_row(row), unsafe_allow_html=True)
