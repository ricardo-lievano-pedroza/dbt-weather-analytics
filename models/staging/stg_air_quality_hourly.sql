with source as (

    select * from {{ source('open_meteo', 'raw_air_quality_hourly') }}

),

deduped as (

    select
        *,
        row_number() over (
            partition by location_id, timestamp
            order by extracted_at desc
        ) as row_num

    from source

)

select
    cast(location_id as varchar) || '-' || cast(timestamp as varchar) as air_quality_hourly_id,
    cast(source_name as varchar) as source_name,
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
    cast(european_aqi as integer) as european_aqi,
    cast(extracted_at as timestamptz) as extracted_at

from deduped
where row_num = 1
