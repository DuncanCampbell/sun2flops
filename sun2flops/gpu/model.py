"""GPU power and compute model."""

import numpy as np

from sun2flops.config import GPUConfig


def gpu_power_w(u: float, cfg: GPUConfig) -> float:
    """
    Calculate GPU power consumption at given utilization.

    P(u) = P_idle + (P_max - P_idle) * u^exponent

    Parameters
    ----------
    u : float
        Utilization level (0 to 1)
    cfg : GPUConfig
        GPU configuration

    Returns
    -------
    float
        Total GPU power in watts for all GPUs
    """
    u = np.clip(u, 0.0, 1.0)
    p_single = cfg.p_idle_w + (cfg.p_max_w - cfg.p_idle_w) * (u ** cfg.power_exponent)
    return p_single * cfg.n_gpus


def gpu_flops(u: float, dt_s: float, cfg: GPUConfig) -> float:
    """
    Calculate FLOPs produced at given utilization over a time period.

    FLOPs = u * flops_peak_per_gpu * n_gpus * dt_seconds

    Parameters
    ----------
    u : float
        Utilization level (0 to 1)
    dt_s : float
        Time period in seconds
    cfg : GPUConfig
        GPU configuration

    Returns
    -------
    float
        Total FLOPs produced
    """
    u = np.clip(u, 0.0, 1.0)
    return u * cfg.flops_peak_per_gpu * cfg.n_gpus * dt_s


def u_from_power(p_target_w: float, cfg: GPUConfig) -> float:
    """
    Calculate utilization from target power level.

    Inverts the power curve:
    P = P_idle + (P_max - P_idle) * u^exp
    u = ((P - P_idle) / (P_max - P_idle)) ^ (1/exp)

    Parameters
    ----------
    p_target_w : float
        Target power in watts (for all GPUs)
    cfg : GPUConfig
        GPU configuration

    Returns
    -------
    float
        Utilization level (0 to 1)
    """
    total_p_idle = cfg.p_idle_w * cfg.n_gpus
    total_p_max = cfg.p_max_w * cfg.n_gpus
    p_range = total_p_max - total_p_idle

    if p_range <= 0:
        return 1.0 if p_target_w >= total_p_max else 0.0

    if p_target_w <= total_p_idle:
        return 0.0

    if p_target_w >= total_p_max:
        return 1.0

    # Invert the power curve
    normalized = (p_target_w - total_p_idle) / p_range
    u = normalized ** (1.0 / cfg.power_exponent)

    return np.clip(u, 0.0, 1.0)


def total_idle_power_w(cfg: GPUConfig) -> float:
    """Get total idle power for all GPUs."""
    return cfg.p_idle_w * cfg.n_gpus


def total_max_power_w(cfg: GPUConfig) -> float:
    """Get total max power for all GPUs."""
    return cfg.p_max_w * cfg.n_gpus
