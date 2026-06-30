{{ config(materialized='view') }}

-- One row per city per upcoming forecast date (>= today).
-- Includes pre-computed score components so the dashboard can reweight live.

with forecast as (

    select *
    from {{ ref('fct_forecast_accuracy') }}
    where date >= current_date

),

locations as (

    select location_id, latitude, longitude, timezone
    from {{ ref('dim_location') }}

)

select
    f.forecast_accuracy_id,
    f.location_id,
    f.city_name,
    f.country,
    f.country_code,
    f.date,
    f.forecast_snapshot_date,
    f.forecast_horizon_days,
    f.forecast_horizon_bucket,

    l.latitude,
    l.longitude,
    l.timezone,

    f.fcst_temperature_2m_max,
    f.fcst_temperature_2m_min,
    f.fcst_temperature_2m_mean,
    f.fcst_precipitation_sum,
    f.fcst_rain_sum,
    f.fcst_snowfall_sum,
    f.fcst_wind_speed_10m_max,

    -- score components (0-100); stored so dashboard can reweight without re-querying
    round(
        (1 - least(abs(coalesce(f.fcst_temperature_2m_mean, 22.0) - 22.0) / 20.0, 1.0)) * 100
    , 1) as temp_comfort_score,

    round(
        (1 - least(coalesce(f.fcst_precipitation_sum,  0) / 20.0, 1.0)) * 100
    , 1) as rain_score,

    round(
        (1 - least(coalesce(f.fcst_wind_speed_10m_max, 0) / 80.0, 1.0)) * 100
    , 1) as wind_score,

    -- composite visit score with default weights (40 / 35 / 25)
    round((
        0.40 * (1 - least(abs(coalesce(f.fcst_temperature_2m_mean, 22.0) - 22.0) / 20.0, 1.0))
        + 0.35 * (1 - least(coalesce(f.fcst_precipitation_sum,  0) / 20.0, 1.0))
        + 0.25 * (1 - least(coalesce(f.fcst_wind_speed_10m_max, 0) / 80.0, 1.0))
    ) * 100, 1) as visit_score,

    case
        when coalesce(f.fcst_temperature_2m_max, 0) >= 30       then 'Hot'
        when coalesce(f.fcst_precipitation_sum,  0) >= 5        then 'Rainy'
        when coalesce(f.fcst_wind_speed_10m_max, 0) >= 38       then 'Windy'
        when coalesce(f.fcst_temperature_2m_min, 0) <= 0        then 'Freezing'
        when coalesce(f.fcst_snowfall_sum,        0) > 0        then 'Snowy'
        when coalesce(f.fcst_temperature_2m_mean, 20) between 18 and 26
             and coalesce(f.fcst_precipitation_sum, 0) < 1      then 'Comfortable'
        else 'Mixed'
    end as condition_label,

    f.has_actuals

from forecast f
left join locations l on f.location_id = l.location_id
