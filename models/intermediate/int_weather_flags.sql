-- Add analytical boolean flags by combining daily weather with daily air quality.
-- Grain: location_id, date.
--
-- Thresholds (documented so downstream marts can reason about them):
--   rainy day       : precipitation_sum   >= 1 mm
--   hot day         : temperature_2m_max  >= 30 C
--   windy day       : wind_speed_10m_max  >= 38 km/h
--   poor AQI day    : max_european_aqi    >= 60 (European AQI "poor" band starts at 60)
--   comfortable day : mean temp between 18 and 26 C and none of the above adverse flags

with weather as (

    select * from {{ ref('int_city_day_weather') }}

),

air_quality as (

    select
        location_id,
        date,
        avg_european_aqi,
        max_european_aqi
    from {{ ref('int_air_quality_daily') }}

),

joined as (

    select
        weather.weather_daily_id,
        weather.location_id,
        weather.date,
        weather.city_name,
        weather.country_code,

        weather.temperature_2m_max,
        weather.temperature_2m_min,
        weather.temperature_2m_mean,
        weather.precipitation_sum,
        weather.wind_speed_10m_max,

        air_quality.avg_european_aqi,
        air_quality.max_european_aqi

    from weather
    left join air_quality
        on weather.location_id = air_quality.location_id
        and weather.date = air_quality.date

),

flagged as (

    select
        *,
        coalesce(precipitation_sum  >= 1,  false) as is_rainy_day,
        coalesce(temperature_2m_max >= 30, false) as is_hot_day,
        coalesce(wind_speed_10m_max >= 38, false) as is_windy_day,
        coalesce(max_european_aqi   >= 60, false) as is_poor_aqi_day
    from joined

)

select
    weather_daily_id,
    location_id,
    date,
    city_name,
    country_code,

    temperature_2m_max,
    temperature_2m_min,
    temperature_2m_mean,
    precipitation_sum,
    wind_speed_10m_max,
    avg_european_aqi,
    max_european_aqi,

    is_rainy_day,
    is_hot_day,
    is_windy_day,
    is_poor_aqi_day,

    coalesce(
        not is_rainy_day
        and not is_hot_day
        and not is_windy_day
        and not is_poor_aqi_day
        and temperature_2m_mean >= 18
        and temperature_2m_mean <= 26,
        false
    ) as is_comfortable_day

from flagged
