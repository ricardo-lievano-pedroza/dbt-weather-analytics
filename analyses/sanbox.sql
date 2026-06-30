select count(*) from {{ ref('fct_city_weather_day') }} 
where temperature_2m_min is null