-- Add analytical boolean flags by combining daily weather with daily air quality.
-- Grain: location_id, date.
--
-- Thresholds are defined as project vars (see dbt_project.yml) so they live in a
-- single, self-documenting place:
--   rainy day       : precipitation_sum   >= var('rainy_precip_mm')
--   hot day         : temperature_2m_max  >= var('hot_temp_c')
--   windy day       : wind_speed_10m_max  >= var('windy_kmh')
--   freezing day    : temperature_2m_min  <= var('freezing_temp_c')
--   snowy day       : snowfall_sum         > 0
--   poor AQI day    : max_european_aqi    >= var('poor_aqi')
--   comfortable day : mean temp within [comfortable_temp_min_c, comfortable_temp_max_c]
--                     and none of the adverse flags

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
        weather.snowfall_sum,
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
        coalesce(precipitation_sum  >= {{ var('rainy_precip_mm') }}, false) as is_rainy_day,
        coalesce(temperature_2m_max >= {{ var('hot_temp_c') }},      false) as is_hot_day,
        coalesce(wind_speed_10m_max >= {{ var('windy_kmh') }},       false) as is_windy_day,
        coalesce(temperature_2m_min <= {{ var('freezing_temp_c') }}, false) as is_freezing_day,
        coalesce(snowfall_sum        > 0,                            false) as is_snowy_day,
        coalesce(max_european_aqi   >= {{ var('poor_aqi') }},        false) as is_poor_aqi_day
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
    snowfall_sum,
    wind_speed_10m_max,
    avg_european_aqi,
    max_european_aqi,

    is_rainy_day,
    is_hot_day,
    is_windy_day,
    is_freezing_day,
    is_snowy_day,
    is_poor_aqi_day,

    coalesce(
        not is_rainy_day
        and not is_hot_day
        and not is_windy_day
        and not is_freezing_day
        and not is_snowy_day
        and not is_poor_aqi_day
        and temperature_2m_mean >= {{ var('comfortable_temp_min_c') }}
        and temperature_2m_mean <= {{ var('comfortable_temp_max_c') }},
        false
    ) as is_comfortable_day

from flagged
