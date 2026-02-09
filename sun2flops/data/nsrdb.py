from __future__ import annotations

from pathlib import Path
import inspect
import os
import pandas as pd
import pvlib

from sun2flops.config.models import SiteConfig, WeatherConfig
from sun2flops.data.io import load_dataframe, preferred_extension, save_dataframe


REQUIRED_COLUMNS = ["ghi", "dni", "dhi", "temp_air", "wind_speed"]


def _resolve_nsrdb_fetcher():
    if hasattr(pvlib.iotools, "get_nsrdb"):
        return pvlib.iotools.get_nsrdb
    if hasattr(pvlib.iotools, "get_psm4"):
        return pvlib.iotools.get_psm4
    if hasattr(pvlib.iotools, "get_psm3"):
        return pvlib.iotools.get_psm3
    try:
        from pvlib.iotools.psm4 import get_psm4  # type: ignore
    except Exception:
        get_psm4 = None
    try:
        from pvlib.iotools.psm3 import get_psm3  # type: ignore
    except Exception as exc:  # pragma: no cover - import path depends on pvlib version
        if get_psm4 is not None:
            return get_psm4
        raise ImportError(
            "pvlib does not provide NSRDB download helpers. "
            "Install a pvlib release that exposes get_nsrdb, get_psm4, "
            "or get_psm3, or use a different weather data source."
        ) from exc
    return get_psm3


def _call_nsrdb_fetcher(fetcher, **kwargs):
    signature = inspect.signature(fetcher)
    filtered = {key: value for key, value in kwargs.items() if key in signature.parameters}
    return fetcher(**filtered)


def _cache_key(site: SiteConfig, year: int, weather: WeatherConfig) -> str:
    lat = round(site.latitude, 3)
    lon = round(site.longitude, 3)
    return f"nsrdb_{lat}_{lon}_{year}_{weather.interval_min}min_ld{int(weather.leap_day)}"


def _cache_path(site: SiteConfig, year: int, weather: WeatherConfig) -> Path:
    ext = preferred_extension()
    key = _cache_key(site, year, weather)
    return Path(weather.cache_dir) / f"{key}{ext}"


def _ensure_timezone(df: pd.DataFrame, timezone: str) -> pd.DataFrame:
    if df.index.tz is None:
        df.index = df.index.tz_localize(timezone)
    else:
        df.index = df.index.tz_convert(timezone)
    return df


def _select_columns(df: pd.DataFrame) -> pd.DataFrame:
    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(f"NSRDB response missing columns: {missing}")
    return df[REQUIRED_COLUMNS].copy()


def fetch_nsrdb_year(
    site: SiteConfig,
    year: int,
    weather: WeatherConfig,
) -> tuple[pd.DataFrame, dict]:
    """
    Fetch one year of NSRDB data at 30-min resolution via pvlib helpers (PSM4/PSM3).
    Cache to parquet/csv in weather.cache_dir.

    Return:
      df index tz-aware local time
      columns: ghi, dni, dhi, temp_air, wind_speed
      meta dict
    """
    cache_path = _cache_path(site, year, weather)
    if cache_path.exists():
        df = load_dataframe(cache_path)
        df = _ensure_timezone(df, site.timezone)
        return df, {}

    api_key = weather.api_key or os.getenv("NSRDB_API_KEY")
    email = weather.email or os.getenv("NSRDB_EMAIL")
    if not api_key or not email:
        raise ValueError("NSRDB api_key/email missing; set in config or env")

    fetcher = _resolve_nsrdb_fetcher()
    df, meta = _call_nsrdb_fetcher(
        fetcher,
        latitude=site.latitude,
        longitude=site.longitude,
        names=year,
        interval=weather.interval_min,
        leap_day=weather.leap_day,
        api_key=api_key,
        email=email,
        map_variables=True,
    )
    df = _select_columns(df)
    df = _ensure_timezone(df, site.timezone)
    save_dataframe(df, cache_path)
    return df, meta


def load_weather_range(
    site: SiteConfig,
    weather: WeatherConfig,
) -> pd.DataFrame:
    """
    Concatenate all requested years.
    Enforce 30-min regularity and tz-awareness.
    """
    frames = []
    for year in weather.years:
        df, _ = fetch_nsrdb_year(site, year, weather)
        frames.append(df)

    if not frames:
        raise ValueError("No weather data fetched")

    combined = pd.concat(frames).sort_index()
    combined = _ensure_timezone(combined, site.timezone)

    if weather.interval_min != 30:
        raise ValueError("Weather interval must be 30 minutes")
    combined = combined.asfreq("30min")
    return combined
