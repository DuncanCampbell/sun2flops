"""Battery model with OCV curve, internal resistance, and current limits."""

from dataclasses import dataclass
from typing import Tuple

import numpy as np

from sun2flops.config import BatteryConfig


@dataclass
class BatteryState:
    """Current state of the battery."""
    soc: float


@dataclass
class BatteryStepResult:
    """Result of a single battery step."""
    soc_next: float
    v_ocv: float
    i_a: float  # Positive = charging, negative = discharging
    p_batt_w: float  # Power at battery terminals (cell side)
    p_bus_w: float  # Power on DC bus side
    losses_w: float  # Total losses (converter + internal resistance)
    limited: bool  # True if request was limited


def ocv_from_soc(soc: float, cfg: BatteryConfig) -> float:
    """
    Get open-circuit voltage from SOC using piecewise linear interpolation.

    Parameters
    ----------
    soc : float
        State of charge (0 to 1)
    cfg : BatteryConfig
        Battery configuration with OCV curve

    Returns
    -------
    float
        Open-circuit voltage in volts
    """
    soc_points = np.array(cfg.ocv_soc)
    v_points = np.array(cfg.ocv_v)

    # Clamp SOC to valid range
    soc_clamped = np.clip(soc, soc_points[0], soc_points[-1])

    return float(np.interp(soc_clamped, soc_points, v_points))


