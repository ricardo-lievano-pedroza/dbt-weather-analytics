{{ config(materialized='view') }}

-- One row per city. Current observed snapshot + today/tomorrow forecast
-- + 7-day visit scores. Evaluated at query time (view) so current_date is live.

with latest_observed as (

    select *
    from {{ ref('fct_city_weather_day') }}
    qualify row_number() over (partition by location_id order by date desc) = 1

),

upcoming as (

    select *
    from {{ ref('fct_forecast_accuracy') }}
    where date >= current_date

),

today_fcst as (

    select *
    from {{ ref('fct_forecast_accuracy') }}
    where date = current_date

),

tomorrow_fcst as (

    select *
    from {{ ref('fct_forecast_accuracy') }}
    where date = current_date + interval '1 day'

),

score_agg as (

    select
        location_id,

        round(avg(
            0.40 * (1 - least(abs(coalesce(fcst_temperature_2m_mean, 22.0) - 22.0) / 20.0, 1.0))
            + 0.35 * (1 - least(coalesce(fcst_precipitation_sum,   0) / 20.0, 1.0))
            + 0.25 * (1 - least(coalesce(fcst_wind_speed_10m_max,  0) / 80.0, 1.0))
        ) * 100, 1) as visit_score,

        round(avg(
            1 - least(abs(coalesce(fcst_temperature_2m_mean, 22.0) - 22.0) / 20.0, 1.0)
        ) * 100, 1) as avg_temp_comfort_score,

        round(avg(
            1 - least(coalesce(fcst_precipitation_sum, 0) / 20.0, 1.0)
        ) * 100, 1) as avg_rain_score,

        round(avg(
            1 - least(coalesce(fcst_wind_speed_10m_max, 0) / 80.0, 1.0)
        ) * 100, 1) as avg_wind_score

    from upcoming
    group by location_id

),

final as (

    select
        -- location
        l.location_id,
        l.city_name,
        l.country,
        l.country_code,
        l.latitude,
        l.longitude,
        l.timezone,
        l.elevation,
        l.population,

        -- latest observed
        o.date                 as last_observed_date,
        o.temperature_2m_max   as obs_temp_max,
        o.temperature_2m_min   as obs_temp_min,
        o.temperature_2m_mean  as obs_temp_mean,
        o.precipitation_sum    as obs_precip,
        o.wind_speed_10m_max   as obs_wind,
        o.is_rainy_day,
        o.is_hot_day,
        o.is_windy_day,
        o.is_freezing_day,
        o.is_snowy_day,
        o.is_poor_aqi_day,
        o.is_comfortable_day,
        o.avg_european_aqi,
        o.max_european_aqi,
        o.european_aqi_band,

        -- today's forecast
        t.fcst_temperature_2m_max   as today_temp_max,
        t.fcst_temperature_2m_min   as today_temp_min,
        t.fcst_temperature_2m_mean  as today_temp_mean,
        t.fcst_precipitation_sum    as today_precip,
        t.fcst_wind_speed_10m_max   as today_wind,

        -- tomorrow's forecast
        tm.fcst_temperature_2m_max  as tomorrow_temp_max,
        tm.fcst_temperature_2m_min  as tomorrow_temp_min,
        tm.fcst_precipitation_sum   as tomorrow_precip,

        -- composite visit score (7-day horizon)
        vs.visit_score,
        vs.avg_temp_comfort_score,
        vs.avg_rain_score,
        vs.avg_wind_score,

        case
            when o.is_comfortable_day             then 'Comfortable'
            when o.is_hot_day                     then 'Hot'
            when o.is_rainy_day                   then 'Rainy'
            when o.is_windy_day                   then 'Windy'
            when o.is_freezing_day                then 'Freezing'
            when o.is_snowy_day                   then 'Snowy'
            else 'Mixed'
        end as condition_label,

        case
            when coalesce(vs.visit_score, 0) >= 75 then
                case
                    when o.is_comfortable_day             then 'warm, dry, comfortable'
                    when not o.is_rainy_day and not o.is_windy_day then 'clear skies, light wind'
                    else 'good overall conditions'
                end
            when coalesce(vs.visit_score, 0) >= 50 then 'decent conditions expected'
            else 'challenging weather ahead'
        end as recommendation_reason

    from {{ ref('dim_location') }} l
    left join latest_observed o  on l.location_id = o.location_id
    left join today_fcst       t  on l.location_id = t.location_id
    left join tomorrow_fcst    tm on l.location_id = tm.location_id
    left join score_agg        vs on l.location_id = vs.location_id

)

select * from final
