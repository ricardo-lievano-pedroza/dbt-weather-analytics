# dbt-weather-analytics

Analytics engineering project for the Open-Meteo group assignment. It extracts
Europe-wide weather and air-quality data from the [Open-Meteo](https://open-meteo.com/)
API, loads it into MotherDuck, transforms it with dbt through staging →
intermediate → marts layers, and serves the results in a Streamlit dashboard
that recommends the best European city for a holiday.

## Architecture

```text
Open-Meteo API
      │  scripts/extract_open_meteo.py  (→ data/raw/*.csv)
      │  scripts/load_raw_to_motherduck.py
      ▼
MotherDuck: open_meteo_europe_sa
      │
  raw ─────────► staging ─────────► intermediate ─────────► marts
 (source        (views,           (tables, business       (tables + views,
  tables)        cleaned/typed)    logic & flags)          analytics-ready)
                                                              │
                                                              ▼
                                                    Streamlit dashboard
                                                     (dashboard/app.py)
```

## Current Setup

The cloud warehouse is MotherDuck and the project database is:

```text
open_meteo_europe_sa
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
MOTHERDUCK_DATABASE=open_meteo_europe_sa
```

Do not commit `.env`.

## Bootstrap MotherDuck

Run:

```bash
python scripts/bootstrap_motherduck.py
```

This safely creates or verifies:

- the `open_meteo_europe_sa` MotherDuck database
- the `raw`, `staging`, `intermediate`, and `marts` schemas
- the empty raw Open-Meteo source tables

You can also run the SQL manually in the MotherDuck UI:

```text
sql/init_motherduck.sql
```

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

## dbt Project

This repo includes a `profiles.yml` that connects dbt to MotherDuck using
environment variables, so no credentials are stored in code:

```bash
dbt deps                       # install packages (dbt_utils)
dbt debug --profiles-dir .     # verify the MotherDuck connection
dbt build --profiles-dir .     # run + test all models
```

Materializations are configured in `dbt_project.yml`: staging as **views**,
intermediate and marts as **tables**. A `generate_schema_name` macro routes
each layer to its own schema (`staging`, `intermediate`, `marts`) instead of
the default prefixed naming.

### Staging (`models/staging`, views)

Cleaned and typed one-to-one views over the raw sources:

- `stg_locations` — one row per tracked city.
- `stg_weather_daily` — observed daily weather.
- `stg_forecast_daily` — daily forecasts, reduced to the latest snapshot per date.
- `stg_air_quality_hourly` — hourly air-quality readings.

### Intermediate (`models/intermediate`, tables)

Business logic and enrichment (grain `location_id, date`):

- `int_city_day_weather` — actual daily weather joined to location attributes.
- `int_air_quality_daily` — hourly AQI rolled up to daily average/peak, bands and coverage counts.
- `int_weather_flags` — boolean condition flags (rainy, hot, windy, freezing, snowy, poor AQI, comfortable) derived from thresholds defined as project `vars`.
- `int_forecast_daily_enriched` — daily forecasts with location attributes, forecast horizon (days ahead) and a horizon bucket.

Flag thresholds (rainy/hot/windy/comfortable, etc.) are tunable in one place —
the `vars` block of `dbt_project.yml`.

### Marts (`models/marts`)

Analytics-ready models that power the dashboard:

- `dim_location` (table) — location dimension, one row per city.
- `fct_city_weather_day` (table) — one row per city per observed day: all weather measures, condition flags and daily air quality.
- `fct_forecast_accuracy` (table) — forecast vs. observed actuals with pre-computed signed and absolute errors for MAE/bias analysis.
- `mart_latest_conditions` (view) — latest observed day + today/tomorrow forecast plus a 7-day composite visit score; powers the Overview and Recommendations.
- `mart_forecast_upcoming` (view) — upcoming forecast dates with pre-computed score components for client-side reweighting.

### Tests

Model-level tests (`unique`, `not_null`, unique-combination, relationships) are
declared in the `_*.yml` schema files, plus two singular tests in `tests/`:

- `assert_city_weather_temp_in_range.sql`
- `assert_forecast_horizon_non_negative.sql`

Run them with `dbt test --profiles-dir .` (or as part of `dbt build`).

## Streamlit Dashboard

An interactive dashboard reads directly from the `marts` schema and helps you
find the ideal European city for a holiday.

```bash
streamlit run dashboard/app.py
```

It authenticates to MotherDuck with the same `MOTHERDUCK_TOKEN` /
`MOTHERDUCK_DATABASE` values from your `.env`. Query helpers live in
`dashboard/utils/db.py` (read-only, cached). The app has six tabs
(`dashboard/pages/`):

- **Overview** — KPI cards and a top-pick hero.
- **Map** — cities plotted with their visit scores.
- **Forecast & Trends** — upcoming forecasts and history.
- **Comparison** — compare cities side by side.
- **Recommendations** — visit-score leaderboard.
- **City Detail** — per-city deep dive.

## GitHub Actions

### Raw load workflow

```text
.github/workflows/open-meteo-raw-load.yml
```

Runs the full pipeline in the cloud — extract → load → `dbt deps` → `dbt debug`
→ `dbt parse` → `dbt build` — using the `MOTHERDUCK_TOKEN` repository secret. It
can run:

- manually from the GitHub Actions tab (`workflow_dispatch`)
- automatically every day at `06:20 UTC` (`schedule`)
- on pushes to the `open-meteo-extraction-load` branch for pre-merge validation

### Smoke test workflow

```text
.github/workflows/motherduck-smoke-test.yml
```

A lightweight connectivity check that verifies GitHub can reach MotherDuck and
parse the dbt project.

### Required secret

For the workflows to run, add this repository secret:

```text
MOTHERDUCK_TOKEN
```

Path in GitHub:

```text
Settings -> Secrets and variables -> Actions -> New repository secret
```

Scheduled runs only fire from the default branch and require Actions to be
enabled for the repository.
