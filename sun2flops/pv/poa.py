from __future__ import annotations

import pandas as pd
import pvlib

from sun2flops.config.models import SiteConfig, PVConfig


def add_poa_and_cell_temp(
    weather_df: pd.DataFrame,
    site: SiteConfig,
    pv: PVConfig,
) -> pd.DataFrame:
    """
    Input columns: ghi, dni, dhi, temp_air, wind_speed
    Output adds: solar_zenith, solar_azimuth, poa_global, temp_cell
    """
    location = pvlib.location.Location(
        latitude=site.latitude,
        longitude=site.longitude,
        tz=site.timezone,
        altitude=site.altitude_m,
        name=site.name,
    )
    times = weather_df.index
    solar_pos = location.get_solarposition(times)
    poa = pvlib.irradiance.get_total_irradiance(
        surface_tilt=pv.surface_tilt_deg,
        surface_azimuth=pv.surface_azimuth_deg,
        dni=weather_df["dni"],
        ghi=weather_df["ghi"],
        dhi=weather_df["dhi"],
        solar_zenith=solar_pos["apparent_zenith"],
        solar_azimuth=solar_pos["azimuth"],
    )
    temp_cell = pvlib.temperature.sapm_cell(
        poa_global=poa["poa_global"],
        temp_air=weather_df["temp_air"],
        wind_speed=weather_df["wind_speed"],
    )
    out = weather_df.copy()
    out["solar_zenith"] = solar_pos["apparent_zenith"]
    out["solar_azimuth"] = solar_pos["azimuth"]
    out["poa_global"] = poa["poa_global"]
    out["temp_cell"] = temp_cell
    return out
