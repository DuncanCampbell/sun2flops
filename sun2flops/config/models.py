from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal, Sequence
import warnings


@dataclass(frozen=True)
class SiteConfig:
    name: str
    latitude: float
    longitude: float
    timezone: str
    altitude_m: float | None = None


@dataclass(frozen=True)
class WeatherConfig:
    source: Literal["nsrdb"]
    years: Sequence[int]
    interval_min: int = 30
    leap_day: bool = False
    cache_dir: str = "./cache"
    api_key: str | None = None
    email: str | None = None


@dataclass(frozen=True)
class PVConfig:
    surface_tilt_deg: float
    surface_azimuth_deg: float
    dc_nameplate_kw: float
    dc_model: Literal["pvwatts"] = "pvwatts"
    gamma_pdc_per_c: float = -0.003
    mppt_eff: float = 0.99
    dc_wiring_eff: float = 0.99


@dataclass(frozen=True)
class BatteryConfig:
    energy_capacity_kwh: float
    soc_init: float = 0.5
    soc_min: float = 0.05
    soc_max: float = 0.95
    ocv_soc: Sequence[float] = (0.0, 0.2, 0.5, 0.8, 1.0)
    ocv_v: Sequence[float] = (3.0, 3.4, 3.65, 3.9, 4.1)
    r_internal_ohm: float = 0.02
    i_charge_max_a: float = 200.0
    i_discharge_max_a: float = 200.0
    charge_eff: float = 0.97
    discharge_eff: float = 0.97


@dataclass(frozen=True)
class GPUConfig:
    n_gpus: int = 1
    p_idle_w: float = 80.0
    p_max_w: float = 700.0
    power_exponent: float = 3.0
    flops_peak_per_gpu: float = 1e15


@dataclass(frozen=True)
class GovernorConfig:
    enabled: bool = True
    reserve_soc: float = 0.07
    safety_factor: float = 0.95
    ramp_limit_w_per_step: float = 200.0


@dataclass(frozen=True)
class SimConfig:
    dt_min: int = 30
    coupling_mode: Literal["mppt_bus"] = "mppt_bus"


@dataclass(frozen=True)
class SweepConfig:
    pv_kw_list: Sequence[float] = (0, 0.5, 1, 2, 3, 4, 5)
    batt_kwh_list: Sequence[float] = (0, 2, 5, 10, 20)
    year_for_sweep: int = 2021


@dataclass(frozen=True)
class FullConfig:
    site: SiteConfig
    weather: WeatherConfig
    pv: PVConfig
    battery: BatteryConfig
    gpu: GPUConfig
    governor: GovernorConfig
    sim: SimConfig
    sweep: SweepConfig


def full_config_to_dict(cfg: FullConfig) -> dict:
    return asdict(cfg)


def full_config_from_dict(data: dict) -> FullConfig:
    return FullConfig(
        site=SiteConfig(**data["site"]),
        weather=WeatherConfig(**data["weather"]),
        pv=PVConfig(**data["pv"]),
        battery=BatteryConfig(**data["battery"]),
        gpu=GPUConfig(**data["gpu"]),
        governor=GovernorConfig(**data["governor"]),
        sim=SimConfig(**data["sim"]),
        sweep=SweepConfig(**data["sweep"]),
    )


def _validate_efficiency(name: str, value: float) -> None:
    if not (0 < value <= 1):
        raise ValueError(f"{name} must be in (0, 1], got {value}")


def validate_config(cfg: FullConfig) -> None:
    if cfg.sim.dt_min != 30:
        raise ValueError(f"dt_min must be 30, got {cfg.sim.dt_min}")

    years = list(cfg.weather.years)
    for year in years:
        if year < 1998 or year > 2022:
            warnings.warn(
                f"year {year} is outside NSRDB coverage (1998-2022)",
                stacklevel=2,
            )

    _validate_efficiency("mppt_eff", cfg.pv.mppt_eff)
    _validate_efficiency("dc_wiring_eff", cfg.pv.dc_wiring_eff)
    _validate_efficiency("charge_eff", cfg.battery.charge_eff)
    _validate_efficiency("discharge_eff", cfg.battery.discharge_eff)

    if not (0 <= cfg.battery.soc_min < cfg.battery.soc_max <= 1):
        raise ValueError("soc_min and soc_max must satisfy 0 <= min < max <= 1")
    if not (cfg.battery.soc_min <= cfg.battery.soc_init <= cfg.battery.soc_max):
        raise ValueError("soc_init must be within [soc_min, soc_max]")

    if len(cfg.battery.ocv_soc) != len(cfg.battery.ocv_v):
        raise ValueError("ocv_soc and ocv_v must have the same length")
    if any(s1 >= s2 for s1, s2 in zip(cfg.battery.ocv_soc, cfg.battery.ocv_soc[1:])):
        raise ValueError("ocv_soc must be strictly increasing")
