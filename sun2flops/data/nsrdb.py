"""NSRDB weather data fetching and caching via pvlib."""

import hashlib
import os
from pathlib import Path
from typing import Tuple

import pandas as pd

from sun2flops.config import SiteConfig, WeatherConfig


def _cache_key(lat: float, lon: float, year: int, interval: int, leap_day: bool) -> str:
    """Generate cache key for weather data."""
    key_str = f"{lat:.4f}_{lon:.4f}_{year}_{interval}_{leap_day}"
    return hashlib.md5(key_str.encode()).hexdigest()[:12]


def _cache_path(cache_dir: str, lat: float, lon: float, year: int,
                interval: int, leap_day: bool) -> Path:
    """Get cache file path for weather data."""
    key = _cache_key(lat, lon, year, interval, leap_day)
    return Path(cache_dir) / f"nsrdb_{year}_{key}.parquet"


def fetch_nsrdb_year(
    site: SiteConfig,
    year: int,
    interval_min: int,
    leap_day: bool,
    api_key: str,
    email: str,
    cache_dir: str,
) -> Tuple[pd.DataFrame, dict]:
    """
    Fetch and cache historical weather from NSRDB via pvlib.

    Parameters
    ----------
    site : SiteConfig
        Site location configuration
    year : int
        Year to fetch
    interval_min : int
        Time interval in minutes (must be 30)
    leap_day : bool
        Whether to include leap day
    api_key : str
        NSRDB API key
    email : str
        Email for NSRDB API
    cache_dir : str
        Directory for caching data

    Returns
    -------
    Tuple[pd.DataFrame, dict]
        DataFrame indexed by local time with ghi, dni, dhi, temp_air, wind_speed
        and metadata dict
    """
    from pvlib.iotools import get_psm3

    # Ensure cache directory exists
    Path(cache_dir).mkdir(parents=True, exist_ok=True)

    cache_file = _cache_path(cache_dir, site.latitude, site.longitude,
                             year, interval_min, leap_day)
    meta_file = cache_file.with_suffix('.meta.json')

    # Check cache
    if cache_file.exists() and meta_file.exists():
        df = pd.read_parquet(cache_file)
        import json
        with open(meta_file, 'r') as f:
            meta = json.load(f)
        return df, meta

    # Fetch from NSRDB
    df, meta = get_psm3(
        latitude=site.latitude,
        longitude=site.longitude,
        api_key=api_key,
        email=email,
        names=str(year),
        interval=interval_min,
        leap_day=leap_day,
        attributes=[
            'ghi', 'dni', 'dhi',
            'air_temperature', 'wind_speed',
            'surface_albedo'
        ],
        map_variables=True,  # Use standard pvlib variable names
    )

    # Rename columns to standard names
    column_map = {
        'ghi': 'ghi',
        'dni': 'dni',
        'dhi': 'dhi',
        'temp_air': 'temp_air',
        'wind_speed': 'wind_speed',
        'albedo': 'albedo',
    }

    # Ensure we have the expected columns
    available_cols = {}
    for new_name, old_name in column_map.items():
        if old_name in df.columns:
            available_cols[old_name] = new_name
        elif new_name in df.columns:
            available_cols[new_name] = new_name

    df = df.rename(columns=available_cols)

    # Convert index to local timezone
    if site.timezone:
        df.index = df.index.tz_convert(site.timezone)

    # Cache the data
    df.to_parquet(cache_file)

    # Convert meta to serializable format and cache
    import json
    meta_serializable = {k: str(v) if not isinstance(v, (int, float, str, bool, type(None)))
                         else v for k, v in meta.items()}
    with open(meta_file, 'w') as f:
        json.dump(meta_serializable, f)

    return df, meta


