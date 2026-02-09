from __future__ import annotations

from sun2flops.config.models import BatteryConfig, GovernorConfig, GPUConfig
from sun2flops.gpu.model import gpu_power_from_u_w


def governor_target_power_w(
    soc: float,
    sec_to_sunrise: float,
    gpu: GPUConfig,
    batt: BatteryConfig,
    gov: GovernorConfig,
    p_prev_w: float,
) -> float:
    """
    No forecast.
    E_available = max(0, (soc - reserve_soc) * batt_capacity_Wh)
    P_sustain = E_available / (sec_to_sunrise/3600)
    target = clamp(P_sustain*safety_factor, 0..P_max_total)
    ramp limit around p_prev_w
    """
    if not gov.enabled:
        return gpu_power_from_u_w(1.0, gpu)

    capacity_wh = batt.energy_capacity_kwh * 1000.0
    e_available = max(0.0, (soc - gov.reserve_soc) * capacity_wh)
    if sec_to_sunrise <= 0:
        p_sustain = 0.0
    else:
        p_sustain = e_available / (sec_to_sunrise / 3600.0)

    p_max = gpu_power_from_u_w(1.0, gpu)
    target = max(0.0, min(p_sustain * gov.safety_factor, p_max))

    if gov.ramp_limit_w_per_step > 0:
        lower = p_prev_w - gov.ramp_limit_w_per_step
        upper = p_prev_w + gov.ramp_limit_w_per_step
        target = max(lower, min(target, upper))

    return max(0.0, min(target, p_max))
