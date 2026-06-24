with source as (

    select * from {{ source('open_meteo', 'raw_forecast_daily') }}

),

deduped as (

    select
        *,
        row_number() over (
            partition by location_id, date
            order by extracted_at desc
        ) as row_num

    from source

)

select
    cast(location_id as varchar) || '-' || cast(date as varchar) as forecast_daily_id,
    cast(source_name as varchar) as source_name,
    cast(location_id as bigint) as location_id,
    cast(city_name as varchar) as city_name,
    cast(country_code as varchar) as country_code,
    cast(date as date) as date,
    cast(latitude as double) as latitude,
    cast(longitude as double) as longitude,
    cast(timezone as varchar) as timezone,
    cast(temperature_2m_max as double) as temperature_2m_max,
    cast(temperature_2m_min as double) as temperature_2m_min,
    cast(temperature_2m_mean as double) as temperature_2m_mean,
    cast(precipitation_sum as double) as precipitation_sum,
    cast(rain_sum as double) as rain_sum,
    cast(snowfall_sum as double) as snowfall_sum,
    cast(wind_speed_10m_max as double) as wind_speed_10m_max,
    cast(extracted_at as timestamptz) as extracted_at

from deduped
where row_num = 1
