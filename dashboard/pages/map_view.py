import streamlit as st
import folium
from streamlit_folium import st_folium
import pandas as pd
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from utils.db import forecast_upcoming, dim_location
from utils import theme as rv

# label -> (column, vmin, vmax, ramp key, decimals)
VARIABLES = {
    "Visit score":   ("visit_score",               0, 100, "score",  0),
    "Temperature":   ("fcst_temperature_2m_max",    0,  45, "temp",   0),
    "Precipitation": ("fcst_precipitation_sum",     0,  20, "precip", 1),
    "Wind":          ("fcst_wind_speed_10m_max",    0,  80, "wind",   0),
}

# ramp key -> (low rgb, high rgb) using the app's semantic palette
_RAMPS = {
    "score":  ((226, 59, 74), (0, 168, 126)),    # red -> teal
    "temp":   ((55, 138, 221), (226, 59, 74)),   # blue -> red
    "precip": ((190, 215, 240), (24, 95, 165)),  # pale -> blue
    "wind":   ((203, 201, 247), (73, 79, 223)),  # pale -> cobalt
}

_TILES = {"light": "CartoDB positron", "dark": "CartoDB dark_matter"}


def _mix(a, b, t):
    t = max(0.0, min(1.0, t))
    return "#%02x%02x%02x" % tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def _color(kind, value, vmin, vmax):
    if value is None or pd.isna(value):
        return "#8d969e"
    lo, hi = _RAMPS.get(kind, ((73, 79, 223), (73, 79, 223)))
    return _mix(lo, hi, (value - vmin) / max(vmax - vmin, 1e-9))


def _segmented(label, options, key):
    """Pill segmented control on Streamlit >= 1.40, radio fallback below that."""
    if hasattr(st, "segmented_control"):
        return st.segmented_control(label, options, default=options[0], key=key) or options[0]
    return st.radio(label, options, horizontal=True, key=key)


def show():
    theme = st.session_state.get("theme", "light")

    with st.spinner("Loading forecast data…"):
        fcst = forecast_upcoming()
        locs = dim_location()

    if fcst.empty:
        st.warning("No forecast data found. Run `dbt build` to build the mart models.")
        return

    fcst = fcst.copy()
    fcst["date"] = pd.to_datetime(fcst["date"]).dt.date
    dates = sorted(fcst["date"].unique())
    conditions = ["All"]
    if "condition_label" in fcst:
        conditions += sorted(fcst["condition_label"].dropna().unique())

    with st.container(border=True):
        c1, c2, c3, c4 = st.columns([2.2, 2.2, 1.6, 1.8])
        with c1:
            var_label = _segmented("Variable", list(VARIABLES.keys()), "map_var")
        with c2:
            sel_date = st.select_slider(
                "Forecast date", options=dates, value=dates[0],
                format_func=lambda d: d.strftime("%b %d"),
            )
        with c3:
            cond = st.selectbox("Condition", conditions)
        with c4:
            min_score = st.slider("Min visit score", 0, 100, 0, 5)

    col_field, vmin, vmax, kind, dec = VARIABLES[var_label]

    day = fcst[fcst["date"] == sel_date]
    if cond != "All" and "condition_label" in day:
        day = day[day["condition_label"] == cond]
    if "visit_score" in day:
        day = day[day["visit_score"].fillna(0) >= min_score]

    if day.empty:
        st.info("No cities match the current filters.")
        return

    center = [locs["latitude"].mean(), locs["longitude"].mean()]
    fmap = folium.Map(location=center, zoom_start=4, tiles=_TILES[theme],
                      control_scale=False)

    fmap.get_root().header.add_child(folium.Element(
        "<style>.leaflet-popup-content-wrapper{border-radius:14px;box-shadow:none;"
        "border:1px solid #e2e2e7}.leaflet-popup-tip{display:none}"
        ".leaflet-tooltip{border:none;border-radius:8px;background:#16181a;color:#fff;"
        "font:400 12px Inter,system-ui,sans-serif;padding:4px 9px;box-shadow:none}"
        ".leaflet-tooltip:before{display:none}</style>"
    ))

    max_val = day[col_field].max() or 1
    for _, r in day.iterrows():
        val = r.get(col_field)
        vtxt = "N/A" if pd.isna(val) else f"{val:.{dec}f}"
        norm = 0.0 if pd.isna(val) else max(0.0, min(1.0, val / max_val))
        popup = folium.Popup(
            f"<div style='font:400 13px Inter,system-ui,sans-serif;min-width:150px'>"
            f"<div style='font-weight:500;font-size:15px'>{r['city_name']}</div>"
            f"<div style='color:#8d969e;font-size:12px;margin-bottom:6px'>"
            f"{r.get('country', '')} · {r.get('condition_label', '')}</div>"
            f"<div>{var_label}: <b>{vtxt}</b></div></div>",
            max_width=260,
        )
        folium.CircleMarker(
            location=[r["latitude"], r["longitude"]],
            radius=7 + norm * 16,
            color="#ffffff", weight=2,
            fill=True, fill_color=_color(kind, val, vmin, vmax), fill_opacity=0.9,
            tooltip=f"<b>{r['city_name']}</b> · {vtxt}",
            popup=popup,
        ).add_to(fmap)

    lo, hi = _RAMPS[kind]
    t = rv.THEMES[theme]
    fmap.get_root().html.add_child(folium.Element(
        f"<div style='position:absolute;z-index:9999;left:14px;bottom:22px;"
        f"background:{t['surface']};border:1px solid {t['hairline']};border-radius:14px;"
        f"padding:10px 12px;font:400 11px Inter,system-ui,sans-serif;color:{t['faint']}'>"
        f"<div style='margin-bottom:6px'>{var_label}</div>"
        f"<div style='width:130px;height:8px;border-radius:999px;"
        f"background:linear-gradient(90deg,{'#%02x%02x%02x' % lo},{'#%02x%02x%02x' % hi})'></div>"
        f"<div style='display:flex;justify-content:space-between;font-size:10px;margin-top:3px'>"
        f"<span>{vmin}</span><span>{vmax}</span></div></div>"
    ))

    st_folium(fmap, use_container_width=True, height=520, returned_objects=[])
    st.caption(
        f"Showing {var_label} for {sel_date:%b %d}. Point size and color scale with the "
        "value — hover for a quick read, click a city for details."
    )
