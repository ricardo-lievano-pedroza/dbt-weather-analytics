-- Roll hourly air quality measurements up to one row per city per local date.
-- Grain: location_id, date.
--
-- Note: raw_air_quality_hourly is the highest-volume source. As history grows,
-- consider converting this model to an incremental materialization keyed on
-- `date` so daily rollups are not recomputed for the full history every run.

with hourly as (

    select * from {{ ref('stg_air_quality_hourly') }}

),

daily as (

    select
        location_id,
        cast(timestamp as date) as date,

        max(city_name)    as city_name,
        max(country_code) as country_code,

        count(*)             as hours_observed,
        count(european_aqi)  as aqi_hours_observed,

        avg(european_aqi) as avg_european_aqi,
        max(european_aqi) as max_european_aqi,

        avg(pm2_5) as avg_pm2_5,
        max(pm2_5) as max_pm2_5,
        avg(pm10)  as avg_pm10,
        max(pm10)  as max_pm10,

        avg(carbon_monoxide)  as avg_carbon_monoxide,
        avg(nitrogen_dioxide) as avg_nitrogen_dioxide,
        avg(ozone)            as avg_ozone

    from hourly
    group by location_id, cast(timestamp as date)

)

select
    cast(location_id as varchar) || '-' || cast(date as varchar) as air_quality_daily_id,
    location_id,
    city_name,
    country_code,
    date,
    hours_observed,
    aqi_hours_observed,
    coalesce(hours_observed >= {{ var('complete_aqi_hours') }}, false) as is_complete_aqi_day,
    avg_european_aqi,
    max_european_aqi,

    -- European AQI band (EEA bands), classified on the daily average index.
    case
        when avg_european_aqi is null then null
        when avg_european_aqi < 20  then 'good'
        when avg_european_aqi < 40  then 'fair'
        when avg_european_aqi < 60  then 'moderate'
        when avg_european_aqi < 80  then 'poor'
        when avg_european_aqi < 100 then 'very poor'
        else 'extremely poor'
    end as european_aqi_band,

    avg_pm2_5,
    max_pm2_5,
    avg_pm10,
    max_pm10,
    avg_carbon_monoxide,
    avg_nitrogen_dioxide,
    avg_ozone
from daily
