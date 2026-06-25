-- Roll hourly air quality measurements up to one row per city per local date.
-- Grain: location_id, date.

with hourly as (

    select * from {{ ref('stg_air_quality_hourly') }}

),

daily as (

    select
        location_id,
        cast(timestamp as date) as date,

        max(city_name)    as city_name,
        max(country_code) as country_code,

        count(*) as hours_observed,

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
    avg_european_aqi,
    max_european_aqi,
    avg_pm2_5,
    max_pm2_5,
    avg_pm10,
    max_pm10,
    avg_carbon_monoxide,
    avg_nitrogen_dioxide,
    avg_ozone
from daily
