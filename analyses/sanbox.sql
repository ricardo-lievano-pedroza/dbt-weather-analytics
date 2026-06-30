select * from {{ ref('fct_forecast_accuracy') }} 
where city_name = 'Brussels' 