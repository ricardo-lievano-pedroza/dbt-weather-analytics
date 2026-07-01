import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from utils.db import forecast_upcoming
from utils import theme as rv

MAX_CITIES = 6

# activity preset -> temp / rain / wind weights (no emojis)
PRESETS = {
    "Custom":    None,
    "Beach day": dict(w_temp=0.50, w_rain=0.30, w_wind=0.20),
    "Hiking":    dict(w_temp=0.40, w_rain=0.35, w_wind=0.25),
    "City walk": dict(w_temp=0.35, w_rain=0.45, w_wind=0.20),
    "Skiing":    dict(w_temp=0.20, w_rain=0.45, w_wind=0.35),
}


def _segmented(label, options, key):
    if hasattr(st, "segmented_control"):
        return st.segmented_control(label, options, default=options[0], key=key) or options[0]
    return st.radio(label, options, horizontal=True, key=key)


def _f(v, dec=1):
    return "—" if v is None or (isinstance(v, float) and pd.isna(v)) else f"{v:.{dec}f}"


def _recompute_score(df, w_temp, w_rain, w_wind):
    total = w_temp + w_rain + w_wind
    w_temp, w_rain, w_wind = w_temp / total, w_rain / total, w_wind / total
    return (
        w_temp * df["temp_comfort_score"].fillna(50)
        + w_rain * df["rain_score"].fillna(50)
        + w_wind * df["wind_score"].fillna(50)
    ).round(1)


def _default_cities(fcst, all_cities):
    if "visit_score" in fcst.columns:
        ranked = fcst.groupby("city_name")["visit_score"].mean().sort_values(ascending=False)
        return ranked.head(MAX_CITIES).index.tolist()
    return all_cities[:MAX_CITIES]


def _hero_html(top):
    score = top["composite_score"]
    cond = top.get("condition_label") or ""
    return (
        "<div class='rv-hero'><div>"
        "<div class='rv-eyebrow'>Top recommendation</div>"
        f"<div class='rv-hero-city'>{top['city_name']}</div>"
        f"<div class='rv-hero-sub'>{cond} · best match for your preferences</div></div>"
        "<div style='text-align:right'>"
        f"<div class='rv-hero-score'>{score:.0f}<span class='rv-hero-max'>/100</span></div>"
        "<div class='rv-eyebrow'>match score</div></div></div>"
    )


def _leaderboard_html(ranked, start_rank):
    rows = []
    for i, (_, r) in enumerate(ranked.iterrows()):
        score = r["composite_score"]
        color = rv.ROLES[rv.score_role(score)][4]
        width = max(0, min(100, score))
        rows.append(
            "<div class='rv-lrow'>"
            f"<span class='rv-rank'>#{start_rank + i}</span>"
            f"<span class='rv-lcity'>{r['city_name']}</span>"
            f"{rv.condition_pill(r.get('condition_label'))}"
            f"<div class='rv-lbar'><span style='width:{width:.0f}%;background:{color}'></span></div>"
            f"<span class='rv-lscore'>{score:.0f}/100</span>"
            "</div>"
        )
    return "".join(rows)


def _breakdown(ranked, w_temp, w_rain, w_wind, theme):
    t = rv.THEMES[theme]
    total = w_temp + w_rain + w_wind
    w_t, w_r, w_w = w_temp / total, w_rain / total, w_wind / total
    cities = ranked["city_name"].tolist()
    fig = go.Figure()
    fig.add_bar(name="Temp comfort", x=cities,
                y=(ranked["temp_comfort_score"].fillna(0) * w_t).round(1), marker_color=rv.PRIMARY)
    fig.add_bar(name="Low rain", x=cities,
                y=(ranked["rain_score"].fillna(0) * w_r).round(1), marker_color="#00a87e")
    fig.add_bar(name="Low wind", x=cities,
                y=(ranked["wind_score"].fillna(0) * w_w).round(1), marker_color="#ec7e00")
    fig.update_layout(
        barmode="stack", height=340, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, system-ui, sans-serif", color=t["faint"], size=12),
        yaxis=dict(title="Score (pts)", gridcolor=t["divider"], zeroline=False),
        xaxis=dict(showgrid=False),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0,
                    font=dict(color=t["text"], size=12), bgcolor="rgba(0,0,0,0)"),
        hoverlabel=dict(bgcolor=t["surface"], bordercolor=t["hairline"], font=dict(color=t["text"])),
        margin=dict(l=45, r=20, t=40, b=40),
    )
    return fig


