-- Compares the latest forecast snapshot for each city/date against actual
-- observed weather, producing signed and absolute errors per measure.
-- Rows where has_actuals = false represent future-dated forecasts with no
-- observed counterpart yet. Grain: location_id, date.

with forecast as (

    select * from {{ ref('int_forecast_daily_enriched') }}

),

actuals as (

    select
        location_id,
        date,
        temperature_2m_max  as actual_temperature_2m_max,
        temperature_2m_min  as actual_temperature_2m_min,
        temperature_2m_mean as actual_temperature_2m_mean,
        precipitation_sum   as actual_precipitation_sum,
        rain_sum            as actual_rain_sum,
        snowfall_sum        as actual_snowfall_sum,
        wind_speed_10m_max  as actual_wind_speed_10m_max
    from {{ ref('int_city_day_weather') }}

),

final as (

    select
        -- surrogate key
        cast(forecast.location_id as varchar) || '-' || cast(forecast.date as varchar) as forecast_accuracy_id,

        forecast.forecast_daily_id,
        forecast.location_id,
        forecast.date,

        -- location (FK to dim_location)
        forecast.city_name,
        forecast.country,
        forecast.country_code,

        -- forecast metadata
        forecast.forecast_snapshot_date,
        forecast.forecast_horizon_days,
        forecast.forecast_horizon_bucket,

        -- forecasted values
        forecast.temperature_2m_max  as fcst_temperature_2m_max,
        forecast.temperature_2m_min  as fcst_temperature_2m_min,
        forecast.temperature_2m_mean as fcst_temperature_2m_mean,
        forecast.precipitation_sum   as fcst_precipitation_sum,
        forecast.rain_sum            as fcst_rain_sum,
        forecast.snowfall_sum        as fcst_snowfall_sum,
        forecast.wind_speed_10m_max  as fcst_wind_speed_10m_max,

        -- actual values
        actuals.actual_temperature_2m_max,
        actuals.actual_temperature_2m_min,
        actuals.actual_temperature_2m_mean,
        actuals.actual_precipitation_sum,
        actuals.actual_rain_sum,
        actuals.actual_snowfall_sum,
        actuals.actual_wind_speed_10m_max,

        -- signed errors (forecast − actual; positive = over-forecast)
        forecast.temperature_2m_max  - actuals.actual_temperature_2m_max  as temp_max_error,
        forecast.temperature_2m_min  - actuals.actual_temperature_2m_min  as temp_min_error,
        forecast.temperature_2m_mean - actuals.actual_temperature_2m_mean as temp_mean_error,
        forecast.precipitation_sum   - actuals.actual_precipitation_sum   as precipitation_error,
        forecast.wind_speed_10m_max  - actuals.actual_wind_speed_10m_max  as wind_speed_error,

        -- absolute errors (useful for MAE aggregations)
        abs(forecast.temperature_2m_max  - actuals.actual_temperature_2m_max)  as temp_max_abs_error,
        abs(forecast.temperature_2m_min  - actuals.actual_temperature_2m_min)  as temp_min_abs_error,
        abs(forecast.temperature_2m_mean - actuals.actual_temperature_2m_mean) as temp_mean_abs_error,
        abs(forecast.precipitation_sum   - actuals.actual_precipitation_sum)   as precipitation_abs_error,
        abs(forecast.wind_speed_10m_max  - actuals.actual_wind_speed_10m_max)  as wind_speed_abs_error,

        actuals.actual_temperature_2m_max is not null as has_actuals

    from forecast
    left join actuals
        on forecast.location_id = actuals.location_id
        and forecast.date = actuals.date

)

select * from final