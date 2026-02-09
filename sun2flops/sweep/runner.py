from __future__ import annotations

from dataclasses import replace
import pandas as pd

from sun2flops.config.models import FullConfig
from sun2flops.sim.engine import run_simulation


def run_sweep(
    weather_df: pd.DataFrame,
    cfg: FullConfig,
) -> pd.DataFrame:
    """
    Uses cfg.sweep.pv_kw_list and cfg.sweep.batt_kwh_list.
    Runs simulation on cfg.sweep.year_for_sweep by default (fast).
    Returns tidy df:
      pv_kw, batt_kwh, total_flops, utilization, pv_curtailment_fraction, unmet_energy_wh, ...
    """
    rows = []
    for pv_kw in cfg.sweep.pv_kw_list:
        for batt_kwh in cfg.sweep.batt_kwh_list:
            pv_cfg = replace(cfg.pv, dc_nameplate_kw=pv_kw)
            batt_cfg = replace(cfg.battery, energy_capacity_kwh=batt_kwh)
            sweep_cfg = replace(cfg, pv=pv_cfg, battery=batt_cfg)
            _, metrics = run_simulation(
                weather_df,
                sweep_cfg,
                single_year=cfg.sweep.year_for_sweep,
            )
            row = {
                "pv_kw": pv_kw,
                "batt_kwh": batt_kwh,
            }
            row.update(metrics)
            rows.append(row)

    return pd.DataFrame(rows)
