import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from utils.db import forecast_upcoming
from utils import theme as rv

# short label -> (column, y-axis title, is a temperature series)
VARIABLES = {
    "Max temp":  ("fcst_temperature_2m_max",  "Max temperature (°C)",  True),
    "Min temp":  ("fcst_temperature_2m_min",  "Min temperature (°C)",  True),
    "Mean temp": ("fcst_temperature_2m_mean", "Mean temperature (°C)", True),
    "Precip":    ("fcst_precipitation_sum",   "Precipitation (mm)",    False),
    "Wind":      ("fcst_wind_speed_10m_max",  "Wind speed (km/h)",     False),
    "Score":     ("visit_score",              "Visit score",           False),
}


def _segmented(label, options, key):
    if hasattr(st, "segmented_control"):
        return st.segmented_control(label, options, default=options[0], key=key) or options[0]
    return st.radio(label, options, horizontal=True, key=key)


def _f(v, dec=1):
    return "—" if v is None or (isinstance(v, float) and pd.isna(v)) else f"{v:.{dec}f}"


def _focus_chart(df, y_col, axis_title, cities, focus, is_temp, theme):
    t = rv.THEMES[theme]
    ctx = "#c9c9cd" if theme == "light" else "rgba(255,255,255,0.20)"
    focus_color = t["spark"]
    band = "rgba(73,79,223,0.10)" if theme == "light" else "rgba(127,119,221,0.16)"

    fig = go.Figure()
    for city in cities:
        if city == focus:
            continue
        cdf = df[df["city_name"] == city].sort_values("date")
        fig.add_trace(go.Scatter(
            x=cdf["date"], y=cdf[y_col], mode="lines",
            line=dict(color=ctx, width=1.5), name=city,
            hovertemplate=f"{city}: %{{y:.1f}}<extra></extra>", showlegend=False,
        ))

    fcdf = df[df["city_name"] == focus].sort_values("date")
    have_band = is_temp and {"fcst_temperature_2m_max", "fcst_temperature_2m_min"} <= set(df.columns)
    if have_band and not fcdf.empty:
        fig.add_trace(go.Scatter(
            x=pd.concat([fcdf["date"], fcdf["date"][::-1]]),
            y=pd.concat([fcdf["fcst_temperature_2m_max"], fcdf["fcst_temperature_2m_min"][::-1]]),
            fill="toself", fillcolor=band, line=dict(color="rgba(0,0,0,0)"),
            hoverinfo="skip", showlegend=False,
        ))
    if not fcdf.empty:
        fig.add_trace(go.Scatter(
            x=fcdf["date"], y=fcdf[y_col], mode="lines+markers",
            line=dict(color=focus_color, width=3), marker=dict(size=6, color=focus_color),
            name=focus, hovertemplate=f"{focus}: %{{y:.1f}}<extra></extra>", showlegend=False,
        ))

    today = pd.Timestamp.today().normalize()
    fig.add_shape(type="line", x0=today, x1=today, y0=0, y1=1, xref="x", yref="paper",
                  line=dict(color=t["faint"], dash="dot", width=1))
    fig.add_annotation(x=today, y=1, xref="x", yref="paper", text="Today", showarrow=False,
                       font=dict(color=t["faint"], size=11), xanchor="left", yanchor="bottom")
    fig.update_layout(
        height=440, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, system-ui, sans-serif", color=t["faint"], size=12),
        margin=dict(l=55, r=20, t=30, b=40), hovermode="closest", showlegend=False,
        xaxis=dict(showgrid=False, zeroline=False, linecolor=t["divider"]),
        yaxis=dict(title=axis_title, showgrid=True, gridcolor=t["divider"], zeroline=False),
    )
    return fig


def _small_multiples(df, y_col, cities, theme):
    t = rv.THEMES[theme]
    per_row = 4
    for start in range(0, len(cities), per_row):
        chunk = cities[start:start + per_row]
        cols = st.columns(len(chunk))
        for col, city in zip(cols, chunk):
            cdf = df[df["city_name"] == city].sort_values("date")
            fig = go.Figure(go.Scatter(
                x=cdf["date"], y=cdf[y_col], mode="lines",
                line=dict(color=t["spark"], width=2),
                hovertemplate="%{y:.1f}<extra></extra>",
            ))
            fig.update_layout(
                height=170, margin=dict(l=8, r=8, t=28, b=8),
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font=dict(family="Inter, system-ui, sans-serif", color=t["faint"], size=10),
                title=dict(text=city, font=dict(size=12, color=t["text"])),
                xaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
                yaxis=dict(showgrid=True, gridcolor=t["divider"], zeroline=False),
                showlegend=False,
            )
            with col:
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def _table_html(df, cities):
    rows = df[df["city_name"].isin(cities)].sort_values(["city_name", "date"])
    head = ("<tr><th>City</th><th>Date</th><th>Max °C</th><th>Min °C</th>"
            "<th>Precip mm</th><th>Wind km/h</th><th>Visit score</th><th>Condition</th></tr>")
    body = []
    for _, r in rows.iterrows():
        d = pd.to_datetime(r["date"]).strftime("%b %d")
        body.append(
            "<tr>"
            f"<td class='rv-td-city'>{r['city_name']}</td><td>{d}</td>"
            f"<td class='rv-num'>{_f(r.get('fcst_temperature_2m_max'))}</td>"
            f"<td class='rv-num'>{_f(r.get('fcst_temperature_2m_min'))}</td>"
            f"<td class='rv-num'>{_f(r.get('fcst_precipitation_sum'))}</td>"
            f"<td class='rv-num'>{_f(r.get('fcst_wind_speed_10m_max'))}</td>"
            f"<td>{rv.score_bar(r.get('visit_score'))}</td>"
            f"<td>{rv.condition_pill(r.get('condition_label'))}</td>"
            "</tr>"
        )
    return f"<table class='rv-tbl'>{head}{''.join(body)}</table>"


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
        c1, c2, c3, c4 = st.columns([3, 3, 2, 1.4])
        with c1:
            selected = st.multiselect("Cities", all_cities, default=all_cities, key="fc_cities")
        with c2:
            var_label = _segmented("Variable", list(VARIABLES.keys()), "fc_var")
        with c3:
            focus_opts = selected or all_cities
            focus = st.selectbox("Focus city", focus_opts, key="fc_focus")
        with c4:
            small = st.toggle("Small multiples", key="fc_small")

    if not selected:
        st.info("Select at least one city.")
        return

    df = fcst[fcst["city_name"].isin(selected)]
    y_col, axis_title, is_temp = VARIABLES[var_label]

    with st.container(border=True):
        if small:
            st.markdown(
                f'<div class="rv-cardtitle">{axis_title} · per city</div>'
                '<div class="rv-cardsub">One mini chart per selected city.</div>',
                unsafe_allow_html=True,
            )
            _small_multiples(df, y_col, selected, theme)
        else:
            st.markdown(
                f'<div class="rv-cardtitle">{axis_title} · next 7 days</div>'
                f'<div class="rv-cardsub">{focus} in focus'
                + (" (with its high–low band)" if is_temp else "")
                + " — other cities shown as light context lines.</div>",
                unsafe_allow_html=True,
            )
            st.plotly_chart(
                _focus_chart(df, y_col, axis_title, selected, focus, is_temp, theme),
                use_container_width=True, config={"displayModeBar": False},
            )

    with st.container(border=True):
        st.markdown('<div class="rv-cardtitle">Forecast data table</div>', unsafe_allow_html=True)
        st.markdown(_table_html(df, selected), unsafe_allow_html=True)
