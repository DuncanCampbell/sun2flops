"""Background tasks for running simulations."""

import json
import os
import traceback
from pathlib import Path

import pandas as pd

from api.schemas import FullConfigSchema, RunOptionsSchema, RunStatusSchema
from sun2flops.config import (
    SiteConfig,
    WeatherConfig,
    PVConfig,
    BatteryConfig,
    GPUConfig,
    GovernorConfig,
    SimConfig,
)
from sun2flops.data.nsrdb import generate_synthetic_weather, load_weather_range
from sun2flops.sim.engine import run_simulation
from sun2flops.sweep.runner import run_sweep


ARTIFACTS_DIR = Path("./artifacts")


def get_run_dir(run_id: str) -> Path:
    """Get the artifacts directory for a run."""
    return ARTIFACTS_DIR / run_id


def update_status(run_id: str, status: str, progress: int = 0, message: str = ""):
    """Update the status of a run."""
    run_dir = get_run_dir(run_id)
    status_data = RunStatusSchema(
        status=status,
        progress=progress,
        message=message,
    )
    with open(run_dir / "status.json", "w") as f:
        json.dump(status_data.model_dump(), f)


def schema_to_config(config: FullConfigSchema):
    """Convert Pydantic schema to dataclass config objects."""
    site = SiteConfig(
        name=config.site.name,
        latitude=config.site.latitude,
        longitude=config.site.longitude,
        timezone=config.site.timezone,
        altitude_m=config.site.altitude_m,
    )

    weather = WeatherConfig(
        source=config.weather.source,
        years=config.weather.years,
        interval_min=config.weather.interval_min,
        leap_day=config.weather.leap_day,
        cache_dir=config.weather.cache_dir,
    )

    pv = PVConfig(
        surface_tilt_deg=config.pv.surface_tilt_deg,
        surface_azimuth_deg=config.pv.surface_azimuth_deg,
        dc_nameplate_kw=config.pv.dc_nameplate_kw,
        dc_model=config.pv.dc_model,
        gamma_pdc_per_c=config.pv.gamma_pdc_per_c,
        mppt_eff=config.pv.mppt_eff,
        dc_wiring_eff=config.pv.dc_wiring_eff,
    )

    battery = BatteryConfig(
        energy_capacity_kwh=config.battery.energy_capacity_kwh,
        soc_init=config.battery.soc_init,
        soc_min=config.battery.soc_min,
        soc_max=config.battery.soc_max,
        ocv_soc=tuple(config.battery.ocv_soc),
        ocv_v=tuple(config.battery.ocv_v),
        r_internal_ohm=config.battery.r_internal_ohm,
        i_charge_max_a=config.battery.i_charge_max_a,
        i_discharge_max_a=config.battery.i_discharge_max_a,
        charge_eff=config.battery.charge_eff,
        discharge_eff=config.battery.discharge_eff,
    )

    gpu = GPUConfig(
        n_gpus=config.gpu.n_gpus,
        p_idle_w=config.gpu.p_idle_w,
        p_max_w=config.gpu.p_max_w,
        flops_peak_per_gpu=config.gpu.flops_peak_per_gpu,
        power_exponent=config.gpu.power_exponent,
    )

    governor = GovernorConfig(
        enabled=config.governor.enabled,
        reserve_soc=config.governor.reserve_soc,
        safety_factor=config.governor.safety_factor,
        ramp_limit_w_per_step=config.governor.ramp_limit_w_per_step,
    )

    sim = SimConfig(
        dt_min=config.sim.dt_min,
        coupling_mode=config.sim.coupling_mode,
    )

    return site, weather, pv, battery, gpu, governor, sim


def load_weather_data(
    site: SiteConfig,
    weather_cfg: WeatherConfig,
    run_options: RunOptionsSchema,
) -> pd.DataFrame:
    """Load weather data for simulation."""
    api_key = os.environ.get("NSRDB_API_KEY", "")
    email = os.environ.get("NSRDB_EMAIL", "")

    if api_key and email:
        # Use NSRDB data
        if run_options.use_all_years:
            return load_weather_range(
                site=site,
                wcfg=weather_cfg,
                api_key=api_key,
                email=email,
            )
        else:
            # Single year
            from sun2flops.data.nsrdb import fetch_nsrdb_year
            df, _ = fetch_nsrdb_year(
                site=site,
                year=run_options.single_year or 2021,
                interval_min=weather_cfg.interval_min,
                leap_day=weather_cfg.leap_day,
                api_key=api_key,
                email=email,
                cache_dir=weather_cfg.cache_dir,
            )
            return df
    else:
        # Use synthetic data
        return generate_synthetic_weather(
            site=site,
            year=run_options.single_year or 2021,
            interval_min=weather_cfg.interval_min,
        )


