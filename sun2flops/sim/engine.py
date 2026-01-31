"""Main simulation engine for sun2flops."""

from typing import Dict, Any

import numpy as np
import pandas as pd

from sun2flops.config import (
    SiteConfig, PVConfig, BatteryConfig, GPUConfig,
    GovernorConfig, SimConfig,
)
from sun2flops.battery.model import (
    BatteryState, step_battery, get_max_discharge_power, get_max_charge_power,
)
from sun2flops.gpu.model import (
    gpu_power_w, gpu_flops, u_from_power,
    total_idle_power_w, total_max_power_w,
)
from sun2flops.control.governor import GovernorState, governor_target_power
from sun2flops.control.solar_times import compute_sun_times
from sun2flops.pv.poa import add_poa_irradiance
from sun2flops.pv.dc_power import pv_dc_power_mpp


def run_simulation(
    weather: pd.DataFrame,
    site: SiteConfig,
    pv: PVConfig,
    batt: BatteryConfig,
    gpu: GPUConfig,
    gov: GovernorConfig,
    sim: SimConfig,
) -> Dict[str, Any]:
    """
    Run the full simulation.

    Parameters
    ----------
    weather : pd.DataFrame
        Weather data with ghi, dni, dhi, temp_air, wind_speed
    site : SiteConfig
        Site location configuration
    pv : PVConfig
        PV system configuration
    batt : BatteryConfig
        Battery configuration
    gpu : GPUConfig
        GPU configuration
    gov : GovernorConfig
        Governor configuration
    sim : SimConfig
        Simulation configuration

    Returns
    -------
    Dict with:
        - timeseries: pd.DataFrame with simulation results
        - metrics: dict with summary metrics
    """
    # Compute POA irradiance and cell temperature
    poa_df = add_poa_irradiance(weather, site, pv)

    # Compute PV DC power on bus
    pv_bus_power = pv_dc_power_mpp(poa_df, pv)

    # Compute solar times for governor
    sun_times = compute_sun_times(poa_df.index, site)

    # Initialize states
    batt_state = BatteryState(soc=batt.soc_init)
    gov_state = GovernorState(p_prev_w=0.0)

    # Time step
    dt_hours = sim.dt_min / 60.0
    dt_seconds = sim.dt_min * 60.0

    # Prepare output arrays
    n_steps = len(poa_df)

    results = {
        'P_pv_bus_w': np.zeros(n_steps),
        'P_gpu_req_w': np.zeros(n_steps),
        'P_gpu_served_w': np.zeros(n_steps),
        'P_batt_bus_w': np.zeros(n_steps),
        'soc': np.zeros(n_steps),
        'curtailed_w': np.zeros(n_steps),
        'unmet_w': np.zeros(n_steps),
        'flops_step': np.zeros(n_steps),
        'utilization': np.zeros(n_steps),
    }

    p_gpu_max = total_max_power_w(gpu)
    p_gpu_idle = total_idle_power_w(gpu)

    for i in range(n_steps):
        # Current PV power available on bus
        p_pv = pv_bus_power.iloc[i]
        results['P_pv_bus_w'][i] = p_pv

        # Current SOC
        current_soc = batt_state.soc
        results['soc'][i] = current_soc

        # Governor determines target GPU power
        seconds_to_sunrise = sun_times['seconds_to_sunrise'].iloc[i]
        p_gpu_target = governor_target_power(
            current_soc, seconds_to_sunrise, gpu, batt, gov, gov_state
        )
        results['P_gpu_req_w'][i] = p_gpu_target

        # Determine how to meet the GPU demand
        # First, use available PV
        p_pv_to_gpu = min(p_pv, p_gpu_target)
        p_deficit = p_gpu_target - p_pv_to_gpu
        p_surplus = p_pv - p_pv_to_gpu

        # If deficit, try to discharge battery
        p_from_batt = 0.0
        p_to_batt = 0.0

        if p_deficit > 0:
            # Need to discharge battery
            max_discharge = get_max_discharge_power(batt_state, batt)
            p_from_batt = min(p_deficit, max_discharge)
        elif p_surplus > 0:
            # Charge battery with surplus
            max_charge = get_max_charge_power(batt_state, batt)
            p_to_batt = min(p_surplus, max_charge)

        # Calculate actual GPU power served
        p_gpu_served = p_pv_to_gpu + p_from_batt
        p_gpu_served = min(p_gpu_served, p_gpu_max)

        # Handle the case where GPU can't run below idle
        if p_gpu_served < p_gpu_idle:
            # GPU is off
            p_gpu_served = 0.0

        results['P_gpu_served_w'][i] = p_gpu_served

        # Curtailed is requested - served (only if we wanted to serve more)
        curtailed = max(0, p_gpu_target - p_gpu_served)
        results['curtailed_w'][i] = curtailed

        # Unmet is when we had insufficient power (PV + battery limited)
        unmet = max(0, p_gpu_target - p_gpu_served)
        results['unmet_w'][i] = unmet

        # Now execute battery step
        # Positive p_bus = charging, negative = discharging
        if p_from_batt > 0:
            # Discharging
            batt_result = step_battery(batt_state, -p_from_batt, dt_hours, batt)
            results['P_batt_bus_w'][i] = batt_result.p_bus_w  # Will be negative
        elif p_to_batt > 0:
            # Charging
            batt_result = step_battery(batt_state, p_to_batt, dt_hours, batt)
            results['P_batt_bus_w'][i] = batt_result.p_bus_w  # Will be positive
        else:
            # No battery action
            batt_result = step_battery(batt_state, 0.0, dt_hours, batt)
            results['P_batt_bus_w'][i] = 0.0

        # Update battery state
        batt_state = BatteryState(soc=batt_result.soc_next)

        # Calculate utilization and FLOPs
        if p_gpu_served > 0:
            u = u_from_power(p_gpu_served, gpu)
        else:
            u = 0.0

        results['utilization'][i] = u
        results['flops_step'][i] = gpu_flops(u, dt_seconds, gpu)

    # Build timeseries DataFrame
    timeseries = pd.DataFrame(results, index=poa_df.index)

    # Add some derived columns
    timeseries['poa_global'] = poa_df['poa_global']
    timeseries['temp_cell'] = poa_df['temp_cell']

    # Calculate summary metrics
    metrics = compute_metrics(timeseries, dt_hours, gpu, pv, batt)

    return {
        'timeseries': timeseries,
        'metrics': metrics,
    }