def step_battery(
    state: BatteryState,
    p_bus_request_w: float,
    dt_hours: float,
    cfg: BatteryConfig,
) -> BatteryStepResult:
    """
    Execute one battery timestep.

    Sign conventions:
    - p_bus_request_w > 0: charge from bus into battery
    - p_bus_request_w < 0: discharge from battery to bus

    Parameters
    ----------
    state : BatteryState
        Current battery state
    p_bus_request_w : float
        Requested power on bus side (positive = charge, negative = discharge)
    dt_hours : float
        Time step in hours
    cfg : BatteryConfig
        Battery configuration

    Returns
    -------
    BatteryStepResult
        Result of the step including new SOC and actual power
    """
    soc = state.soc
    capacity_wh = cfg.energy_capacity_kwh * 1000.0

    # Get OCV at current SOC
    v_ocv = ocv_from_soc(soc, cfg)

    # Handle zero capacity case
    if capacity_wh <= 0:
        return BatteryStepResult(
            soc_next=soc,
            v_ocv=v_ocv,
            i_a=0.0,
            p_batt_w=0.0,
            p_bus_w=0.0,
            losses_w=0.0,
            limited=abs(p_bus_request_w) > 0,
        )

    limited = False

    if p_bus_request_w >= 0:
        # Charging: bus -> battery
        # P_cell = P_bus * charge_eff
        p_cell_request = p_bus_request_w * cfg.charge_eff

        # Solve for current: P_cell = V*I = (OCV + I*R) * I
        # OCV*I + R*I^2 = P_cell
        # R*I^2 + OCV*I - P_cell = 0
        # I = (-OCV + sqrt(OCV^2 + 4*R*P_cell)) / (2*R)
        i_a, actual_limited = _solve_charging_current(
            v_ocv, cfg.r_internal_ohm, p_cell_request, cfg.i_charge_max_a
        )
        limited = limited or actual_limited

        # Check SOC limit
        energy_to_add_wh = v_ocv * i_a * dt_hours  # Approximate
        soc_new = soc + energy_to_add_wh / capacity_wh

        if soc_new > cfg.soc_max:
            # Limit to max SOC
            energy_available_wh = (cfg.soc_max - soc) * capacity_wh
            if energy_available_wh > 0 and dt_hours > 0:
                i_a = energy_available_wh / (v_ocv * dt_hours)
                i_a = min(i_a, cfg.i_charge_max_a)
            else:
                i_a = 0.0
            limited = True

        # Calculate actual powers
        v_term = v_ocv + i_a * cfg.r_internal_ohm  # Terminal voltage during charge
        p_batt_w = v_term * i_a
        p_bus_w = p_batt_w / cfg.charge_eff if cfg.charge_eff > 0 else 0.0
        losses_w = p_bus_w - (v_ocv * i_a)  # Converter + I²R losses

        # Update SOC
        energy_added_wh = v_ocv * i_a * dt_hours
        soc_next = soc + energy_added_wh / capacity_wh
        soc_next = min(soc_next, cfg.soc_max)

    else:
        # Discharging: battery -> bus
        # P_bus = P_cell * discharge_eff
        # We want P_bus = -p_bus_request_w (positive value for output)
        p_bus_desired = -p_bus_request_w
        p_cell_request = p_bus_desired / cfg.discharge_eff if cfg.discharge_eff > 0 else 0.0

        # Solve for current: P_cell = V*I = (OCV - I*R) * I (I positive for discharge)
        # OCV*I - R*I^2 = P_cell
        # -R*I^2 + OCV*I - P_cell = 0
        # R*I^2 - OCV*I + P_cell = 0
        # I = (OCV - sqrt(OCV^2 - 4*R*P_cell)) / (2*R)
        i_a, actual_limited = _solve_discharging_current(
            v_ocv, cfg.r_internal_ohm, p_cell_request, cfg.i_discharge_max_a
        )
        limited = limited or actual_limited

        # Check SOC limit
        energy_to_remove_wh = v_ocv * i_a * dt_hours  # Approximate
        soc_new = soc - energy_to_remove_wh / capacity_wh

        if soc_new < cfg.soc_min:
            # Limit to min SOC
            energy_available_wh = (soc - cfg.soc_min) * capacity_wh
            if energy_available_wh > 0 and dt_hours > 0:
                i_a = energy_available_wh / (v_ocv * dt_hours)
                i_a = min(i_a, cfg.i_discharge_max_a)
            else:
                i_a = 0.0
            limited = True

        # Calculate actual powers (i_a is positive for discharge)
        v_term = v_ocv - i_a * cfg.r_internal_ohm  # Terminal voltage during discharge
        p_batt_w = v_term * i_a  # Power delivered by battery cells
        p_bus_w = -p_batt_w * cfg.discharge_eff  # Power to bus (negative = discharge)

        # Internal resistance losses
        i2r_loss = i_a * i_a * cfg.r_internal_ohm
        converter_loss = p_batt_w * (1 - cfg.discharge_eff)
        losses_w = i2r_loss + converter_loss

        # Update SOC
        energy_removed_wh = v_ocv * i_a * dt_hours
        soc_next = soc - energy_removed_wh / capacity_wh
        soc_next = max(soc_next, cfg.soc_min)

        # Store current as negative for discharge convention
        i_a = -i_a

    soc_next = np.clip(soc_next, cfg.soc_min, cfg.soc_max)

    return BatteryStepResult(
        soc_next=float(soc_next),
        v_ocv=v_ocv,
        i_a=float(i_a),
        p_batt_w=float(p_batt_w) if p_bus_request_w >= 0 else float(-p_batt_w),
        p_bus_w=float(p_bus_w),
        losses_w=float(losses_w),
        limited=limited,
    )


def _solve_charging_current(
    v_ocv: float,
    r_ohm: float,
    p_cell_target: float,
    i_max: float,
) -> Tuple[float, bool]:
    """
    Solve for charging current given target cell power.

    During charging: V_terminal = V_ocv + I*R
    P_cell = V_terminal * I = (V_ocv + I*R) * I = V_ocv*I + R*I²

    Solving: R*I² + V_ocv*I - P_cell = 0
    """
    limited = False

    if p_cell_target <= 0:
        return 0.0, False

    if r_ohm > 0:
        # Quadratic formula
        a = r_ohm
        b = v_ocv
        c = -p_cell_target

        discriminant = b * b - 4 * a * c
        if discriminant < 0:
            # No real solution, limit to max current
            i_a = i_max
            limited = True
        else:
            # Take positive root
            i_a = (-b + np.sqrt(discriminant)) / (2 * a)
    else:
        # No internal resistance
        i_a = p_cell_target / v_ocv if v_ocv > 0 else 0.0

    # Apply current limit
    if i_a > i_max:
        i_a = i_max
        limited = True

    return max(0.0, i_a), limited


