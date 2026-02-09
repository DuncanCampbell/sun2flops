# Sun2FLOPs

A modular simulation package that models solar PV generation flowing through a DC battery system to GPU compute (FLOPs) with 30-minute historical weather data. The package is designed for headless Python use and a Colab notebook runner.

## Features

- NSRDB (PSM3) weather ingestion with caching
- PV plane-of-array transposition and PVWatts DC power
- Battery OCV + internal resistance step model with current limits
- GPU power utilization + FLOPs mapping
- Governor and simulation engine
- Sweep runner and plotting utilities

## Quick start

```bash
pip install -e .
```

```python
from sun2flops.config.models import (
    SiteConfig, WeatherConfig, PVConfig, BatteryConfig, GPUConfig,
    GovernorConfig, SimConfig, SweepConfig, FullConfig,
)
from sun2flops.data.nsrdb import load_weather_range
from sun2flops.sim.engine import run_simulation

cfg = FullConfig(
    site=SiteConfig(
        name="Texas",
        latitude=31.9686,
        longitude=-99.9018,
        timezone="America/Chicago",
    ),
    weather=WeatherConfig(source="nsrdb", years=[2021]),
    pv=PVConfig(surface_tilt_deg=20, surface_azimuth_deg=180, dc_nameplate_kw=3),
    battery=BatteryConfig(energy_capacity_kwh=10),
    gpu=GPUConfig(),
    governor=GovernorConfig(),
    sim=SimConfig(),
    sweep=SweepConfig(),
)

weather = load_weather_range(cfg.site, cfg.weather)
results, metrics = run_simulation(weather, cfg)
print(metrics)
```

See `notebooks/colab_driver.ipynb` for a full workflow.

## Colab quick start

1. Open `notebooks/colab_driver.ipynb` in Colab.
2. Update the `REPO_DIR` variable in the notebook to point to the local folder that contains `pyproject.toml` (not a URL).
3. Run the install cell (it upgrades pvlib and runs `pip install -e .`) and continue through the notebook.
4. Set your NSRDB API key and email in the notebook cell before fetching weather data.

If you connected Colab to this repo through GitHub and `pyproject.toml` is not found, `git clone` the repo in Colab (for example, into `/content/sun2flops`) and set `REPO_DIR` to that local folder.
