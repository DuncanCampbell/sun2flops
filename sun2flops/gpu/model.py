from __future__ import annotations

from sun2flops.config.models import GPUConfig


def gpu_power_from_u_w(u: float, cfg: GPUConfig) -> float:
    """Scaled by n_gpus, includes idle."""
    u_clamped = min(max(u, 0.0), 1.0)
    p_per_gpu = cfg.p_idle_w + (cfg.p_max_w - cfg.p_idle_w) * (u_clamped ** cfg.power_exponent)
    return p_per_gpu * cfg.n_gpus


def gpu_u_from_power(p_w: float, cfg: GPUConfig) -> float:
    """Invert curve; clamp [0,1]."""
    p_per_gpu = max(p_w / cfg.n_gpus, 0.0)
    if p_per_gpu <= cfg.p_idle_w:
        return 0.0
    if p_per_gpu >= cfg.p_max_w:
        return 1.0
    norm = (p_per_gpu - cfg.p_idle_w) / (cfg.p_max_w - cfg.p_idle_w)
    u = norm ** (1.0 / cfg.power_exponent)
    return min(max(u, 0.0), 1.0)


def gpu_flops_step(u: float, dt_s: float, cfg: GPUConfig) -> float:
    """FLOPs produced this timestep."""
    u_clamped = min(max(u, 0.0), 1.0)
    return cfg.n_gpus * cfg.flops_peak_per_gpu * u_clamped * dt_s
