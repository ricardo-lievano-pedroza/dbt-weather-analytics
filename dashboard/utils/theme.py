"""Revolut-inspired theme for the Streamlit dashboard.

All styling lives here in Python and is injected as CSS so every page shares
one look. Supports a light/dark toggle stored in st.session_state, line-icon +
colored condition pills, Space Grotesk for display numbers, and subtle motion.
"""
import math
import streamlit as st

PRIMARY = "#494fdf"  # Revolut cobalt violet

# Per-mode design tokens (from the Revolut design system).
THEMES = {
    "dark": {
        "canvas": "#0a0a0a",
        "surface": "#16181a",
        "hairline": "rgba(255,255,255,0.12)",
        "divider": "rgba(255,255,255,0.06)",
        "text": "#ffffff",
        "mute": "rgba(255,255,255,0.72)",
        "faint": "#8d969e",
        "track": "rgba(255,255,255,0.08)",
        "spark": "#7f77dd",
    },
    "light": {
        "canvas": "#f4f4f4",
        "surface": "#ffffff",
        "hairline": "#e2e2e7",
        "divider": "#ececf0",
        "text": "#191c1f",
        "mute": "#505a63",
        "faint": "#8d969e",
        "track": "#e2e2e7",
        "spark": "#494fdf",
    },
}

# condition label -> (tabler icon, semantic role)
CONDITIONS = {
    "Comfortable": ("ti-sun", "good"),
    "Hot": ("ti-flame", "warn"),
    "Rainy": ("ti-cloud-rain", "rain"),
    "Windy": ("ti-wind", "neutral"),
    "Freezing": ("ti-snowflake", "cold"),
    "Snowy": ("ti-snowflake", "cold"),
    "Mixed": ("ti-cloud", "neutral"),
}

# role -> (dark_bg, dark_text, light_bg, light_text, bar_color)
ROLES = {
    "good": ("rgba(0,168,126,0.16)", "#5dcaa5", "#e1f5ee", "#0f6e56", "#00a87e"),
    "warn": ("rgba(236,126,0,0.16)", "#efab4f", "#faeeda", "#854f0b", "#ec7e00"),
    "bad": ("rgba(226,59,74,0.16)", "#f09595", "#fceaea", "#a32d2d", "#e23b4a"),
    "rain": ("rgba(55,108,213,0.18)", "#85b7eb", "#e6f1fb", "#185fa5", "#376cd5"),
    "cold": ("rgba(55,108,213,0.18)", "#85b7eb", "#e6f1fb", "#185fa5", "#378add"),
    "neutral": ("rgba(255,255,255,0.10)", "#c9c9cd", "#eceef0", "#505a63", "#8d969e"),
}

# up to 6 distinct, mode-aware series colors (charts with several cities)
SERIES = {
    "light": ["#494fdf", "#00a87e", "#ec7e00", "#e61e49", "#007bc2", "#a8571f"],
    "dark":  ["#7f77dd", "#1dc39b", "#f2a13a", "#f2547d", "#3fa0e0", "#c98a52"],
}

_FONTS = (
    "@import url('https://fonts.googleapis.com/css2?"
    "family=Inter:wght@400;500&family=Space+Grotesk:wght@400;500&display=swap');"
    "@import url('https://cdn.jsdelivr.net/npm/@tabler/icons-webfont@3/dist/tabler-icons.min.css');"
)

