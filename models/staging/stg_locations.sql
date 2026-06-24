with source as (

    select * from {{ source('open_meteo', 'raw_locations') }}

),

deduped as (

    select
        *,
        row_number() over (
            partition by location_id
            order by extracted_at desc
        ) as row_num

    from source

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
    cast(extracted_at as timestamptz) as extracted_at

from deduped
where row_num = 1
