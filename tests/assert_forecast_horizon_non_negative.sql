-- Fails if any forecast horizon is negative, which would mean the forecast
-- snapshot was recorded after the date it was predicting.

select
    forecast_accuracy_id,
    location_id,
    date,
    forecast_snapshot_date,
    forecast_horizon_days
from {{ ref('fct_forecast_accuracy') }}
where forecast_horizon_days < 0