def _solve_discharging_current(
    v_ocv: float,
    r_ohm: float,
    p_cell_target: float,
    i_max: float,
) -> Tuple[float, bool]:
    """
    Solve for discharging current given target cell power.

    During discharge: V_terminal = V_ocv - I*R
    P_cell = V_terminal * I = (V_ocv - I*R) * I = V_ocv*I - R*I²

    Solving: -R*I² + V_ocv*I - P_cell = 0
    Or: R*I² - V_ocv*I + P_cell = 0
    """
    limited = False

    if p_cell_target <= 0:
        return 0.0, False

    if r_ohm > 0:
        # Quadratic formula
        a = r_ohm
        b = -v_ocv
        c = p_cell_target

        discriminant = b * b - 4 * a * c
        if discriminant < 0:
            # No real solution - requested power exceeds battery capability
            # Max power occurs at I = V_ocv / (2*R)
            i_a = min(v_ocv / (2 * r_ohm), i_max)
            limited = True
        else:
            # Take the smaller positive root (less current for same power)
            i_a = (v_ocv - np.sqrt(discriminant)) / (2 * r_ohm)
            if i_a < 0:
                # Use the other root
                i_a = (v_ocv + np.sqrt(discriminant)) / (2 * r_ohm)
    else:
        # No internal resistance
        i_a = p_cell_target / v_ocv if v_ocv > 0 else 0.0

    # Apply current limit
    if i_a > i_max:
        i_a = i_max
        limited = True

    return max(0.0, i_a), limited


def get_max_discharge_power(state: BatteryState, cfg: BatteryConfig) -> float:
    """
    Get maximum instantaneous discharge power available.

    Parameters
    ----------
    state : BatteryState
        Current battery state
    cfg : BatteryConfig
        Battery configuration

    Returns
    -------
    float
        Maximum discharge power in watts (positive value)
    """
    if cfg.energy_capacity_kwh <= 0:
        return 0.0

    if state.soc <= cfg.soc_min:
        return 0.0

    v_ocv = ocv_from_soc(state.soc, cfg)

    # Max power with current limit
    # P = (V_ocv - I*R) * I, maximized at I = V_ocv/(2R)
    if cfg.r_internal_ohm > 0:
        i_optimal = v_ocv / (2 * cfg.r_internal_ohm)
        i_max = min(i_optimal, cfg.i_discharge_max_a)
    else:
        i_max = cfg.i_discharge_max_a

    v_term = v_ocv - i_max * cfg.r_internal_ohm
    p_cell_max = v_term * i_max
    p_bus_max = p_cell_max * cfg.discharge_eff

    return max(0.0, p_bus_max)


def get_max_charge_power(state: BatteryState, cfg: BatteryConfig) -> float:
    """
    Get maximum instantaneous charge power that can be accepted.

    Parameters
    ----------
    state : BatteryState
        Current battery state
    cfg : BatteryConfig
        Battery configuration

    Returns
    -------
    float
        Maximum charge power in watts (positive value)
    """
    if cfg.energy_capacity_kwh <= 0:
        return 0.0

    if state.soc >= cfg.soc_max:
        return 0.0

    v_ocv = ocv_from_soc(state.soc, cfg)

    # At max current
    i_max = cfg.i_charge_max_a
    v_term = v_ocv + i_max * cfg.r_internal_ohm
    p_cell_max = v_term * i_max
    p_bus_max = p_cell_max / cfg.charge_eff if cfg.charge_eff > 0 else 0.0

    return p_bus_max
