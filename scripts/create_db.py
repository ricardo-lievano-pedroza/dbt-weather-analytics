import argparse
from pathlib import Path

import duckdb


def create_database(db_path: str, data_dir: str = "../data") -> None:
    """Create and populate a DuckDB database from every Parquet file in `data_dir`."""
    data_path = Path(data_dir)
    parquet_files = sorted(data_path.glob("*.parquet"))
    if not parquet_files:
        raise FileNotFoundError(f"No Parquet files found in {data_path.resolve()}")

    conn = duckdb.connect(f"../{db_path}")
    try:
        for parquet in parquet_files:
            table_name = parquet.stem
            conn.execute(
                "CREATE TABLE IF NOT EXISTS "
                f"{table_name} AS SELECT * FROM read_parquet(?)",
                [str(parquet)],
            )
            print(f"Created table: {table_name}")
    finally:
        conn.close()

    print(f"Database written to {Path(db_path).resolve()}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Create and populate a DuckDB database from Parquet files."
    )
    parser.add_argument(
        "--database",
        "-d",
        default="my_database",
        help="Name of the database file (without .duckdb extension). Default: my_database",
    )
    args = parser.parse_args()
    create_database(f"{args.database}.duckdb")
