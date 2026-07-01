import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from utils.db import forecast_upcoming
from utils import theme as rv

MAX_CITIES = 6

# radar/table metrics: label -> (column, normalize-to-0-100 higher=better, decimals)
METRICS = {
    "Avg temp (°C)": ("fcst_temperature_2m_mean", lambda v: np.clip((v + 5) / 45 * 100, 0, 100), 1),
    "Max temp (°C)": ("fcst_temperature_2m_max",  lambda v: np.clip(v / 45 * 100, 0, 100), 1),
    "Min temp (°C)": ("fcst_temperature_2m_min",  lambda v: np.clip((v + 10) / 50 * 100, 0, 100), 1),
    "Precip (mm)":   ("fcst_precipitation_sum",   lambda v: np.clip((1 - v / 20) * 100, 0, 100), 1),
    "Wind (km/h)":   ("fcst_wind_speed_10m_max",  lambda v: np.clip((1 - v / 80) * 100, 0, 100), 1),
    "Visit score":   ("visit_score",              lambda v: np.clip(v, 0, 100), 0),
}

# line-chart variables: label -> (column, axis title, is a temperature series)
LINE_VARS = {
    "Max temp":  ("fcst_temperature_2m_max",  "Max temperature (°C)",  True),
    "Min temp":  ("fcst_temperature_2m_min",  "Min temperature (°C)",  True),
    "Mean temp": ("fcst_temperature_2m_mean", "Mean temperature (°C)", True),
    "Precip":    ("fcst_precipitation_sum",   "Precipitation (mm)",    False),
    "Wind":      ("fcst_wind_speed_10m_max",  "Wind speed (km/h)",     False),
    "Score":     ("visit_score",              "Visit score",           False),
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
        return ranked.head(4).index.tolist()
    return all_cities[:4]


def _line_chart(df, y_col, axis_title, cities, is_temp, theme):
    t = rv.THEMES[theme]
    palette = rv.SERIES[theme]
    fig = go.Figure()
    if is_temp and len(cities) == 1 and {"fcst_temperature_2m_max", "fcst_temperature_2m_min"} <= set(df.columns):
        cdf = df[df["city_name"] == cities[0]].sort_values("date")
        fig.add_trace(go.Scatter(
            x=pd.concat([cdf["date"], cdf["date"][::-1]]),
            y=pd.concat([cdf["fcst_temperature_2m_max"], cdf["fcst_temperature_2m_min"][::-1]]),
            fill="toself", fillcolor=_rgba(palette[0], 0.10), line=dict(color="rgba(0,0,0,0)"),
            hoverinfo="skip", showlegend=False,
        ))
    for i, city in enumerate(cities):
        color = palette[i % len(palette)]
        cdf = df[df["city_name"] == city].sort_values("date")
        fig.add_trace(go.Scatter(
            x=cdf["date"], y=cdf[y_col], mode="lines+markers", name=city,
            line=dict(color=color, width=2.5), marker=dict(size=6, color=color),
            hovertemplate="%{y:.1f}<extra>" + city + "</extra>",
        ))
    today = pd.Timestamp.today().normalize()
    fig.add_shape(type="line", x0=today, x1=today, y0=0, y1=1, xref="x", yref="paper",
                  line=dict(color=t["faint"], dash="dot", width=1))
    fig.add_annotation(x=today, y=1, xref="x", yref="paper", text="Today", showarrow=False,
                       font=dict(color=t["faint"], size=11), xanchor="left", yanchor="bottom")
    fig.update_layout(
        height=460, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
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
        height=460, paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, system-ui, sans-serif", color=t["faint"], size=12),
        polar=dict(
            bgcolor="rgba(0,0,0,0)",
            radialaxis=dict(range=[0, 100], gridcolor=t["divider"], linecolor=t["divider"],
                            tickfont=dict(size=9, color=t["faint"])),
            angularaxis=dict(gridcolor=t["divider"], linecolor=t["divider"],
                             tickfont=dict(color=t["text"], size=11)),
        ),
        legend=dict(orientation="h", yanchor="bottom", y=-0.12, x=0,
                    font=dict(color=t["text"], size=12), bgcolor="rgba(0,0,0,0)"),
        margin=dict(l=40, r=40, t=20, b=50), showlegend=True,
    )
    return fig


def _cell(v, colmax, is_score, dec):
    if v is None or pd.isna(v):
        return "<td>—</td>"
    width = max(0, min(100, v / colmax * 100)) if colmax else 0
    color = rv.ROLES[rv.score_role(v)][4] if is_score else "var(--rv-primary)"
    return (f"<td class='rv-num'>{v:.{dec}f}"
            f"<div class='rv-cellbar'><span style='width:{width:.0f}%;background:{color}'></span></div></td>")


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
                '<div class="rv-cardsub">Bars show each value relative to the column maximum.</div>',
                unsafe_allow_html=True)
    st.markdown(_table_html(agg, selected), unsafe_allow_html=True)


def show():
    theme = st.session_state.get("theme", "light")

    with st.spinner("Loading forecast data…"):
        fcst = forecast_upcoming()

    if fcst.empty:
        st.warning("No forecast data found. Run `dbt build` to build the mart models.")
        return

    fcst = fcst.copy()
    fcst["date"] = pd.to_datetime(fcst["date"])
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
        var_label = _segmented("Variable", list(LINE_VARS.keys()), "cmp_var") if chart_type == "Line" else None

    if not selected:
        st.info("Select at least one city.")
        return

    sub = fcst[fcst["city_name"].isin(selected)].copy()
    dates = sorted(sub["date"].unique())
    scoped = sub
    if scope == "Today only" and dates:
        scoped = sub[sub["date"] == dates[0]]
    elif scope == "Tomorrow only" and len(dates) > 1:
        scoped = sub[sub["date"] == dates[1]]

    metric_cols = [col for _, (col, _, _) in METRICS.items() if col in scoped.columns]
    agg = scoped.groupby("city_name")[metric_cols].mean().reindex(selected).round(2)

    if chart_type == "Line":
        y_col, axis_title, is_temp = LINE_VARS[var_label]
        with st.container(border=True):
            st.markdown(f'<div class="rv-cardtitle">{axis_title} · next 7 days</div>'
                        '<div class="rv-cardsub">Each city has its own color; compare trends across the week.</div>',
                        unsafe_allow_html=True)
            st.plotly_chart(_line_chart(sub, y_col, axis_title, selected, is_temp, theme),
                            use_container_width=True, config={"displayModeBar": False})
        with st.container(border=True):
            _table_card(agg, selected)
    else:
        left, right = st.columns([5, 7])
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
