"""Pydantic schemas for the API."""

from typing import Dict, List, Literal, Optional, Any
from pydantic import BaseModel, Field


class SiteConfigSchema(BaseModel):
    """Site location configuration."""
    name: str = "Default Site"
    latitude: float = 31.9686
    longitude: float = -99.9018
    timezone: str = "America/Chicago"
    altitude_m: Optional[float] = None


class WeatherConfigSchema(BaseModel):
    """Weather data configuration."""
    source: Literal["nsrdb"] = "nsrdb"
    years: List[int] = Field(default_factory=lambda: list(range(2003, 2023)))
    interval_min: int = 30
    leap_day: bool = False
    cache_dir: str = "./cache"


class PVConfigSchema(BaseModel):
    """PV system configuration."""
    surface_tilt_deg: float = 20.0
    surface_azimuth_deg: float = 180.0
    dc_nameplate_kw: float = 1.0
    dc_model: Literal["pvwatts", "singlediode"] = "pvwatts"
    gamma_pdc_per_c: float = -0.003
    mppt_eff: float = 0.99
    dc_wiring_eff: float = 0.99


class BatteryConfigSchema(BaseModel):
    """Battery system configuration."""
    energy_capacity_kwh: float = 10.0
    soc_init: float = 0.5
    soc_min: float = 0.05
    soc_max: float = 0.95
    ocv_soc: List[float] = Field(default_factory=lambda: [0.0, 0.2, 0.5, 0.8, 1.0])
    ocv_v: List[float] = Field(default_factory=lambda: [3.0, 3.4, 3.65, 3.9, 4.1])
    r_internal_ohm: float = 0.02
    i_charge_max_a: float = 200.0
    i_discharge_max_a: float = 200.0
    charge_eff: float = 0.97
    discharge_eff: float = 0.97


class GPUConfigSchema(BaseModel):
    """GPU compute configuration."""
    n_gpus: int = 1
    p_idle_w: float = 80.0
    p_max_w: float = 700.0
    flops_peak_per_gpu: float = 1e15
    power_exponent: float = 3.0


class GovernorConfigSchema(BaseModel):
    """Governor configuration."""
    enabled: bool = True
    reserve_soc: float = 0.07
    safety_factor: float = 0.95
    ramp_limit_w_per_step: float = 200.0


class SimConfigSchema(BaseModel):
    """Simulation configuration."""
    dt_min: int = 30
    coupling_mode: Literal["mppt_bus"] = "mppt_bus"


class FullConfigSchema(BaseModel):
    """Complete configuration."""
    site: SiteConfigSchema = Field(default_factory=SiteConfigSchema)
    weather: WeatherConfigSchema = Field(default_factory=WeatherConfigSchema)
    pv: PVConfigSchema = Field(default_factory=PVConfigSchema)
    battery: BatteryConfigSchema = Field(default_factory=BatteryConfigSchema)
    gpu: GPUConfigSchema = Field(default_factory=GPUConfigSchema)
    governor: GovernorConfigSchema = Field(default_factory=GovernorConfigSchema)
    sim: SimConfigSchema = Field(default_factory=SimConfigSchema)


class RunOptionsSchema(BaseModel):
    """Options for a run."""
    single_year: Optional[int] = 2021
    use_all_years: bool = False
    pv_kw_list: List[float] = Field(default_factory=lambda: [0, 0.5, 1, 2, 3, 4, 5])
    batt_kwh_list: List[float] = Field(default_factory=lambda: [0, 2, 5, 10, 20])


class RunRequestSchema(BaseModel):
    """Request to start a simulation run."""
    mode: Literal["single", "sweep"]
    config: FullConfigSchema
    run_options: RunOptionsSchema = Field(default_factory=RunOptionsSchema)


class RunResponseSchema(BaseModel):
    """Response after starting a run."""
    run_id: str


class RunStatusSchema(BaseModel):
    """Status of a run."""
    status: Literal["queued", "running", "done", "error"]
    progress: int = 0  # 0-100
    message: str = ""
    metrics: Optional[Dict[str, Any]] = None


class HealthCheckSchema(BaseModel):
    """Health check response."""
    nsrdb_configured: bool
    status: str = "ok"


class TimeseriesResponseSchema(BaseModel):
    """Timeseries data response."""
    index: List[str]  # ISO timestamps
    columns: List[str]
    data: List[List[float]]


class SweepResponseSchema(BaseModel):
    """Sweep results response."""
    columns: List[str]
    data: List[Dict[str, Any]]
