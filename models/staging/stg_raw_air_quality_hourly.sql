with source as (

    select * from {{ source('weather_local', 'raw_air_quality_hourly') }}

)

select
    cast(source_name as varchar) as source_name,
    cast(extracted_at as timestamp) as extracted_at,
    cast(location_id as bigint) as location_id,
    cast(city_name as varchar) as city_name,
    cast(country_code as varchar) as country_code,
    cast(timestamp as timestamp) as timestamp,
    cast(latitude as double) as latitude,
    cast(longitude as double) as longitude,
    cast(timezone as varchar) as timezone,
    cast(pm10 as double) as pm10,
    cast(pm2_5 as double) as pm2_5,
    cast(carbon_monoxide as double) as carbon_monoxide,
    cast(nitrogen_dioxide as double) as nitrogen_dioxide,
    cast(ozone as double) as ozone,
    cast(european_aqi as bigint) as european_aqi

from source
