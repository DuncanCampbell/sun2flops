"""Governor for GPU throttling based on battery state and time to sunrise."""

from dataclasses import dataclass

import numpy as np

from sun2flops.config import BatteryConfig, GovernorConfig, GPUConfig
from sun2flops.gpu.model import total_idle_power_w, total_max_power_w


@dataclass
class GovernorState:
    """State for the governor (for ramp limiting)."""
    p_prev_w: float = 0.0


def governor_target_power(
    soc: float,
    seconds_to_sunrise: float,
    gpu: GPUConfig,
    batt: BatteryConfig,
    cfg: GovernorConfig,
    state: GovernorState,
) -> float:
    """
    Calculate target GPU power using no-forecast throttling.

    The governor tries to sustain compute until sunrise by limiting
    power draw based on available battery energy.

    Parameters
    ----------
    soc : float
        Current battery state of charge (0 to 1)
    seconds_to_sunrise : float
        Seconds until next sunrise
    gpu : GPUConfig
        GPU configuration
    batt : BatteryConfig
        Battery configuration
    cfg : GovernorConfig
        Governor configuration
    state : GovernorState
        Governor state for ramp limiting

    Returns
    -------
    float
        Target GPU power in watts
    """
    if not cfg.enabled:
        # Governor disabled, return max power
        return total_max_power_w(gpu)

    p_max = total_max_power_w(gpu)
    p_idle = total_idle_power_w(gpu)

    # If it's daytime (seconds_to_sunrise <= 0), run at max
    if seconds_to_sunrise <= 0:
        p_target = p_max
    else:
        # Calculate available energy
        batt_capacity_wh = batt.energy_capacity_kwh * 1000.0
        e_available_wh = max(0.0, (soc - cfg.reserve_soc) * batt_capacity_wh)

        # Calculate sustainable power
        hours_to_sunrise = seconds_to_sunrise / 3600.0

        if hours_to_sunrise > 0:
            p_sustain_w = e_available_wh / hours_to_sunrise
        else:
            p_sustain_w = p_max

        # Apply safety factor
        p_target = p_sustain_w * cfg.safety_factor

        # Clamp to valid range
        p_target = np.clip(p_target, 0.0, p_max)

    # Apply ramp limit
    if cfg.ramp_limit_w_per_step > 0:
        delta = p_target - state.p_prev_w
        if abs(delta) > cfg.ramp_limit_w_per_step:
            if delta > 0:
                p_target = state.p_prev_w + cfg.ramp_limit_w_per_step
            else:
                p_target = state.p_prev_w - cfg.ramp_limit_w_per_step

    # Update state
    state.p_prev_w = p_target

    return float(p_target)
