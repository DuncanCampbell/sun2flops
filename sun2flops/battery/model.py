from __future__ import annotations

from dataclasses import dataclass
import math

from sun2flops.config.models import BatteryConfig


@dataclass
class BatteryStepResult:
    soc_next: float
    v_ocv: float
    i_a: float
    p_batt_cell_w: float
    p_batt_bus_w: float
    losses_w: float
    limited: bool


def ocv_from_soc(soc: float, cfg: BatteryConfig) -> float:
    """Piecewise-linear interpolation with clamping."""
    if soc <= cfg.ocv_soc[0]:
        return cfg.ocv_v[0]
    if soc >= cfg.ocv_soc[-1]:
        return cfg.ocv_v[-1]
    for s0, s1, v0, v1 in zip(
        cfg.ocv_soc[:-1], cfg.ocv_soc[1:], cfg.ocv_v[:-1], cfg.ocv_v[1:]
    ):
        if s0 <= soc <= s1:
            frac = (soc - s0) / (s1 - s0)
            return v0 + frac * (v1 - v0)
    return cfg.ocv_v[-1]


def _solve_current(v_ocv: float, p_cell: float, r_int: float) -> float:
    discriminant = v_ocv**2 - 4 * r_int * p_cell
    if discriminant < 0:
        discriminant = 0
    sqrt_disc = math.sqrt(discriminant)
    if r_int == 0:
        return p_cell / v_ocv
    return (v_ocv - sqrt_disc) / (2 * r_int)


def step_battery(
    soc: float,
    p_bus_request_w: float,
    dt_hours: float,
    cfg: BatteryConfig,
) -> BatteryStepResult:
    """
    p_bus_request_w > 0 => charge (bus->battery)
    p_bus_request_w < 0 => discharge (battery->bus)

    Uses OCV(soc), Rint, current limits, converter efficiencies.
    Solves quadratic for current:
      P_cell = (OCV - I*R)*I

    Enforces SOC bounds; if clipping SOC, adjust actual power.
    """
    v_ocv = ocv_from_soc(soc, cfg)

    if p_bus_request_w >= 0:
        p_cell_target = -p_bus_request_w * cfg.charge_eff
    else:
        p_cell_target = -p_bus_request_w / cfg.discharge_eff

    i_a = _solve_current(v_ocv, p_cell_target, cfg.r_internal_ohm)
    limited = False
    if i_a > cfg.i_discharge_max_a:
        i_a = cfg.i_discharge_max_a
        limited = True
    if i_a < -cfg.i_charge_max_a:
        i_a = -cfg.i_charge_max_a
        limited = True

    p_cell_actual = (v_ocv - i_a * cfg.r_internal_ohm) * i_a

    if p_cell_actual >= 0:
        p_bus_actual = -p_cell_actual * cfg.discharge_eff
    else:
        p_bus_actual = -p_cell_actual / cfg.charge_eff

    capacity_wh = cfg.energy_capacity_kwh * 1000.0
    delta_soc = -p_cell_actual * dt_hours / capacity_wh
    soc_next = soc + delta_soc

    if soc_next < cfg.soc_min:
        soc_next = cfg.soc_min
        limited = True
    if soc_next > cfg.soc_max:
        soc_next = cfg.soc_max
        limited = True

    if limited:
        energy_delta_wh = (soc_next - soc) * capacity_wh
        p_cell_actual = -energy_delta_wh / dt_hours
        if p_cell_actual >= 0:
            p_bus_actual = -p_cell_actual * cfg.discharge_eff
        else:
            p_bus_actual = -p_cell_actual / cfg.charge_eff

    losses_w = abs(p_bus_actual - p_cell_actual)

    return BatteryStepResult(
        soc_next=soc_next,
        v_ocv=v_ocv,
        i_a=i_a,
        p_batt_cell_w=p_cell_actual,
        p_batt_bus_w=p_bus_actual,
        losses_w=losses_w,
        limited=limited,
    )