def load_weather_range(
    site: SiteConfig,
    wcfg: WeatherConfig,
    api_key: str,
    email: str,
) -> pd.DataFrame:
    """
    Load weather data for a range of years.

    Parameters
    ----------
    site : SiteConfig
        Site location configuration
    wcfg : WeatherConfig
        Weather configuration with years range
    api_key : str
        NSRDB API key
    email : str
        Email for NSRDB API

    Returns
    -------
    pd.DataFrame
        Concatenated weather data for all years
    """
    dfs = []

    for year in wcfg.years:
        df, _ = fetch_nsrdb_year(
            site=site,
            year=year,
            interval_min=wcfg.interval_min,
            leap_day=wcfg.leap_day,
            api_key=api_key,
            email=email,
            cache_dir=wcfg.cache_dir,
        )
        dfs.append(df)

    # Concatenate and sort
    result = pd.concat(dfs, axis=0)
    result = result.sort_index()

    # Verify regular 30-min frequency
    expected_freq = pd.Timedelta(minutes=wcfg.interval_min)
    time_diffs = result.index.to_series().diff().dropna()

    if not (time_diffs == expected_freq).all():
        # Check for DST transitions and other expected irregularities
        irregular = time_diffs[time_diffs != expected_freq]
        # Allow DST transitions (23h or 25h gaps once per year)
        non_dst = irregular[~irregular.isin([pd.Timedelta(hours=1),
                                              pd.Timedelta(hours=0.5),
                                              pd.Timedelta(minutes=90)])]
        if len(non_dst) > len(wcfg.years) * 2:  # Allow some irregularities
            raise ValueError(
                f"Weather data does not have regular {wcfg.interval_min}-min frequency. "
                f"Found {len(non_dst)} irregular intervals."
            )

    return result


def generate_synthetic_weather(
    site: SiteConfig,
    year: int = 2021,
    interval_min: int = 30,
) -> pd.DataFrame:
    """
    Generate synthetic weather data for testing when NSRDB is not available.

    Parameters
    ----------
    site : SiteConfig
        Site location configuration
    year : int
        Year to generate
    interval_min : int
        Time interval in minutes

    Returns
    -------
    pd.DataFrame
        Synthetic weather data
    """
    import numpy as np
    from pvlib import solarposition

    # Create time index
    tz = site.timezone or 'UTC'
    start = pd.Timestamp(f'{year}-01-01 00:00', tz=tz)
    end = pd.Timestamp(f'{year}-12-31 23:30', tz=tz)
    times = pd.date_range(start, end, freq=f'{interval_min}min')

    # Get solar position
    solpos = solarposition.get_solarposition(
        times, site.latitude, site.longitude,
        altitude=site.altitude_m or 0
    )

    # Generate clear-sky-like irradiance with some variability
    zenith = solpos['apparent_zenith'].values
    cos_zen = np.cos(np.radians(zenith))
    cos_zen = np.clip(cos_zen, 0, 1)

    # Simple clear sky model
    dni_clear = 1000 * cos_zen ** 0.5
    dni_clear = np.where(cos_zen > 0.05, dni_clear, 0)

    # Add some cloud variability
    np.random.seed(42 + year)
    cloud_factor = 0.5 + 0.5 * np.random.random(len(times))
    cloud_factor = np.convolve(cloud_factor, np.ones(6)/6, mode='same')  # Smooth

    dni = dni_clear * cloud_factor
    ghi = dni * cos_zen + 100 * cos_zen  # Simplified diffuse
    ghi = np.clip(ghi, 0, 1200)
    dhi = ghi - dni * cos_zen
    dhi = np.clip(dhi, 0, 500)

    # Temperature: seasonal + diurnal variation
    day_of_year = times.dayofyear
    hour_of_day = times.hour + times.minute / 60

    # Seasonal component (warmer in summer)
    temp_seasonal = 15 + 15 * np.sin(2 * np.pi * (day_of_year - 80) / 365)
    # Diurnal component
    temp_diurnal = 5 * np.sin(2 * np.pi * (hour_of_day - 6) / 24)
    temp_air = temp_seasonal + temp_diurnal + np.random.randn(len(times)) * 2

    # Wind speed
    wind_speed = 3 + 2 * np.random.random(len(times))

    df = pd.DataFrame({
        'ghi': ghi,
        'dni': dni,
        'dhi': dhi,
        'temp_air': temp_air,
        'wind_speed': wind_speed,
    }, index=times)

    return df