# Static CSS; only the :root values below are theme-dependent.
_BASE_CSS = """
.stApp{background:var(--rv-canvas);}
header[data-testid="stHeader"]{background:transparent;}
.block-container{padding:2rem 2.5rem 3rem;max-width:100%;}
.stApp, .stMarkdown, [data-testid="stMarkdownContainer"], p, span, label{
  color:var(--rv-text);font-family:'Inter',system-ui,-apple-system,sans-serif;}
h1,h2,h3,h4{color:var(--rv-text)!important;font-family:'Inter',system-ui,sans-serif;}
.stButton>button{background:var(--rv-surface);color:var(--rv-text);
  border:1px solid var(--rv-hairline);border-radius:999px;padding:6px 18px;font-weight:500;
  transition:border-color .2s ease-out,transform .1s ease-out;}
.stButton>button:hover{border-color:var(--rv-primary);color:var(--rv-text);}
.stButton>button:active{transform:scale(.97);}
.st-key-theme_toggle{display:flex;justify-content:flex-end;}
.st-key-theme_toggle button{width:40px;min-width:40px;height:40px;padding:0;border-radius:50%;
  display:inline-flex;align-items:center;justify-content:center;font-size:20px;line-height:1;}
[data-testid="stVerticalBlockBorderWrapper"]{border-radius:20px;
  border:1px solid var(--rv-hairline);background:var(--rv-surface);}
span[data-baseweb="tag"]{background-color:var(--rv-primary)!important;}
span[data-baseweb="tag"] *{color:#fff!important;fill:#fff!important;}

.rv-brand{font-family:'Space Grotesk','Inter',sans-serif;font-size:20px;font-weight:500;
  letter-spacing:-.3px;color:var(--rv-text);}
.rv-tagline{font-size:13px;color:var(--rv-faint);margin-left:12px;}
.rv-section{font-size:13px;color:var(--rv-faint);letter-spacing:.3px;margin:22px 2px 12px;}

.rv-hero{background:var(--rv-primary);border-radius:20px;padding:20px 24px;display:flex;
  justify-content:space-between;align-items:center;animation:rvIn .45s ease-out;}
.rv-eyebrow{font-size:11px;letter-spacing:1.4px;color:rgba(255,255,255,.72);}
.rv-hero-city{font-family:'Space Grotesk','Inter',sans-serif;font-size:30px;font-weight:500;
  letter-spacing:-.4px;color:#fff;margin-top:6px;}
.rv-hero-sub{font-size:13px;color:rgba(255,255,255,.78);margin-top:4px;max-width:520px;}
.rv-hero-score{font-family:'Space Grotesk','Inter',sans-serif;font-size:46px;font-weight:500;
  letter-spacing:-1.5px;line-height:1;color:#fff;}
.rv-hero-max{font-size:20px;font-weight:500;color:rgba(255,255,255,.6);letter-spacing:-.5px;margin-left:1px;}

.rv-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:16px;grid-auto-rows:1fr;}
@media (max-width:1300px){.rv-grid{grid-template-columns:repeat(3,minmax(0,1fr));}}
@media (max-width:850px){.rv-grid{grid-template-columns:repeat(2,minmax(0,1fr));}}
@media (max-width:520px){.rv-grid{grid-template-columns:1fr;}}
.rv-card{display:flex;flex-direction:column;background:var(--rv-surface);border:1px solid var(--rv-hairline);
  border-radius:20px;padding:18px 20px;transition:transform .2s ease-out,border-color .2s ease-out;animation:rvIn .5s ease-out;}
.rv-card:hover{transform:translateY(-3px);border-color:var(--rv-primary);}
.rv-card-head{display:flex;justify-content:space-between;align-items:center;gap:8px;}
.rv-city{font-size:15px;font-weight:500;color:var(--rv-text);}
.rv-pill{display:inline-flex;align-items:center;gap:5px;font-size:11px;padding:3px 9px;
  border-radius:999px;white-space:nowrap;}
.rv-temp{font-family:'Space Grotesk','Inter',sans-serif;font-size:40px;font-weight:500;
  letter-spacing:-1.4px;color:var(--rv-text);margin:10px 0 2px;}
.rv-stats{font-size:12px;color:var(--rv-faint);display:flex;gap:14px;margin:6px 0 14px;}
.rv-stats i{margin-right:3px;}
.rv-foot{margin-top:auto;}
.rv-bar{height:6px;border-radius:999px;background:var(--rv-track);overflow:hidden;}
.rv-bar>span{display:block;height:6px;border-radius:999px;animation:rvGrow .7s ease-out;}
.rv-score-label{font-size:11px;color:var(--rv-faint);margin-top:8px;}
.rv-spark{width:100%;height:46px;margin-top:12px;display:block;}

.rv-cardtitle{font-size:14px;font-weight:500;color:var(--rv-text);}
.rv-cardsub{font-size:11px;color:var(--rv-faint);margin:2px 0 8px;}
.rv-tbl{width:100%;border-collapse:collapse;font-size:13px;}
.rv-tbl th{text-align:left;font-weight:400;color:var(--rv-faint);font-size:11px;letter-spacing:.3px;
  padding:9px 12px;border-bottom:1px solid var(--rv-hairline);}
.rv-tbl td{padding:10px 12px;border-bottom:1px solid var(--rv-divider);color:var(--rv-text);}
.rv-tbl tr:hover td{background:var(--rv-track);}
.rv-num{font-variant-numeric:tabular-nums;}
.rv-td-city{font-weight:500;}
.rv-sc{display:flex;align-items:center;gap:8px;}
.rv-scbar{width:56px;height:5px;border-radius:999px;background:var(--rv-track);overflow:hidden;}
.rv-scbar>span{display:block;height:5px;border-radius:999px;}
.rv-cellbar{height:5px;border-radius:999px;background:var(--rv-track);overflow:hidden;margin-top:5px;}
.rv-cellbar>span{display:block;height:5px;border-radius:999px;background:var(--rv-primary);}

.rv-lrow{display:flex;align-items:center;gap:14px;padding:12px 4px;border-bottom:1px solid var(--rv-divider);animation:rvIn .4s ease-out;}
.rv-lrow:last-child{border-bottom:none;}
.rv-rank{width:30px;font-family:'Space Grotesk','Inter',sans-serif;color:var(--rv-faint);font-size:14px;}
.rv-lcity{font-weight:500;color:var(--rv-text);width:120px;}
.rv-lbar{flex:1;height:6px;border-radius:999px;background:var(--rv-track);overflow:hidden;}
.rv-lbar>span{display:block;height:6px;border-radius:999px;animation:rvGrow .7s ease-out;}
.rv-lscore{font-family:'Space Grotesk','Inter',sans-serif;color:var(--rv-text);width:64px;text-align:right;font-size:15px;}

@keyframes rvIn{from{opacity:0;transform:translateY(6px);}}
@keyframes rvGrow{from{width:0;}}
"""


