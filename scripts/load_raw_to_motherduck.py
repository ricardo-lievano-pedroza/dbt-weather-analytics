"""Load extracted Open-Meteo CSV files into the MotherDuck raw schema."""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote

import duckdb

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional local convenience
    load_dotenv = None


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATABASE = "open_meteo_europe_sa"


@dataclass(frozen=True)
class ColumnSpec:
    name: str
    data_type: str


@dataclass(frozen=True)
class TableSpec:
    file_name: str
    table_name: str
    columns: tuple[ColumnSpec, ...]
    key_columns: tuple[str, ...]


LOCATION_COLUMNS = (
    ColumnSpec("extracted_at", "TIMESTAMPTZ"),
    ColumnSpec("location_id", "BIGINT"),
    ColumnSpec("city_name", "VARCHAR"),
    ColumnSpec("country", "VARCHAR"),
    ColumnSpec("country_code", "VARCHAR"),
    ColumnSpec("admin1", "VARCHAR"),
    ColumnSpec("latitude", "DOUBLE"),
    ColumnSpec("longitude", "DOUBLE"),
    ColumnSpec("timezone", "VARCHAR"),
    ColumnSpec("elevation", "DOUBLE"),
    ColumnSpec("population", "BIGINT"),
)

DAILY_WEATHER_COLUMNS = (
    ColumnSpec("source_name", "VARCHAR"),
    ColumnSpec("extracted_at", "TIMESTAMPTZ"),
    ColumnSpec("location_id", "BIGINT"),
    ColumnSpec("city_name", "VARCHAR"),
    ColumnSpec("country_code", "VARCHAR"),
    ColumnSpec("date", "DATE"),
    ColumnSpec("latitude", "DOUBLE"),
    ColumnSpec("longitude", "DOUBLE"),
    ColumnSpec("timezone", "VARCHAR"),
    ColumnSpec("temperature_2m_max", "DOUBLE"),
    ColumnSpec("temperature_2m_min", "DOUBLE"),
    ColumnSpec("temperature_2m_mean", "DOUBLE"),
    ColumnSpec("precipitation_sum", "DOUBLE"),
    ColumnSpec("rain_sum", "DOUBLE"),
    ColumnSpec("snowfall_sum", "DOUBLE"),
    ColumnSpec("wind_speed_10m_max", "DOUBLE"),
)

AIR_QUALITY_COLUMNS = (
    ColumnSpec("source_name", "VARCHAR"),
    ColumnSpec("extracted_at", "TIMESTAMPTZ"),
    ColumnSpec("location_id", "BIGINT"),
    ColumnSpec("city_name", "VARCHAR"),
    ColumnSpec("country_code", "VARCHAR"),
    ColumnSpec("timestamp", "TIMESTAMP"),
    ColumnSpec("latitude", "DOUBLE"),
    ColumnSpec("longitude", "DOUBLE"),
    ColumnSpec("timezone", "VARCHAR"),
    ColumnSpec("pm10", "DOUBLE"),
    ColumnSpec("pm2_5", "DOUBLE"),
    ColumnSpec("carbon_monoxide", "DOUBLE"),
    ColumnSpec("nitrogen_dioxide", "DOUBLE"),
    ColumnSpec("ozone", "DOUBLE"),
    ColumnSpec("european_aqi", "INTEGER"),
)

TABLE_SPECS = (
    TableSpec(
        file_name="raw_locations.csv",
        table_name="raw_locations",
        columns=LOCATION_COLUMNS,
        key_columns=("location_id",),
    ),
    TableSpec(
        file_name="raw_weather_daily.csv",
        table_name="raw_weather_daily",
        columns=DAILY_WEATHER_COLUMNS,
        key_columns=("location_id", "date"),
    ),
    TableSpec(
        file_name="raw_forecast_daily.csv",
        table_name="raw_forecast_daily",
        columns=DAILY_WEATHER_COLUMNS,
        key_columns=("location_id", "date", "extracted_at"),
    ),
    TableSpec(
        file_name="raw_air_quality_hourly.csv",
        table_name="raw_air_quality_hourly",
        columns=AIR_QUALITY_COLUMNS,
        key_columns=("location_id", "timestamp"),
    ),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Load extracted Open-Meteo CSV files into MotherDuck raw tables."
    )
    parser.add_argument(
        "--input-dir",
        default="data/raw",
        help="Directory containing the four raw Open-Meteo CSV files.",
    )
    parser.add_argument(
        "--database",
        default=None,
        help="MotherDuck database name. Defaults to MOTHERDUCK_DATABASE or open_meteo_europe.",
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Delete all rows from each raw table before loading.",
    )
    return parser.parse_args()


