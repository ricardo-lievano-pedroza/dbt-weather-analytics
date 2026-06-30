import streamlit as st

st.set_page_config(
    page_title="Weather Analytics",
    page_icon="🌤",
    layout="wide",
    initial_sidebar_state="collapsed",
)

from pages import overview, map_view, forecast, comparison, recommendations, city_detail

PAGES = [
    ("🌤  Overview", overview),
    ("🗺  Map", map_view),
    ("📈  Forecast & Trends", forecast),
    ("⚖  Comparison", comparison),
    ("🏆  Recommendations", recommendations),
    ("🏙  City Detail", city_detail),
]

st.title("Weather Analytics")
st.caption("Europe")

tabs = st.tabs([label for label, _ in PAGES])
for tab, (_, module) in zip(tabs, PAGES):
    with tab:
        module.show()