def init_theme():
    """Ensure a theme is selected. Call once, early, on every run."""
    st.session_state.setdefault("theme", "light")


def _toggle_theme():
    st.session_state.theme = "light" if st.session_state.theme == "dark" else "dark"


def render_toggle(container):
    """Light/dark switch as a compact icon button (moon in light mode, sun in dark)."""
    is_light = st.session_state.get("theme") == "light"
    icon = ":material/dark_mode:" if is_light else ":material/light_mode:"
    tip = "Switch to dark mode" if is_light else "Switch to light mode"
    container.button(icon, key="theme_toggle", on_click=_toggle_theme, help=tip)


def render_fullscreen(container):
    """Render a button that toggles browser fullscreen for the whole app.

    Fullscreen needs a client-side gesture, so this runs as a small same-origin
    component that calls requestFullscreen on the parent Streamlit document.
    """
    import streamlit.components.v1 as components

    t = THEMES[st.session_state.get("theme", "light")]
    html = f"""<style>
    body{{margin:0;display:flex;justify-content:flex-start;align-items:center;height:44px}}
    #fsb{{width:40px;height:40px;border-radius:50%;border:1px solid {t['hairline']};
      background:{t['surface']};color:{t['text']};cursor:pointer;display:flex;
      align-items:center;justify-content:center;transition:border-color .2s ease-out,transform .1s ease-out;}}
    #fsb:hover{{border-color:{PRIMARY}}}
    #fsb:active{{transform:scale(.94)}}
    #fsb svg{{width:18px;height:18px}}
    </style>
    <button id="fsb" title="Toggle fullscreen" aria-label="Toggle fullscreen" onclick="rvFs()">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
        stroke-linecap="round" stroke-linejoin="round"><path d="M4 8V4h4M16 4h4v4M20 16v4h-4M8 20H4v-4"/></svg>
    </button>
    <script>
    function rvFs(){{var d=window.parent.document;
      if(!d.fullscreenElement){{d.documentElement.requestFullscreen();}}else{{d.exitFullscreen();}}}}
    </script>"""
    with container:
        components.html(html, height=44)


def inject_css():
    """Inject the full theme stylesheet for the current mode."""
    t = THEMES[st.session_state.get("theme", "dark")]
    root = (
        ":root{"
        f"--rv-primary:{PRIMARY};"
        f"--rv-canvas:{t['canvas']};"
        f"--rv-surface:{t['surface']};"
        f"--rv-hairline:{t['hairline']};"
        f"--rv-divider:{t['divider']};"
        f"--rv-text:{t['text']};"
        f"--rv-mute:{t['mute']};"
        f"--rv-faint:{t['faint']};"
        f"--rv-track:{t['track']};"
        "}"
    )
    st.markdown(f"<style>{_FONTS}{root}{_BASE_CSS}</style>", unsafe_allow_html=True)


# --- helpers ----------------------------------------------------------------

def _is_num(v):
    return v is not None and not (isinstance(v, float) and math.isnan(v))


def _num(v, dec=0, dash="—"):
    return f"{v:.{dec}f}" if _is_num(v) else dash


def score_role(score):
    if not _is_num(score):
        return "neutral"
    if score >= 70:
        return "good"
    if score >= 45:
        return "warn"
    return "bad"


