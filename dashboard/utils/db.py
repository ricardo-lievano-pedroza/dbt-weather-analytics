import os
import duckdb
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

SCHEMA = "marts"


def _conn_str() -> str:
    token = os.getenv("MOTHERDUCK_TOKEN", "")
    db = os.getenv("MOTHERDUCK_DATABASE", "open_meteo_europe_sa")
    if token:
        return f"md:{db}?motherduck_token={token}"
    return os.path.join(os.path.dirname(__file__), "..", "..", "my_database.duckdb")


@st.cache_data(ttl=300, show_spinner=False)
def run_query(sql: str) -> pd.DataFrame:
    conn = duckdb.connect(_conn_str(), read_only=True)
    try:
        return conn.execute(sql).df()
    finally:
        conn.close()


def latest_conditions() -> pd.DataFrame:
    return run_query(f"SELECT * FROM {SCHEMA}.mart_latest_conditions ORDER BY city_name")


def forecast_upcoming() -> pd.DataFrame:
    return run_query(
        f"SELECT * FROM {SCHEMA}.mart_forecast_upcoming ORDER BY city_name, date"
    )


def weather_history(days: int = 30) -> pd.DataFrame:
    return run_query(f"""
        SELECT *
        FROM {SCHEMA}.fct_city_weather_day
        WHERE date >= current_date - INTERVAL '{days} days'
        ORDER BY city_name, date
    """)


def forecast_accuracy_summary() -> pd.DataFrame:
    return run_query(f"""
        SELECT
            city_name,
            forecast_horizon_bucket,
            round(avg(temp_mean_abs_error), 2)   AS mae_temp_mean,
            round(avg(temp_max_abs_error),  2)    AS mae_temp_max,
            round(avg(precipitation_abs_error), 2) AS mae_precip,
            round(avg(wind_speed_abs_error), 2)   AS mae_wind,
            count(*) AS n
        FROM {SCHEMA}.fct_forecast_accuracy
        WHERE has_actuals
        GROUP BY city_name, forecast_horizon_bucket
        ORDER BY city_name, forecast_horizon_bucket
    """)


def dim_location() -> pd.DataFrame:
    return run_query(f"SELECT * FROM {SCHEMA}.dim_location ORDER BY city_name")