def compute_metrics(
    ts: pd.DataFrame,
    dt_hours: float,
    gpu: GPUConfig,
    pv: PVConfig,
    batt: BatteryConfig,
) -> Dict[str, Any]:
    """
    Compute summary metrics from simulation timeseries.

    Parameters
    ----------
    ts : pd.DataFrame
        Simulation timeseries
    dt_hours : float
        Time step in hours
    gpu : GPUConfig
        GPU configuration
    pv : PVConfig
        PV configuration
    batt : BatteryConfig
        Battery configuration

    Returns
    -------
    Dict with summary metrics
    """
    n_steps = len(ts)
    total_hours = n_steps * dt_hours

    # Total FLOPs
    total_flops = ts['flops_step'].sum()

    # Maximum possible FLOPs (if running at 100% all the time)
    max_flops_per_step = gpu.flops_peak_per_gpu * gpu.n_gpus * (dt_hours * 3600)
    max_possible_flops = max_flops_per_step * n_steps

    # Utilization (FLOPs-based)
    utilization = total_flops / max_possible_flops if max_possible_flops > 0 else 0.0

    # Average utilization
    avg_utilization = ts['utilization'].mean()

    # Hours with unmet demand
    hours_unserved = (ts['unmet_w'] > 0).sum() * dt_hours

    # Total energy
    total_pv_energy_wh = ts['P_pv_bus_w'].sum() * dt_hours
    total_gpu_energy_wh = ts['P_gpu_served_w'].sum() * dt_hours

    # Curtailment
    # Curtailment here means PV energy that wasn't used
    # Calculate as PV - GPU - battery charging
    pv_to_battery = ts['P_batt_bus_w'].clip(lower=0).sum() * dt_hours  # Only positive (charging)
    pv_used = total_gpu_energy_wh + pv_to_battery
    pv_curtailed = max(0, total_pv_energy_wh - pv_used)
    curtailment_fraction = pv_curtailed / total_pv_energy_wh if total_pv_energy_wh > 0 else 0.0

    # Peak values
    peak_pv_w = ts['P_pv_bus_w'].max()
    peak_gpu_w = ts['P_gpu_served_w'].max()

    # Battery cycles (rough estimate)
    # Each full discharge+charge is one cycle
    batt_energy_moved = ts['P_batt_bus_w'].abs().sum() * dt_hours
    batt_capacity_wh = batt.energy_capacity_kwh * 1000.0
    equivalent_cycles = batt_energy_moved / (2 * batt_capacity_wh) if batt_capacity_wh > 0 else 0.0

    return {
        'total_flops': total_flops,
        'max_possible_flops': max_possible_flops,
        'utilization': utilization,
        'avg_utilization': avg_utilization,
        'hours_unserved': hours_unserved,
        'total_hours': total_hours,
        'total_pv_energy_kwh': total_pv_energy_wh / 1000.0,
        'total_gpu_energy_kwh': total_gpu_energy_wh / 1000.0,
        'pv_curtailment_kwh': pv_curtailed / 1000.0,
        'curtailment_fraction': curtailment_fraction,
        'peak_pv_kw': peak_pv_w / 1000.0,
        'peak_gpu_kw': peak_gpu_w / 1000.0,
        'battery_equivalent_cycles': equivalent_cycles,
        'pv_nameplate_kw': pv.dc_nameplate_kw,
        'battery_capacity_kwh': batt.energy_capacity_kwh,
        'n_gpus': gpu.n_gpus,
    }
