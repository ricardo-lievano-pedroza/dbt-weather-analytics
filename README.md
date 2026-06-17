# dbt-weather-analytics

Analytics engineering project for the Open-Meteo group assignment.

## Current Setup

The cloud warehouse is MotherDuck and the project database is:

```text
open_meteo_europe
```

The database is organized into four schemas:

```text
raw
staging
intermediate
marts
```

The initial database bootstrap also creates empty raw source tables expected by the extraction pipeline:

```text
raw.raw_locations
raw.raw_weather_daily
raw.raw_forecast_daily
raw.raw_air_quality_hourly
```

## Local Setup

Create a virtual environment and install dependencies:

```bash
python -m venv .venv
```

On Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

On macOS/Linux:

```bash
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Create a local `.env` file from the example:

```bash
cp .env.example .env
```

Set the private token value in `.env`:

```text
MOTHERDUCK_TOKEN=your_private_token_here
MOTHERDUCK_DATABASE=open_meteo_europe
```

Do not commit `.env`.

## Bootstrap MotherDuck

Run:

```bash
python scripts/bootstrap_motherduck.py
```

This safely creates or verifies:

- the `open_meteo_europe` MotherDuck database
- the `raw`, `staging`, `intermediate`, and `marts` schemas
- the empty raw Open-Meteo source tables

You can also run the SQL manually in the MotherDuck UI:

```text
sql/init_motherduck.sql
```

## dbt Connection

This repo includes a `profiles.yml` that connects dbt to MotherDuck using environment variables:

```bash
dbt debug --profiles-dir .
dbt parse --profiles-dir .
```

The connection string is token-based and does not store credentials in code.

## GitHub Secret

For GitHub Actions, add this repository secret:

```text
MOTHERDUCK_TOKEN
```

Path in GitHub:

```text
Settings -> Secrets and variables -> Actions -> New repository secret
```

After adding the secret, run the manual workflow:

```text
Actions -> MotherDuck smoke test -> Run workflow
```

The workflow verifies that GitHub can connect to MotherDuck, bootstrap the database objects, and parse the dbt project.

## Extract And Load Raw Open-Meteo Data

The raw pipeline has two scripts:

```text
scripts/extract_open_meteo.py
scripts/load_raw_to_motherduck.py
```

The extractor pulls Europe-wide weather and air quality data from Open-Meteo and writes four CSV files:

```text
data/raw/raw_locations.csv
data/raw/raw_weather_daily.csv
data/raw/raw_forecast_daily.csv
data/raw/raw_air_quality_hourly.csv
```

Run the extraction locally:

```bash
python scripts/extract_open_meteo.py --output-dir data/raw --past-days 92 --forecast-days 7
```

Load the CSV files into MotherDuck:

```bash
python scripts/load_raw_to_motherduck.py --input-dir data/raw
```

The loader writes to:

```text
raw.raw_locations
raw.raw_weather_daily
raw.raw_forecast_daily
raw.raw_air_quality_hourly
```

The default load mode upserts by natural key:

- `raw_locations`: `location_id`
- `raw_weather_daily`: `location_id`, `date`
- `raw_forecast_daily`: `location_id`, `date`, `extracted_at`
- `raw_air_quality_hourly`: `location_id`, `timestamp`

This keeps the raw tables rerunnable while preserving separate forecast snapshots from different extraction runs.

To fully replace all rows in each raw table, use:

```bash
python scripts/load_raw_to_motherduck.py --input-dir data/raw --replace
```

## GitHub Raw Load Workflow

The repository includes a cloud workflow:

```text
.github/workflows/open-meteo-raw-load.yml
```

It runs the extract and load pipeline using the `MOTHERDUCK_TOKEN` repository secret.

After the workflow is merged into `main`, it can run:

- manually from the GitHub Actions tab
- automatically every day at `06:20 UTC`

The workflow also runs on pushes to the `open-meteo-extraction-load` branch for validation before merging.

## Next Work

The next project pieces are:

- create dbt staging models from the registered sources
- build intermediate and mart models
- connect a public Streamlit dashboard to the final mart tables
