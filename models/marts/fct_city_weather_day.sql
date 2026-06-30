-- One row per city per day of observed weather, combining all weather measures,
-- analytical flags and air quality. Grain: location_id, date.

with weather as (

    select * from {{ ref('int_city_day_weather') }}

),

flags as (

    select
        weather_daily_id,
        is_rainy_day,
        is_hot_day,
        is_windy_day,
        is_freezing_day,
        is_snowy_day,
        is_poor_aqi_day,
        is_comfortable_day
    from {{ ref('int_weather_flags') }}

),

air_quality as (

    select * from {{ ref('int_air_quality_daily') }}

),

final as (

    select
        -- keys
        weather.weather_daily_id,
        weather.location_id,
        weather.date,

        -- location (FK to dim_location)
        weather.city_name,
        weather.country,
        weather.country_code,
        weather.admin1,
        weather.latitude,
        weather.longitude,
        weather.timezone,
        weather.elevation,
        weather.population,

        -- weather measures
        weather.temperature_2m_max,
        weather.temperature_2m_min,
        weather.temperature_2m_mean,
        weather.temperature_range,
        weather.precipitation_sum,
        weather.rain_sum,
        weather.snowfall_sum,
        weather.wind_speed_10m_max,

        -- analytical flags
        flags.is_rainy_day,
        flags.is_hot_day,
        flags.is_windy_day,
        flags.is_freezing_day,
        flags.is_snowy_day,
        flags.is_poor_aqi_day,
        flags.is_comfortable_day,

        -- air quality
        air_quality.avg_european_aqi,
        air_quality.max_european_aqi,
        air_quality.european_aqi_band,
        air_quality.is_complete_aqi_day,
        air_quality.avg_pm2_5,
        air_quality.max_pm2_5,
        air_quality.avg_pm10,
        air_quality.max_pm10,
        air_quality.avg_carbon_monoxide,
        air_quality.avg_nitrogen_dioxide,
        air_quality.avg_ozone,

        weather.extracted_at

    from weather
    left join flags
        on weather.weather_daily_id = flags.weather_daily_id
    left join air_quality
        on weather.location_id = air_quality.location_id
        and weather.date = air_quality.date

)

select * from final