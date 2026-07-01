import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from utils.db import forecast_upcoming, weather_history
from utils import theme as rv

MAX_CITIES = 6

# radar/table metrics (forecast, scope-aggregated): label -> (column, normalize-0-100, decimals)
METRICS = {
    "Avg temp (°C)": ("fcst_temperature_2m_mean", lambda v: np.clip((v + 5) / 45 * 100, 0, 100), 1),
    "Max temp (°C)": ("fcst_temperature_2m_max",  lambda v: np.clip(v / 45 * 100, 0, 100), 1),
    "Min temp (°C)": ("fcst_temperature_2m_min",  lambda v: np.clip((v + 10) / 50 * 100, 0, 100), 1),
    "Precip (mm)":   ("fcst_precipitation_sum",   lambda v: np.clip((1 - v / 20) * 100, 0, 100), 1),
    "Wind (km/h)":   ("fcst_wind_speed_10m_max",  lambda v: np.clip((1 - v / 80) * 100, 0, 100), 1),
    "Visit score":   ("visit_score",              lambda v: np.clip(v, 0, 100), 0),
}

# 30-day observed trends: label -> (mean/value column, min column or None, max column or None, title)
TREND_VARS = {
    "Temperature": ("temperature_2m_mean", "temperature_2m_min", "temperature_2m_max",
                    "Temperature range (°C) — min / mean / max"),
    "Precipitation": ("precipitation_sum", None, None, "Daily precipitation (mm)"),
    "Wind": ("wind_speed_10m_max", None, None, "Daily max wind (km/h)"),
}

SCOPES = ["7-day average", "Today only", "Tomorrow only"]


def _segmented(label, options, key):
    if hasattr(st, "segmented_control"):
        return st.segmented_control(label, options, default=options[0], key=key) or options[0]
    return st.radio(label, options, horizontal=True, key=key)


def _rgba(hexc, a):
    hexc = hexc.lstrip("#")
    r, g, b = int(hexc[0:2], 16), int(hexc[2:4], 16), int(hexc[4:6], 16)
    return f"rgba({r},{g},{b},{a})"


def _default_cities(fcst, all_cities):
    if "visit_score" in fcst.columns:
        ranked = fcst.groupby("city_name")["visit_score"].mean().sort_values(ascending=False)
        return ranked.head(3).index.tolist()
    return all_cities[:3]


def _trends_chart(hist, cities, var, theme):
    mean_col, min_col, max_col, _ = TREND_VARS[var]
    t = rv.THEMES[theme]
    palette = rv.SERIES[theme]
    fig = go.Figure()
    for i, city in enumerate(cities):
        color = palette[i % len(palette)]
        cdf = hist[hist["city_name"] == city].sort_values("date")
        if cdf.empty:
            continue
        line_col = mean_col if mean_col in cdf.columns else (max_col if max_col else None)
        if line_col is None or line_col not in cdf.columns:
            continue
        if min_col and max_col and {min_col, max_col} <= set(cdf.columns):
            fig.add_trace(go.Scatter(
                x=pd.concat([cdf["date"], cdf["date"][::-1]]),
                y=pd.concat([cdf[max_col], cdf[min_col][::-1]]),
                fill="toself", fillcolor=_rgba(color, 0.12), line=dict(color="rgba(0,0,0,0)"),
                name=city, hoverinfo="skip", showlegend=False,
            ))
        fig.add_trace(go.Scatter(
            x=cdf["date"], y=cdf[line_col], mode="lines", name=city,
            line=dict(color=color, width=2), hovertemplate="%{y:.1f}<extra>" + city + "</extra>",
        ))
    fig.update_layout(
        height=440, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, system-ui, sans-serif", color=t["faint"], size=12),
        margin=dict(l=55, r=20, t=30, b=40), hovermode="x unified",
        hoverlabel=dict(bgcolor=t["surface"], bordercolor=t["hairline"],
                        font=dict(color=t["text"], family="Inter, system-ui, sans-serif")),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0,
                    font=dict(color=t["text"], size=12), bgcolor="rgba(0,0,0,0)"),
        xaxis=dict(showgrid=False, zeroline=False, linecolor=t["divider"]),
        yaxis=dict(showgrid=True, gridcolor=t["divider"], zeroline=False),
    )
    return fig


def _radar(agg, cities, theme):
    t = rv.THEMES[theme]
    palette = rv.SERIES[theme]
    labels = list(METRICS.keys())
    theta = labels + [labels[0]]
    fig = go.Figure()
    for i, city in enumerate(cities):
        if city not in agg.index:
            continue
        vals = []
        for label, (col, norm, _) in METRICS.items():
            raw = agg.loc[city, col] if col in agg.columns else np.nan
            vals.append(float(norm(raw)) if pd.notna(raw) else 0.0)
        color = palette[i % len(palette)]
        fig.add_trace(go.Scatterpolar(
            r=vals + [vals[0]], theta=theta, name=city, mode="lines",
            line=dict(color=color, width=2), fill="toself", fillcolor=_rgba(color, 0.10),
        ))
    fig.update_layout(
        height=400, paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, system-ui, sans-serif", color=t["faint"], size=12),
        polar=dict(
            bgcolor="rgba(0,0,0,0)",
            radialaxis=dict(range=[0, 100], gridcolor=t["divider"], linecolor=t["divider"],
                            tickfont=dict(size=9, color=t["faint"])),
            angularaxis=dict(gridcolor=t["divider"], linecolor=t["divider"],
                             tickfont=dict(color=t["text"], size=11)),
        ),
        legend=dict(orientation="h", yanchor="bottom", y=-0.14, x=0,
                    font=dict(color=t["text"], size=12), bgcolor="rgba(0,0,0,0)"),
        margin=dict(l=12, r=12, t=16, b=60), showlegend=True,
    )
    return fig


