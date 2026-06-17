CREATE DATABASE IF NOT EXISTS open_meteo_europe;
USE open_meteo_europe;

CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS intermediate;
CREATE SCHEMA IF NOT EXISTS marts;

CREATE TABLE IF NOT EXISTS raw.raw_locations (
    extracted_at TIMESTAMPTZ,
    location_id BIGINT,
    city_name VARCHAR,
    country VARCHAR,
    country_code VARCHAR,
    admin1 VARCHAR,
    latitude DOUBLE,
    longitude DOUBLE,
    timezone VARCHAR,
    elevation DOUBLE,
    population BIGINT
);

CREATE TABLE IF NOT EXISTS raw.raw_weather_daily (
    source_name VARCHAR,
    extracted_at TIMESTAMPTZ,
    location_id BIGINT,
    city_name VARCHAR,
    country_code VARCHAR,
    date DATE,
    latitude DOUBLE,
    longitude DOUBLE,
    timezone VARCHAR,
    temperature_2m_max DOUBLE,
    temperature_2m_min DOUBLE,
    temperature_2m_mean DOUBLE,
    precipitation_sum DOUBLE,
    rain_sum DOUBLE,
    snowfall_sum DOUBLE,
    wind_speed_10m_max DOUBLE
);

CREATE TABLE IF NOT EXISTS raw.raw_forecast_daily (
    source_name VARCHAR,
    extracted_at TIMESTAMPTZ,
    location_id BIGINT,
    city_name VARCHAR,
    country_code VARCHAR,
    date DATE,
    latitude DOUBLE,
    longitude DOUBLE,
    timezone VARCHAR,
    temperature_2m_max DOUBLE,
    temperature_2m_min DOUBLE,
    temperature_2m_mean DOUBLE,
    precipitation_sum DOUBLE,
    rain_sum DOUBLE,
    snowfall_sum DOUBLE,
    wind_speed_10m_max DOUBLE
);

CREATE TABLE IF NOT EXISTS raw.raw_air_quality_hourly (
    source_name VARCHAR,
    extracted_at TIMESTAMPTZ,
    location_id BIGINT,
    city_name VARCHAR,
    country_code VARCHAR,
    timestamp TIMESTAMP,
    latitude DOUBLE,
    longitude DOUBLE,
    timezone VARCHAR,
    pm10 DOUBLE,
    pm2_5 DOUBLE,
    carbon_monoxide DOUBLE,
    nitrogen_dioxide DOUBLE,
    ozone DOUBLE,
    european_aqi INTEGER
);
