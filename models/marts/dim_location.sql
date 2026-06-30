-- One row per tracked city. Source of truth for location attributes
-- referenced by all fact tables. Grain: location_id.

with source as (

    select * from {{ ref('stg_locations') }}

)

select
    location_id,
    city_name,
    country,
    country_code,
    admin1,
    latitude,
    longitude,
    timezone,
    elevation,
    population
from source