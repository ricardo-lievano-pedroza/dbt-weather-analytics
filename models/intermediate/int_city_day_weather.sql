-- Join actual daily weather to city/location attributes.
-- Grain: location_id, date.

with weather as (

    select * from {{ ref('stg_weather_daily') }}

),

locations as (

    select * from {{ ref('stg_locations') }}

)

select
    weather.weather_daily_id,
    weather.location_id,
    weather.date,

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

    -- daily weather measures
    weather.temperature_2m_max,
    weather.temperature_2m_min,
    weather.temperature_2m_mean,
    weather.precipitation_sum,
    weather.rain_sum,
    weather.snowfall_sum,
    weather.wind_speed_10m_max,

    weather.extracted_at

from weather
left join locations
    on weather.location_id = locations.location_id
