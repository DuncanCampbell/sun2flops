from __future__ import annotations

import pandas as pd

from sun2flops.config.models import FullConfig


def compute_metrics(df: pd.DataFrame, cfg: FullConfig) -> dict:
    dt_hours = cfg.sim.dt_min / 60.0
    dt_s = cfg.sim.dt_min * 60.0

    total_flops = df["flops_step"].sum()
    total_seconds = len(df) * dt_s
    flops_capacity = cfg.gpu.flops_peak_per_gpu * cfg.gpu.n_gpus * total_seconds
    utilization = total_flops / flops_capacity if flops_capacity > 0 else 0.0

    pv_energy_wh = df["P_pv_bus_w"].sum() * dt_hours
    pv_curtailed_energy_wh = df["pv_curtailed_w"].sum() * dt_hours
    pv_curtailment_fraction = (
        pv_curtailed_energy_wh / pv_energy_wh if pv_energy_wh > 0 else 0.0
    )

    unmet_energy_wh = df["unmet_w"].sum() * dt_hours
    unserved_hours = (df["unmet_w"] > 0).sum() * dt_hours

    return {
        "total_flops": total_flops,
        "utilization": utilization,
        "pv_energy_wh": pv_energy_wh,
        "pv_curtailed_energy_wh": pv_curtailed_energy_wh,
        "pv_curtailment_fraction": pv_curtailment_fraction,
        "unmet_energy_wh": unmet_energy_wh,
        "unserved_hours": unserved_hours,
    }