def _cell(v, colmax, is_score, dec):
    """Heatmap-tinted cell: stronger tint = higher value within the column."""
    if v is None or pd.isna(v):
        return "<td>—</td>"
    norm = max(0.0, min(1.0, v / colmax)) if colmax else 0.0
    base = rv.ROLES[rv.score_role(v)][4] if is_score else "#494fdf"
    bg = _rgba(base, round(0.06 + 0.26 * norm, 3))
    return f"<td class='rv-num' style='background:{bg}'>{v:.{dec}f}</td>"


def _table_html(agg, cities):
    labels = list(METRICS.keys())
    colmax = {}
    for label, (col, _, _) in METRICS.items():
        vals = [agg.loc[c, col] for c in cities
                if c in agg.index and col in agg.columns and pd.notna(agg.loc[c, col])]
        colmax[label] = max(vals) if vals else 0
    head = "<tr><th>City</th>" + "".join(f"<th>{l}</th>" for l in labels) + "</tr>"
    body = []
    for city in cities:
        cells = [f"<td class='rv-td-city'>{city}</td>"]
        for label, (col, _, dec) in METRICS.items():
            v = agg.loc[city, col] if (city in agg.index and col in agg.columns) else np.nan
            cells.append(_cell(v, colmax[label], label == "Visit score", dec))
        body.append("<tr>" + "".join(cells) + "</tr>")
    return f"<table class='rv-tbl'>{head}{''.join(body)}</table>"


def _table_card(agg, selected):
    st.markdown('<div class="rv-cardtitle">Metric comparison</div>'
                '<div class="rv-cardsub">Each cell tinted by its value within the column (visit score by its rating).</div>',
                unsafe_allow_html=True)
    st.markdown(_table_html(agg, selected), unsafe_allow_html=True)


def show():
    theme = st.session_state.get("theme", "light")

    with st.spinner("Loading data…"):
        fcst = forecast_upcoming()
        hist = weather_history(days=30)

    if fcst.empty:
        st.warning("No forecast data found. Run `dbt build` to build the mart models.")
        return

    fcst = fcst.copy()
    fcst["date"] = pd.to_datetime(fcst["date"])
    if hist is not None and not hist.empty:
        hist = hist.copy()
        hist["date"] = pd.to_datetime(hist["date"])
    all_cities = sorted(fcst["city_name"].unique().tolist())

    with st.container(border=True):
        c1, c2, c3 = st.columns([4, 2, 2])
        with c1:
            selected = st.multiselect(
                "Cities (up to 6)", all_cities, default=_default_cities(fcst, all_cities),
                max_selections=MAX_CITIES, key="cmp_cities",
            )
        with c2:
            chart_type = _segmented("Chart", ["Line", "Radar"], "cmp_chart")
        with c3:
            scope = _segmented("Scope", SCOPES, "cmp_scope")

    if not selected:
        st.info("Select at least one city.")
        return

    scoped = fcst[fcst["city_name"].isin(selected)].copy()
    dates = sorted(scoped["date"].unique())
    if scope == "Today only" and dates:
        scoped = scoped[scoped["date"] == dates[0]]
    elif scope == "Tomorrow only" and len(dates) > 1:
        scoped = scoped[scoped["date"] == dates[1]]
    metric_cols = [col for _, (col, _, _) in METRICS.items() if col in scoped.columns]
    agg = scoped.groupby("city_name")[metric_cols].mean().reindex(selected).round(2)

    if chart_type == "Line":
        var = _segmented("Variable", list(TREND_VARS.keys()), "cmp_trendvar")
        _, _, _, title = TREND_VARS[var]
        with st.container(border=True):
            st.markdown(f'<div class="rv-cardtitle">{title}</div>'
                        '<div class="rv-cardsub">Daily observed weather over the past ~30 days.</div>',
                        unsafe_allow_html=True)
            hsub = hist[hist["city_name"].isin(selected)] if (hist is not None and not hist.empty) else None
            if hsub is None or hsub.empty:
                st.info("No historical data available for these cities.")
            else:
                st.plotly_chart(_trends_chart(hsub, selected, var, theme),
                                use_container_width=True, config={"displayModeBar": False})
        with st.container(border=True):
            _table_card(agg, selected)
    else:
        left, right = st.columns([4, 8])
        with left:
            with st.container(border=True):
                st.markdown('<div class="rv-cardtitle">Profile comparison</div>'
                            '<div class="rv-cardsub">Each axis normalized 0–100, higher is better.</div>',
                            unsafe_allow_html=True)
                st.plotly_chart(_radar(agg, selected, theme), use_container_width=True,
                                config={"displayModeBar": False})
        with right:
            with st.container(border=True):
                _table_card(agg, selected)
