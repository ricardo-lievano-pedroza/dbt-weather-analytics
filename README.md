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

## Next Work

The next project pieces are:

- build the Open-Meteo extraction script for selected European cities
- load extracted files into the `raw` schema
- create dbt staging models from the registered sources
- build intermediate and mart models
- connect a public Streamlit dashboard to the final mart tables
