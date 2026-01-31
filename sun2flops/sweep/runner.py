"""Parameter sweep runner for sun2flops."""

from dataclasses import replace
from typing import Callable, Dict, List, Any, Optional

import pandas as pd

from sun2flops.config import (
    SiteConfig, PVConfig, BatteryConfig, GPUConfig,
    GovernorConfig, SimConfig,
)
from sun2flops.sim.engine import run_simulation


# Default sweep ranges
DEFAULT_PV_KW_LIST = [0, 0.5, 1, 2, 3, 4, 5]
DEFAULT_BATT_KWH_LIST = [0, 2, 5, 10, 20]


def run_sweep(
    weather: pd.DataFrame,
    site: SiteConfig,
    pv: PVConfig,
    batt: BatteryConfig,
    gpu: GPUConfig,
    gov: GovernorConfig,
    sim: SimConfig,
    pv_kw_list: Optional[List[float]] = None,
    batt_kwh_list: Optional[List[float]] = None,
    progress_callback: Optional[Callable[[int, int], None]] = None,
) -> pd.DataFrame:
    """
    Run a parameter sweep over PV and battery sizes.

    Parameters
    ----------
    weather : pd.DataFrame
        Weather data
    site : SiteConfig
        Site configuration
    pv : PVConfig
        Base PV configuration (dc_nameplate_kw will be varied)
    batt : BatteryConfig
        Base battery configuration (energy_capacity_kwh will be varied)
    gpu : GPUConfig
        GPU configuration
    gov : GovernorConfig
        Governor configuration
    sim : SimConfig
        Simulation configuration
    pv_kw_list : List[float], optional
        List of PV sizes to sweep (kWdc)
    batt_kwh_list : List[float], optional
        List of battery sizes to sweep (kWh)
    progress_callback : Callable[[int, int], None], optional
        Callback for progress updates (current, total)

    Returns
    -------
    pd.DataFrame
        Tidy results DataFrame with columns:
        - pv_kw, batt_kwh (sweep parameters)
        - total_flops, utilization, hours_unserved, curtailment_fraction, ...
    """
    if pv_kw_list is None:
        pv_kw_list = DEFAULT_PV_KW_LIST

    if batt_kwh_list is None:
        batt_kwh_list = DEFAULT_BATT_KWH_LIST

    total_runs = len(pv_kw_list) * len(batt_kwh_list)
    results = []
    run_count = 0

    for pv_kw in pv_kw_list:
        for batt_kwh in batt_kwh_list:
            # Create modified configs
            pv_mod = replace(pv, dc_nameplate_kw=pv_kw)
            batt_mod = replace(batt, energy_capacity_kwh=batt_kwh)

            # Run simulation
            result = run_simulation(
                weather=weather,
                site=site,
                pv=pv_mod,
                batt=batt_mod,
                gpu=gpu,
                gov=gov,
                sim=sim,
            )

            # Extract metrics
            metrics = result['metrics']
            row = {
                'pv_kw': pv_kw,
                'batt_kwh': batt_kwh,
                **metrics,
            }
            results.append(row)

            run_count += 1
            if progress_callback:
                progress_callback(run_count, total_runs)

    return pd.DataFrame(results)


def run_sweep_async(
    weather: pd.DataFrame,
    site: SiteConfig,
    pv: PVConfig,
    batt: BatteryConfig,
    gpu: GPUConfig,
    gov: GovernorConfig,
    sim: SimConfig,
    pv_kw_list: Optional[List[float]] = None,
    batt_kwh_list: Optional[List[float]] = None,
    run_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Run sweep and return results (for use in async workers).

    Returns dict with:
        - sweep_df: sweep results as dict (for JSON serialization)
        - run_id: the run ID
    """
    progress_file = None
    if run_id:
        import json
        from pathlib import Path
        artifacts_dir = Path(f"./artifacts/{run_id}")
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        progress_file = artifacts_dir / "progress.json"

    def progress_callback(current: int, total: int):
        if progress_file:
            import json
            with open(progress_file, 'w') as f:
                json.dump({'current': current, 'total': total}, f)

    df = run_sweep(
        weather=weather,
        site=site,
        pv=pv,
        batt=batt,
        gpu=gpu,
        gov=gov,
        sim=sim,
        pv_kw_list=pv_kw_list,
        batt_kwh_list=batt_kwh_list,
        progress_callback=progress_callback,
    )

    return {
        'sweep_df': df.to_dict(orient='records'),
        'run_id': run_id,
    }
