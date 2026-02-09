from __future__ import annotations

import pandas as pd

from sun2flops.config.models import PVConfig


def pv_power_on_bus_w(
    poa_df: pd.DataFrame,
    pv: PVConfig,
) -> pd.Series:
    """
    PVWatts DC estimate at MPP:
      pdc = kw*1000*(poa/1000)*(1 + gamma*(temp_cell-25))
    clamp >=0, then apply mppt_eff and dc_wiring_eff.
    Returns P_pv_bus_w series.
    """
    poa = poa_df["poa_global"]
    temp_cell = poa_df["temp_cell"]
    pdc = (
        pv.dc_nameplate_kw
        * 1000.0
        * (poa / 1000.0)
        * (1 + pv.gamma_pdc_per_c * (temp_cell - 25.0))
    )
    pdc = pdc.clip(lower=0)
    p_bus = pdc * pv.mppt_eff * pv.dc_wiring_eff
    return pd.Series(p_bus, index=poa_df.index, name="P_pv_bus_w")
