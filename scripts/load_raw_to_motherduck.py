"""Load extracted Open-Meteo CSVs into the MotherDuck raw schema."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import duckdb

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional local convenience
    load_dotenv = None


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"
RAW_TABLES = (
    "raw_locations",
    "raw_weather_daily",
    "raw_forecast_daily",
    "raw_air_quality_hourly",
)


def get_token() -> str:
    token = os.getenv("MOTHERDUCK_TOKEN") or os.getenv("motherduck_token")
    if not token:
        raise RuntimeError(
            "MOTHERDUCK_TOKEN is not set. Copy .env.example to .env locally, "
            "or add MOTHERDUCK_TOKEN as a GitHub/Streamlit secret."
        )
    return token


def motherduck_path(database: str) -> str:
    from urllib.parse import quote

    token = quote(get_token(), safe="")
    return f"md:{database}?motherduck_token={token}"


def load_table(connection: duckdb.DuckDBPyConnection, table: str) -> int:
    csv_path = RAW_DATA_DIR / f"{table}.csv"
    if not csv_path.exists():
        raise RuntimeError(f"Missing raw CSV: {csv_path}")

    with csv_path.open(encoding="utf-8") as csv_file:
        columns = csv_file.readline().strip().split(",")
    column_list = ", ".join(columns)

    csv_posix_path = csv_path.as_posix()
    connection.execute(f"TRUNCATE TABLE raw.{table}")
    connection.execute(
        f"""
        COPY raw.{table} ({column_list})
        FROM '{csv_posix_path}'
        (FORMAT CSV, HEADER, AUTO_DETECT TRUE)
        """
    )
    return connection.execute(f"SELECT count(*) FROM raw.{table}").fetchone()[0]


def main() -> int:
    if load_dotenv is not None:
        load_dotenv(PROJECT_ROOT / ".env")

    database = os.getenv("MOTHERDUCK_DATABASE", "open_meteo_europe")
    connection = duckdb.connect(motherduck_path(database))
    try:
        for table in RAW_TABLES:
            row_count = load_table(connection, table)
            print(f"Loaded {row_count:,} rows into raw.{table}")
    finally:
        connection.close()

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"Raw load failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
