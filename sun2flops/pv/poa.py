"""Plane-of-array irradiance and cell temperature calculations."""

import pandas as pd
from pvlib import irradiance, solarposition, temperature

from sun2flops.config import PVConfig, SiteConfig


def add_poa_irradiance(
    weather: pd.DataFrame,
    site: SiteConfig,
    pv: PVConfig,
) -> pd.DataFrame:
    """
    Add POA irradiance and cell temperature to weather data.

    Parameters
    ----------
    weather : pd.DataFrame
        Weather data with ghi, dni, dhi, temp_air, wind_speed
    site : SiteConfig
        Site location configuration
    pv : PVConfig
        PV system configuration

    Returns
    -------
    pd.DataFrame
        Weather data with added columns:
        - solar_zenith, solar_azimuth
        - poa_global
        - temp_cell
    """
    df = weather.copy()

    # Compute solar position
    solpos = solarposition.get_solarposition(
        df.index,
        site.latitude,
        site.longitude,
        altitude=site.altitude_m or 0,
    )

    df['solar_zenith'] = solpos['apparent_zenith']
    df['solar_azimuth'] = solpos['azimuth']

    # Compute angle of incidence
    aoi = irradiance.aoi(
        surface_tilt=pv.surface_tilt_deg,
        surface_azimuth=pv.surface_azimuth_deg,
        solar_zenith=solpos['apparent_zenith'],
        solar_azimuth=solpos['azimuth'],
    )

    # Get extraterrestrial radiation for decomposition models
    dni_extra = irradiance.get_extra_radiation(df.index)

    # Compute POA irradiance components using Perez model
    poa = irradiance.get_total_irradiance(
        surface_tilt=pv.surface_tilt_deg,
        surface_azimuth=pv.surface_azimuth_deg,
        solar_zenith=solpos['apparent_zenith'],
        solar_azimuth=solpos['azimuth'],
        dni=df['dni'],
        ghi=df['ghi'],
        dhi=df['dhi'],
        dni_extra=dni_extra,
        airmass=None,  # Will be calculated internally
        albedo=df.get('albedo', 0.2),  # Default ground albedo
        model='isotropic',  # Simpler model, can upgrade to 'perez' later
    )

    df['poa_global'] = poa['poa_global']
    df['poa_direct'] = poa['poa_direct']
    df['poa_diffuse'] = poa['poa_diffuse']

    # Compute cell temperature using SAPM model
    # Using 'open_rack_glass_glass' as default module type
    temp_params = temperature.TEMPERATURE_MODEL_PARAMETERS['sapm']['open_rack_glass_glass']

    df['temp_cell'] = temperature.sapm_cell(
        poa_global=df['poa_global'],
        temp_air=df['temp_air'],
        wind_speed=df['wind_speed'],
        a=temp_params['a'],
        b=temp_params['b'],
        deltaT=temp_params['deltaT'],
    )

    return df
