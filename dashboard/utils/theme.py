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
[data-testid="stVerticalBlockBorderWrapper"]{border-radius:20px;}
div[data-testid="stVerticalBlockBorderWrapper"]:has(>div>div>[data-testid="stHorizontalBlock"]){
  border:1px solid var(--rv-hairline);background:var(--rv-surface);}

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

.rv-grid{display:flex;flex-wrap:wrap;gap:14px;justify-content:center;}
.rv-card{background:var(--rv-surface);border:1px solid var(--rv-hairline);border-radius:20px;
  flex:1 1 260px;max-width:340px;
  padding:16px 18px;transition:transform .2s ease-out,border-color .2s ease-out;animation:rvIn .5s ease-out;}
.rv-card:hover{transform:translateY(-3px);border-color:var(--rv-primary);}
.rv-card-head{display:flex;justify-content:space-between;align-items:center;gap:8px;}
.rv-city{font-size:14px;font-weight:500;color:var(--rv-text);}
.rv-pill{display:inline-flex;align-items:center;gap:5px;font-size:11px;padding:3px 9px;
  border-radius:999px;white-space:nowrap;}
.rv-temp{font-family:'Space Grotesk','Inter',sans-serif;font-size:34px;font-weight:500;
  letter-spacing:-1px;color:var(--rv-text);margin:8px 0 2px;}
.rv-stats{font-size:12px;color:var(--rv-faint);display:flex;gap:12px;margin:6px 0 12px;}
.rv-stats i{margin-right:3px;}
.rv-bar{height:6px;border-radius:999px;background:var(--rv-track);overflow:hidden;}
.rv-bar>span{display:block;height:6px;border-radius:999px;animation:rvGrow .7s ease-out;}
.rv-score-label{font-size:11px;color:var(--rv-faint);margin-top:6px;}

@keyframes rvIn{from{opacity:0;transform:translateY(6px);}}
@keyframes rvGrow{from{width:0;}}
"""


def init_theme():
    """Ensure a theme is selected. Call once, early, on every run."""
    st.session_state.setdefault("theme", "light")


def _toggle_theme():
    st.session_state.theme = "light" if st.session_state.theme == "dark" else "dark"


def render_toggle(container):
    """Render the light/dark switch. Label names the mode it switches TO."""
    label = "Light mode" if st.session_state.get("theme") == "dark" else "Dark mode"
    container.button(label, key="theme_toggle", on_click=_toggle_theme,
                     use_container_width=True)


def render_fullscreen(container):
    """Render a button that toggles browser fullscreen for the whole app.

    Fullscreen needs a client-side gesture, so this runs as a small same-origin
    component that calls requestFullscreen on the parent Streamlit document.
    """
    import streamlit.components.v1 as components

    t = THEMES[st.session_state.get("theme", "light")]
    html = f"""<style>
    body{{margin:0}}
    #fsb{{width:100%;height:36px;border-radius:999px;border:1px solid {t['hairline']};
      background:{t['surface']};color:{t['text']};font:500 14px/1 'Inter',system-ui,sans-serif;
      cursor:pointer;transition:border-color .2s ease-out;}}
    #fsb:hover{{border-color:{PRIMARY}}}
    </style>
    <button id="fsb" onclick="rvFs()">Fullscreen</button>
    <script>
    function rvFs(){{var d=window.parent.document;
      if(!d.fullscreenElement){{d.documentElement.requestFullscreen();}}else{{d.exitFullscreen();}}}}
    try{{window.parent.document.addEventListener('fullscreenchange',function(){{
      document.getElementById('fsb').textContent =
        window.parent.document.fullscreenElement ? 'Exit fullscreen' : 'Fullscreen';}});}}catch(e){{}}
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


def _sparkline(city, fcst_df, color):
    if fcst_df is None or fcst_df.empty:
        return ""
    d = fcst_df[fcst_df["city_name"] == city].sort_values("date")
    ys = [v for v in d.get("fcst_temperature_2m_max", []) if _is_num(v)]
    if len(ys) < 2:
        return ""
    lo, hi = min(ys), max(ys)
    rng = (hi - lo) or 1.0
    n = len(ys)
    pts = " ".join(
        f"{i / (n - 1) * 100:.1f},{28 - (y - lo) / rng * 24:.1f}" for i, y in enumerate(ys)
    )
    return (
        '<svg viewBox="0 0 100 32" preserveAspectRatio="none" '
        'style="width:100%;height:34px;margin-top:12px;display:block">'
        f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="2" '
        'stroke-linejoin="round" stroke-linecap="round"/></svg>'
    )


def hero(row):
    """Top-pick hero card HTML."""
    city = row.get("city_name", "")
    score = row.get("visit_score")
    reason = row.get("recommendation_reason") or ""
    return (
        '<div class="rv-hero"><div>'
        '<div class="rv-eyebrow">Top pick right now</div>'
        f'<div class="rv-hero-city">{city}</div>'
        f'<div class="rv-hero-sub">{reason}</div></div>'
        '<div style="text-align:right">'
        f'<div class="rv-hero-score">{_num(score)}</div>'
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
        f'<div class="rv-bar"><span style="width:{width:.0f}%;background:{bar}"></span></div>'
        f'<div class="rv-score-label">Visit score {_num(score)}</div>'
        f'{spark}</div>'
    )
