"""Configuration dataclasses for sun2flops simulation."""

from dataclasses import dataclass, field
from typing import Literal, Optional, Sequence


@dataclass
class SiteConfig:
    """Site location configuration."""
    name: str = "Default Site"
    latitude: float = 31.9686  # Texas default
    longitude: float = -99.9018
    timezone: str = "America/Chicago"
    altitude_m: Optional[float] = None


@dataclass
class WeatherConfig:
    """Weather data configuration."""
    source: Literal["nsrdb"] = "nsrdb"
    years: Sequence[int] = field(default_factory=lambda: list(range(2003, 2023)))
    interval_min: int = 30
    leap_day: bool = False
    cache_dir: str = "./cache"


@dataclass
class PVConfig:
    """PV system configuration."""
    # Geometry
    surface_tilt_deg: float = 20.0
    surface_azimuth_deg: float = 180.0  # South-facing

    # Size
    dc_nameplate_kw: float = 1.0

    # Electrical model
    dc_model: Literal["pvwatts", "singlediode"] = "pvwatts"

    # PVWatts parameters
    gamma_pdc_per_c: float = -0.003  # Temperature coefficient

    # DC-only losses
    mppt_eff: float = 0.99
    dc_wiring_eff: float = 0.99


@dataclass
class BatteryConfig:
    """Battery system configuration with OCV curve and current limits."""
    # Capacity
    energy_capacity_kwh: float = 10.0

    # SOC limits
    soc_init: float = 0.5
    soc_min: float = 0.05
    soc_max: float = 0.95

    # OCV curve (piecewise linear) - SOC points
    ocv_soc: Sequence[float] = field(default_factory=lambda: [0.0, 0.2, 0.5, 0.8, 1.0])
    # OCV curve - voltage points (V)
    ocv_v: Sequence[float] = field(default_factory=lambda: [3.0, 3.4, 3.65, 3.9, 4.1])

    # Pack equivalent parameters
    r_internal_ohm: float = 0.02
    i_charge_max_a: float = 200.0
    i_discharge_max_a: float = 200.0

    # DC-only converter efficiencies
    charge_eff: float = 0.97  # bus → battery
    discharge_eff: float = 0.97  # battery → bus


@dataclass
class GPUConfig:
    """GPU compute configuration."""
    n_gpus: int = 1
    p_idle_w: float = 80.0
    p_max_w: float = 700.0

    # Compute mapping (placeholder)
    flops_peak_per_gpu: float = 1e15  # FLOPs/second at full utilization

    # Power curve exponent
    power_exponent: float = 3.0


@dataclass
class GovernorConfig:
    """Governor configuration for GPU throttling."""
    enabled: bool = True
    reserve_soc: float = 0.07
    safety_factor: float = 0.95
    ramp_limit_w_per_step: float = 200.0


@dataclass
class SimConfig:
    """Simulation configuration."""
    dt_min: int = 30
    coupling_mode: Literal["mppt_bus"] = "mppt_bus"  # Future: "direct"


@dataclass
class FullConfig:
    """Complete configuration for a simulation run."""
    site: SiteConfig = field(default_factory=SiteConfig)
    weather: WeatherConfig = field(default_factory=WeatherConfig)
    pv: PVConfig = field(default_factory=PVConfig)
    battery: BatteryConfig = field(default_factory=BatteryConfig)
    gpu: GPUConfig = field(default_factory=GPUConfig)
    governor: GovernorConfig = field(default_factory=GovernorConfig)
    sim: SimConfig = field(default_factory=SimConfig)