def _pill_colors(role):
    dbg, dtx, lbg, ltx, _ = ROLES.get(role, ROLES["neutral"])
    return (dbg, dtx) if st.session_state.get("theme") == "dark" else (lbg, ltx)


def condition_pill(condition):
    """Line-icon + colored condition pill (reused across pages)."""
    condition = condition or "Mixed"
    icon, role = CONDITIONS.get(condition, ("ti-cloud", "neutral"))
    bg, tx = _pill_colors(role)
    return (f'<span class="rv-pill" style="background:{bg};color:{tx}">'
            f'<i class="ti {icon}"></i>{condition}</span>')


def score_bar(score):
    """A visit-score cell: a colored progress bar plus the value (— if missing)."""
    if not _is_num(score):
        return '<div class="rv-sc"><div class="rv-scbar"></div><span>—</span></div>'
    color = ROLES[score_role(score)][4]
    width = max(0, min(100, score))
    return (f'<div class="rv-sc"><div class="rv-scbar">'
            f'<span style="width:{width:.0f}%;background:{color}"></span></div>'
            f'<span>{score:.0f}</span></div>')


def _sparkline(city, fcst_df, color):
    placeholder = '<div class="rv-spark"></div>'  # keeps every card the same height
    if fcst_df is None or fcst_df.empty:
        return placeholder
    d = fcst_df[fcst_df["city_name"] == city].sort_values("date")
    ys = [v for v in d.get("fcst_temperature_2m_max", []) if _is_num(v)]
    if len(ys) < 2:
        return placeholder
    lo, hi = min(ys), max(ys)
    rng = (hi - lo) or 1.0
    n = len(ys)
    pts = " ".join(
        f"{i / (n - 1) * 100:.1f},{28 - (y - lo) / rng * 24:.1f}" for i, y in enumerate(ys)
    )
    return (
        '<svg class="rv-spark" viewBox="0 0 100 32" preserveAspectRatio="none">'
        f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="2" '
        'stroke-linejoin="round" stroke-linecap="round"/></svg>'
    )


def hero(row):
    """Top-pick hero card HTML."""
    city = row.get("city_name", "")
    score = row.get("visit_score")
    reason = row.get("recommendation_reason") or ""
    score_inner = (
        f'{_num(score)}<span class="rv-hero-max">/100</span>'
        if _is_num(score) else _num(score)
    )
    return (
        '<div class="rv-hero"><div>'
        '<div class="rv-eyebrow">Top pick right now</div>'
        f'<div class="rv-hero-city">{city}</div>'
        f'<div class="rv-hero-sub">{reason}</div></div>'
        '<div style="text-align:right">'
        f'<div class="rv-hero-score">{score_inner}</div>'
        '<div class="rv-eyebrow">visit score</div></div></div>'
    )


def kpi_card(row, fcst_df):
    """Per-city KPI card HTML."""
    theme = THEMES[st.session_state.get("theme", "dark")]
    city = row.get("city_name", "")
    condition = row.get("condition_label") or "Mixed"
    icon, role = CONDITIONS.get(condition, ("ti-cloud", "neutral"))
    pbg, ptx = _pill_colors(role)
    tmax = row.get("obs_temp_max")
    tmin = row.get("obs_temp_min")
    precip = row.get("obs_precip") or 0
    wind = row.get("obs_wind") or 0
    score = row.get("visit_score")
    bar = ROLES[score_role(score)][4]
    width = max(0, min(100, score)) if _is_num(score) else 0
    spark = _sparkline(city, fcst_df, theme["spark"])
    score_txt = f"{_num(score)}/100" if _is_num(score) else _num(score)
    return (
        '<div class="rv-card"><div class="rv-card-head">'
        f'<span class="rv-city">{city}</span>'
        f'<span class="rv-pill" style="background:{pbg};color:{ptx}">'
        f'<i class="ti {icon}"></i>{condition}</span></div>'
        f'<div class="rv-temp">{_num(tmax)}°</div>'
        '<div class="rv-stats">'
        f'<span><i class="ti ti-arrow-down"></i>{_num(tmin)}°</span>'
        f'<span><i class="ti ti-droplet"></i>{_num(precip, 1)} mm</span>'
        f'<span><i class="ti ti-wind"></i>{_num(wind)} km/h</span></div>'
        '<div class="rv-foot">'
        f'<div class="rv-bar"><span style="width:{width:.0f}%;background:{bar}"></span></div>'
        f'<div class="rv-score-label">Visit score {score_txt}</div>'
        f'{spark}</div></div>'
    )