def run_simulation_task(
    run_id: str,
    config: FullConfigSchema,
    run_options: RunOptionsSchema,
):
    """Run a single simulation."""
    run_dir = get_run_dir(run_id)

    try:
        update_status(run_id, "running", 10, "Loading weather data...")

        # Convert config
        site, weather_cfg, pv, battery, gpu, governor, sim = schema_to_config(config)

        # Load weather
        weather = load_weather_data(site, weather_cfg, run_options)

        update_status(run_id, "running", 30, "Running simulation...")

        # Run simulation
        result = run_simulation(
            weather=weather,
            site=site,
            pv=pv,
            batt=battery,
            gpu=gpu,
            gov=governor,
            sim=sim,
        )

        update_status(run_id, "running", 80, "Saving results...")

        # Save timeseries as JSON for API
        ts = result["timeseries"]
        ts_json = {
            "index": ts.index.strftime("%Y-%m-%dT%H:%M:%S%z").tolist(),
            "columns": ts.columns.tolist(),
            "data": ts.values.tolist(),
        }
        with open(run_dir / "timeseries.json", "w") as f:
            json.dump(ts_json, f)

        # Save timeseries as CSV for download
        ts.to_csv(run_dir / "timeseries.csv")

        # Save metrics
        metrics = result["metrics"]
        # Convert any non-serializable types
        metrics_clean = {}
        for k, v in metrics.items():
            if hasattr(v, "item"):  # numpy types
                metrics_clean[k] = v.item()
            else:
                metrics_clean[k] = v

        with open(run_dir / "metrics.json", "w") as f:
            json.dump(metrics_clean, f, indent=2)

        update_status(run_id, "done", 100, "Simulation complete")

    except Exception as e:
        error_msg = f"Error: {str(e)}\n{traceback.format_exc()}"
        update_status(run_id, "error", 0, error_msg)


def run_sweep_task(
    run_id: str,
    config: FullConfigSchema,
    run_options: RunOptionsSchema,
):
    """Run a parameter sweep."""
    run_dir = get_run_dir(run_id)

    try:
        update_status(run_id, "running", 5, "Loading weather data...")

        # Convert config
        site, weather_cfg, pv, battery, gpu, governor, sim = schema_to_config(config)

        # Load weather for single year (for faster sweeps)
        weather = load_weather_data(site, weather_cfg, run_options)

        update_status(run_id, "running", 10, "Starting sweep...")

        # Progress callback
        def progress_callback(current: int, total: int):
            progress = 10 + int(80 * current / total)
            update_status(
                run_id,
                "running",
                progress,
                f"Running simulation {current}/{total}...",
            )

        # Run sweep
        sweep_df = run_sweep(
            weather=weather,
            site=site,
            pv=pv,
            batt=battery,
            gpu=gpu,
            gov=governor,
            sim=sim,
            pv_kw_list=run_options.pv_kw_list,
            batt_kwh_list=run_options.batt_kwh_list,
            progress_callback=progress_callback,
        )

        update_status(run_id, "running", 95, "Saving results...")

        # Save sweep results as JSON
        sweep_json = {
            "columns": sweep_df.columns.tolist(),
            "data": sweep_df.to_dict(orient="records"),
        }
        # Clean numpy types
        for row in sweep_json["data"]:
            for k, v in row.items():
                if hasattr(v, "item"):
                    row[k] = v.item()

        with open(run_dir / "sweep.json", "w") as f:
            json.dump(sweep_json, f)

        # Save sweep as CSV
        sweep_df.to_csv(run_dir / "sweep.csv", index=False)

        # Save summary metrics (best configuration)
        best_row = sweep_df.loc[sweep_df["utilization"].idxmax()]
        metrics = best_row.to_dict()
        for k, v in metrics.items():
            if hasattr(v, "item"):
                metrics[k] = v.item()

        with open(run_dir / "metrics.json", "w") as f:
            json.dump(metrics, f, indent=2)

        update_status(run_id, "done", 100, "Sweep complete")

    except Exception as e:
        error_msg = f"Error: {str(e)}\n{traceback.format_exc()}"
        update_status(run_id, "error", 0, error_msg)
