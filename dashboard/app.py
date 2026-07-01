import streamlit as st

st.set_page_config(
    page_title="Weather Analytics",
    layout="wide",
    initial_sidebar_state="collapsed",
)

import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from utils import theme as rv

rv.init_theme()
rv.inject_css()

from pages import overview, map_view, forecast, comparison, recommendations, city_detail

PAGES = [
    ("Overview", overview),
    ("Map", map_view),
    ("Forecast & trends", forecast),
    ("Comparison", comparison),
    ("Recommendations", recommendations),
    ("City detail", city_detail),
]

brand_col, ctrl_col = st.columns([9, 1.1])
brand_col.markdown(
    '<span class="rv-brand">Weather analytics</span>'
    '<span class="rv-tagline">Find the ideal place for your ideal holiday</span>',
    unsafe_allow_html=True,
)
with ctrl_col:
    toggle_col, fs_col = st.columns(2, gap="small")
    rv.render_toggle(toggle_col)
    rv.render_fullscreen(fs_col)

tabs = st.tabs([label for label, _ in PAGES])
for tab, (_, module) in zip(tabs, PAGES):
    with tab:
        module.show()
