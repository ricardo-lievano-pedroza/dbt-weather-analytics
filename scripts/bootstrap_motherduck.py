"""Create and verify the MotherDuck database objects for the project."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from urllib.parse import quote

import duckdb

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional local convenience
    load_dotenv = None


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATABASE = "open_meteo_europe"
EXPECTED_SCHEMAS = ("raw", "staging", "intermediate", "marts")
EXPECTED_RAW_TABLES = (
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


def motherduck_path() -> str:
    token = quote(get_token(), safe="")
    return f"md:?motherduck_token={token}"


def run_sql_file(
    connection: duckdb.DuckDBPyConnection,
    sql_file: Path,
    database: str,
) -> None:
    sql = sql_file.read_text(encoding="utf-8").replace(DEFAULT_DATABASE, database)
    for statement in sql.split(";"):
        statement = statement.strip()
        if statement:
            connection.execute(statement)


def fetch_names(
    connection: duckdb.DuckDBPyConnection,
    query: str,
    parameters: list[str],
) -> set[str]:
    return {row[0] for row in connection.execute(query, parameters).fetchall()}


def main() -> int:
    if load_dotenv is not None:
        load_dotenv(PROJECT_ROOT / ".env")

    database = os.getenv("MOTHERDUCK_DATABASE", DEFAULT_DATABASE)
    sql_file = PROJECT_ROOT / "sql" / "init_motherduck.sql"

    connection = duckdb.connect(motherduck_path())
    try:
        run_sql_file(connection, sql_file, database)

        schemas = fetch_names(
            connection,
            """
            select schema_name
            from information_schema.schemata
            where catalog_name = ?
            """,
            [database],
        )
        missing_schemas = sorted(set(EXPECTED_SCHEMAS) - schemas)
        if missing_schemas:
            raise RuntimeError(f"Missing schemas: {', '.join(missing_schemas)}")

        raw_tables = fetch_names(
            connection,
            """
            select table_name
            from information_schema.tables
            where table_catalog = ?
              and table_schema = 'raw'
            """,
            [database],
        )
        missing_tables = sorted(set(EXPECTED_RAW_TABLES) - raw_tables)
        if missing_tables:
            raise RuntimeError(f"Missing raw tables: {', '.join(missing_tables)}")

        print(f"MotherDuck database ready: {database}")
        print("Schemas:", ", ".join(EXPECTED_SCHEMAS))
        print("Raw tables:", ", ".join(EXPECTED_RAW_TABLES))
    finally:
        connection.close()

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"MotherDuck bootstrap failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
