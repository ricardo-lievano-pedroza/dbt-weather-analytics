-- Enrich daily forecasts with location attributes and a forecast horizon.
-- Grain: location_id, date (the latest snapshot per forecast date, as produced by staging).
--
-- Snapshot logic: stg_forecast_daily keeps the most recently extracted forecast
-- per location_id/date. We surface the snapshot date (when the forecast was made)
-- and derive the forecast horizon, i.e. how many days ahead the forecast looked.

with forecast as (

    select * from {{ ref('stg_forecast_daily') }}

),

locations as (

    select * from {{ ref('stg_locations') }}

),

enriched as (

    select
        forecast.forecast_daily_id,
        forecast.location_id,
        forecast.date,

        -- snapshot logic
        forecast.extracted_at,
        cast(forecast.extracted_at as date) as forecast_snapshot_date,
        date_diff('day', cast(forecast.extracted_at as date), forecast.date) as forecast_horizon_days,

        -- location attributes
        locations.city_name,
        locations.country,
        locations.country_code,
        locations.admin1,
        locations.latitude,
        locations.longitude,
        locations.timezone,
        locations.elevation,
        locations.population,

        -- forecasted daily measures
        forecast.temperature_2m_max,
        forecast.temperature_2m_min,
        forecast.temperature_2m_mean,
        forecast.precipitation_sum,
        forecast.rain_sum,
        forecast.snowfall_sum,
        forecast.wind_speed_10m_max

    from forecast
    left join locations
        on forecast.location_id = locations.location_id

)

select
    *,
    case
        when forecast_horizon_days <= 3 then 'short (0-3d)'
        when forecast_horizon_days <= 7 then 'medium (4-7d)'
        else 'long (8d+)'
    end as forecast_horizon_bucket
from enriched
