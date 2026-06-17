with source as (

    select * from {{ source('weather_local', 'raw_locations') }}

)

select
    cast(location_id as bigint) as location_id,
    cast(city_name as varchar) as city_name,
    cast(country as varchar) as country,
    cast(country_code as varchar) as country_code,
    cast(admin1 as varchar) as admin1,
    cast(latitude as double) as latitude,
    cast(longitude as double) as longitude,
    cast(timezone as varchar) as timezone,
    cast(elevation as double) as elevation,
    cast(population as bigint) as population,
    cast(extracted_at as timestamp) as extracted_at

from source