def _best_day_html(fcst, cities, w_temp, w_rain, w_wind):
    fcst = fcst.copy()
    fcst["composite_score"] = _recompute_score(fcst, w_temp, w_rain, w_wind)
    best = (
        fcst[fcst["city_name"].isin(cities)]
        .sort_values("composite_score", ascending=False)
        .groupby("city_name").first().reset_index()
        .sort_values("composite_score", ascending=False)
    )
    head = ("<tr><th>City</th><th>Best date</th><th>Match</th><th>Avg °C</th>"
            "<th>Precip mm</th><th>Wind km/h</th><th>Condition</th></tr>")
    body = []
    for _, r in best.iterrows():
        d = pd.to_datetime(r["date"]).strftime("%b %d")
        body.append(
            "<tr>"
            f"<td class='rv-td-city'>{r['city_name']}</td><td>{d}</td>"
            f"<td>{rv.score_bar(r['composite_score'])}</td>"
            f"<td class='rv-num'>{_f(r.get('fcst_temperature_2m_mean'))}</td>"
            f"<td class='rv-num'>{_f(r.get('fcst_precipitation_sum'))}</td>"
            f"<td class='rv-num'>{_f(r.get('fcst_wind_speed_10m_max'))}</td>"
            f"<td>{rv.condition_pill(r.get('condition_label'))}</td></tr>"
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

    st.session_state.setdefault("w_temp", 4)
    st.session_state.setdefault("w_rain", 3)
    st.session_state.setdefault("w_wind", 2)

    with st.container(border=True):
        st.markdown('<div class="rv-cardtitle">Preferences</div>'
                    '<div class="rv-cardsub">Pick an activity or set the weights yourself.</div>',
                    unsafe_allow_html=True)
        preset_key = _segmented("Activity preset", list(PRESETS.keys()), "rec_preset")
        preset = PRESETS[preset_key]
        if preset and st.session_state.get("_rec_last_preset") != preset_key:
            st.session_state["w_temp"] = round(preset["w_temp"] * 10)
            st.session_state["w_rain"] = round(preset["w_rain"] * 10)
            st.session_state["w_wind"] = round(preset["w_wind"] * 10)
        st.session_state["_rec_last_preset"] = preset_key
        w1, w2, w3 = st.columns(3)
        w_temp = w1.slider("Temperature weight", 0, 10, key="w_temp")
        w_rain = w2.slider("Rain weight", 0, 10, key="w_rain")
        w_wind = w3.slider("Wind weight", 0, 10, key="w_wind")

    if w_temp + w_rain + w_wind == 0:
        st.warning("Set at least one weight above zero.")
        return

    with st.container(border=True):
        f1, f2, f3 = st.columns([2, 2, 3])
        with f1:
            max_rain = st.slider("Max precipitation (mm)", 0, 30, 30, key="rec_maxrain")
        with f2:
            temp_range = st.slider("Acceptable mean temp (°C)", -20, 50, (-5, 40), key="rec_temprange")
        with f3:
            selected = st.multiselect(
                "Cities (up to 6)", all_cities, default=_default_cities(fcst, all_cities),
                max_selections=MAX_CITIES, key="rec_cities",
            )

    if not selected:
        st.info("Select at least one city.")
        return

    sub = fcst[fcst["city_name"].isin(selected)].copy()
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
        .mean().round(1).reset_index()
        .sort_values("composite_score", ascending=False)
    )
    condition_mode = (
        sub.groupby("city_name")["condition_label"]
        .agg(lambda x: x.mode().iloc[0] if not x.mode().empty else "")
        .reset_index()
    )
    city_scores = city_scores.merge(condition_mode, on="city_name", how="left")

    with st.container(border=True):
        rows = _leaderboard_html(city_scores.iloc[1:], start_rank=2) if len(city_scores) > 1 else ""
        st.markdown(
            _hero_html(city_scores.iloc[0])
            + ('<div class="rv-section">Full ranking</div>' + rows if rows else ""),
            unsafe_allow_html=True,
        )

    left, right = st.columns(2)
    with left:
        with st.container(border=True):
            st.markdown('<div class="rv-cardtitle">Score breakdown</div>'
                        '<div class="rv-cardsub">How each city\'s match score is built from your weights.</div>',
                        unsafe_allow_html=True)
            st.plotly_chart(_breakdown(city_scores, w_temp, w_rain, w_wind, theme),
                            use_container_width=True, config={"displayModeBar": False})
    with right:
        with st.container(border=True):
            st.markdown('<div class="rv-cardtitle">Best day to visit each city</div>'
                        '<div class="rv-cardsub">The highest-scoring day in the forecast window.</div>',
                        unsafe_allow_html=True)
            st.markdown(_best_day_html(sub, selected, w_temp, w_rain, w_wind), unsafe_allow_html=True)
