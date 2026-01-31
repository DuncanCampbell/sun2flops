"""PV DC power calculation at maximum power point."""

import numpy as np
import pandas as pd

from sun2flops.config import PVConfig


def pv_dc_power_mpp(
    poa_df: pd.DataFrame,
    pv: PVConfig,
) -> pd.Series:
    """
    Calculate PV power on DC bus after MPPT and wiring losses.

    Uses PVWatts DC model for initial implementation.

    Parameters
    ----------
    poa_df : pd.DataFrame
        DataFrame with 'poa_global' and 'temp_cell' columns
    pv : PVConfig
        PV system configuration

    Returns
    -------
    pd.Series
        PV power on DC bus in watts
    """
    if pv.dc_model == "pvwatts":
        return _pvwatts_dc(poa_df, pv)
    elif pv.dc_model == "singlediode":
        raise NotImplementedError("Single-diode model not yet implemented")
    else:
        raise ValueError(f"Unknown DC model: {pv.dc_model}")


def _pvwatts_dc(
    poa_df: pd.DataFrame,
    pv: PVConfig,
) -> pd.Series:
    """
    PVWatts DC power model.

    P_dc = P_dc0 * (G_poa / G_ref) * (1 + gamma * (T_cell - T_ref))

    Where:
    - P_dc0 = nameplate DC power
    - G_poa = plane-of-array irradiance
    - G_ref = reference irradiance (1000 W/m²)
    - gamma = temperature coefficient (negative, typically -0.003 to -0.005)
    - T_cell = cell temperature
    - T_ref = reference temperature (25°C)
    """
    # Reference conditions
    g_ref = 1000.0  # W/m²
    t_ref = 25.0  # °C

    # Nameplate power in watts
    p_dc0_w = pv.dc_nameplate_kw * 1000.0

    # Get irradiance and temperature
    poa_global = poa_df['poa_global'].values
    temp_cell = poa_df['temp_cell'].values

    # PVWatts DC power calculation
    # Temperature derating factor
    temp_factor = 1.0 + pv.gamma_pdc_per_c * (temp_cell - t_ref)

    # DC power at MPP
    pdc_w = p_dc0_w * (poa_global / g_ref) * temp_factor

    # Clamp to non-negative
    pdc_w = np.maximum(pdc_w, 0.0)

    # Apply MPPT and wiring efficiency
    pdc_bus_w = pdc_w * pv.mppt_eff * pv.dc_wiring_eff

    return pd.Series(pdc_bus_w, index=poa_df.index, name='pv_dc_bus_w')
