-- Fails if any row contains temperature values outside physically plausible
-- global bounds (-90 °C to 60 °C) or if max < min (impossible range).

select
    weather_daily_id,
    location_id,
    date,
    temperature_2m_max,
    temperature_2m_min
from {{ ref('fct_city_weather_day') }}
where
    temperature_2m_max > 60
    or temperature_2m_min < -90
    or temperature_2m_max < temperature_2m_min