def get_token() -> str:
    token = os.getenv("MOTHERDUCK_TOKEN") or os.getenv("motherduck_token")
    if not token:
        raise RuntimeError(
            "MOTHERDUCK_TOKEN is not set. Copy .env.example to .env locally, "
            "or add MOTHERDUCK_TOKEN as a GitHub/Streamlit secret."
        )
    return token


def motherduck_path(database: str) -> str:
    token = quote(get_token(), safe="")
    return f"md:{database}?motherduck_token={token}"


def quote_identifier(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def sql_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def table_relation(spec: TableSpec) -> str:
    return f"raw.{quote_identifier(spec.table_name)}"


def temp_view_name(spec: TableSpec) -> str:
    return quote_identifier(f"tmp_{spec.table_name}")


def column_type(spec: TableSpec, column_name: str) -> str:
    return next(column.data_type for column in spec.columns if column.name == column_name)


def cast_expression(column: ColumnSpec) -> str:
    identifier = quote_identifier(column.name)
    if column.data_type == "VARCHAR":
        return f"nullif({identifier}, '')"
    return f"try_cast(nullif({identifier}, '') as {column.data_type})"


def create_temp_view(
    connection: duckdb.DuckDBPyConnection,
    spec: TableSpec,
    csv_path: Path,
) -> None:
    connection.execute(
        f"""
        create or replace temp view {temp_view_name(spec)} as
        select *
        from read_csv_auto(
            {sql_literal(csv_path.resolve().as_posix())},
            header = true,
            all_varchar = true,
            sample_size = -1
        )
        """
    )


def validate_columns(connection: duckdb.DuckDBPyConnection, spec: TableSpec) -> None:
    cursor = connection.execute(f"select * from {temp_view_name(spec)} limit 0")
    actual_columns = {description[0] for description in cursor.description}
    expected_columns = {column.name for column in spec.columns}
    missing_columns = sorted(expected_columns - actual_columns)
    if missing_columns:
        raise RuntimeError(
            f"{spec.file_name} is missing columns: {', '.join(missing_columns)}"
        )


def delete_existing_rows(
    connection: duckdb.DuckDBPyConnection,
    spec: TableSpec,
    replace: bool,
) -> None:
    relation = table_relation(spec)
    if replace:
        connection.execute(f"delete from {relation}")
        return

    conditions = []
    for key_column in spec.key_columns:
        data_type = column_type(spec, key_column)
        key_identifier = quote_identifier(key_column)
        conditions.append(
            f"target.{key_identifier} = "
            f"try_cast(nullif(incoming.{key_identifier}, '') as {data_type})"
        )

    connection.execute(
        f"""
        delete from {relation} as target
        using {temp_view_name(spec)} as incoming
        where {' and '.join(conditions)}
        """
    )


def insert_rows(connection: duckdb.DuckDBPyConnection, spec: TableSpec) -> None:
    relation = table_relation(spec)
    column_list = ", ".join(quote_identifier(column.name) for column in spec.columns)
    select_list = ", ".join(
        f"{cast_expression(column)} as {quote_identifier(column.name)}"
        for column in spec.columns
    )
    connection.execute(
        f"""
        insert into {relation} ({column_list})
        select {select_list}
        from {temp_view_name(spec)}
        """
    )


def load_table(
    connection: duckdb.DuckDBPyConnection,
    spec: TableSpec,
    input_dir: Path,
    replace: bool,
) -> None:
    csv_path = input_dir / spec.file_name
    if not csv_path.exists():
        raise FileNotFoundError(f"Missing raw CSV: {csv_path}")

    create_temp_view(connection, spec, csv_path)
    validate_columns(connection, spec)
    incoming_count = connection.execute(
        f"select count(*) from {temp_view_name(spec)}"
    ).fetchone()[0]
    if incoming_count == 0:
        raise RuntimeError(f"{spec.file_name} has no rows to load.")

    delete_existing_rows(connection, spec, replace)
    insert_rows(connection, spec)
    target_count = connection.execute(
        f"select count(*) from {table_relation(spec)}"
    ).fetchone()[0]

    action = "replaced" if replace else "upserted"
    print(
        f"{spec.table_name}: {action} {incoming_count:,} rows "
        f"from {csv_path.as_posix()} ({target_count:,} rows in table)"
    )


def main() -> int:
    if load_dotenv is not None:
        load_dotenv(PROJECT_ROOT / ".env")

    args = parse_args()
    input_dir = Path(args.input_dir)
    database = args.database or os.getenv("MOTHERDUCK_DATABASE", DEFAULT_DATABASE)
    connection = duckdb.connect(motherduck_path(database))

    try:
        for spec in TABLE_SPECS:
            load_table(connection, spec, input_dir, args.replace)
    finally:
        connection.close()

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"Raw load failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
