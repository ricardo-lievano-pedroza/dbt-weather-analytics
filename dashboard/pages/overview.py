import streamlit as st
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from utils.db import latest_conditions, forecast_upcoming
from utils import theme as rv


def show():
    with st.spinner("Loading current conditions…"):
        lc = latest_conditions()
        fcst = forecast_upcoming()

    if lc.empty:
        st.warning("No data available. Run `dbt build` to build the mart models.")
        return

    top = lc.sort_values("visit_score", ascending=False).iloc[0]
    # Exclude the current top pick from the grid; it already headlines the hero.
    # Keyed off visit_score, so the excluded city updates automatically on reload.
    rest = lc.drop(index=top.name)
    cards = "".join(rv.kpi_card(row, fcst) for _, row in rest.iterrows())

    st.markdown(
        rv.hero(top)
        + '<div class="rv-section">Current conditions by city</div>'
        + f'<div class="rv-grid">{cards}</div>',
        unsafe_allow_html=True,
    )
