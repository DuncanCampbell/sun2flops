from __future__ import annotations

import pandas as pd

from sun2flops.battery.model import step_battery
from sun2flops.config.models import FullConfig, validate_config
from sun2flops.control.governor import governor_target_power_w
from sun2flops.control.solar_times import seconds_to_next_sunrise
from sun2flops.gpu.model import gpu_flops_step, gpu_power_from_u_w, gpu_u_from_power
from sun2flops.pv.dc_power import pv_power_on_bus_w
from sun2flops.pv.poa import add_poa_and_cell_temp
from sun2flops.sim.metrics import compute_metrics


def run_simulation(
    weather_df: pd.DataFrame,
    cfg: FullConfig,
    *,
    single_year: int | None = None,
) -> tuple[pd.DataFrame, dict]:
    """
    If single_year provided, filter weather_df to that year before running.
    Returns:
      timeseries df with columns:
        P_pv_bus_w
        P_gpu_req_w
        P_gpu_served_w
        P_batt_bus_w
        soc
        pv_curtailed_w
        curtailed_w
        unmet_w
        flops_step
        sec_to_sunrise (optional for debugging)
      metrics dict
    """
    validate_config(cfg)

    df = weather_df.copy()
    if single_year is not None:
        df = df[df.index.year == single_year]

    poa_df = add_poa_and_cell_temp(df, cfg.site, cfg.pv)
    p_pv_bus = pv_power_on_bus_w(poa_df, cfg.pv)

    sec_to_sunrise = seconds_to_next_sunrise(df.index, cfg.site)

    dt_hours = cfg.sim.dt_min / 60.0
    dt_s = cfg.sim.dt_min * 60.0

    soc = cfg.battery.soc_init
    p_prev = 0.0

    records = []
    for ts in df.index:
        p_pv = float(p_pv_bus.loc[ts])
        sec_to = float(sec_to_sunrise.loc[ts])

        if cfg.governor.enabled:
            p_gpu_req = governor_target_power_w(
                soc=soc,
                sec_to_sunrise=sec_to,
                gpu=cfg.gpu,
                batt=cfg.battery,
                gov=cfg.governor,
                p_prev_w=p_prev,
            )
        else:
            p_gpu_req = gpu_power_from_u_w(1.0, cfg.gpu)

        p_gpu_served = p_gpu_req
        unmet = 0.0
        pv_curtailed = 0.0

        surplus = p_pv - p_gpu_served
        if surplus >= 0:
            batt_res = step_battery(soc, surplus, dt_hours, cfg.battery)
            p_batt_bus = batt_res.p_batt_bus_w
            pv_curtailed = max(0.0, surplus - p_batt_bus)
        else:
            batt_res = step_battery(soc, surplus, dt_hours, cfg.battery)
            p_batt_bus = batt_res.p_batt_bus_w
            p_gpu_served = p_pv - p_batt_bus
            unmet = max(0.0, p_gpu_req - p_gpu_served)

        soc = batt_res.soc_next
        p_prev = p_gpu_req

        u = gpu_u_from_power(p_gpu_served, cfg.gpu)
        flops_step = gpu_flops_step(u, dt_s, cfg.gpu)

        records.append(
            {
                "P_pv_bus_w": p_pv,
                "P_gpu_req_w": p_gpu_req,
                "P_gpu_served_w": p_gpu_served,
                "P_batt_bus_w": p_batt_bus,
                "soc": soc,
                "pv_curtailed_w": pv_curtailed,
                "curtailed_w": pv_curtailed,
                "unmet_w": unmet,
                "flops_step": flops_step,
                "sec_to_sunrise": sec_to,
            }
        )

    result_df = pd.DataFrame(records, index=df.index)
    metrics = compute_metrics(result_df, cfg)
    return result_df, metrics
