// Configuration types matching the API schemas

export interface SiteConfig {
  name: string;
  latitude: number;
  longitude: number;
  timezone: string;
  altitude_m: number | null;
}

export interface WeatherConfig {
  source: 'nsrdb';
  years: number[];
  interval_min: number;
  leap_day: boolean;
  cache_dir: string;
}

export interface PVConfig {
  surface_tilt_deg: number;
  surface_azimuth_deg: number;
  dc_nameplate_kw: number;
  dc_model: 'pvwatts' | 'singlediode';
  gamma_pdc_per_c: number;
  mppt_eff: number;
  dc_wiring_eff: number;
}

export interface BatteryConfig {
  energy_capacity_kwh: number;
  soc_init: number;
  soc_min: number;
  soc_max: number;
  ocv_soc: number[];
  ocv_v: number[];
  r_internal_ohm: number;
  i_charge_max_a: number;
  i_discharge_max_a: number;
  charge_eff: number;
  discharge_eff: number;
}

export interface GPUConfig {
  n_gpus: number;
  p_idle_w: number;
  p_max_w: number;
  flops_peak_per_gpu: number;
  power_exponent: number;
}

export interface GovernorConfig {
  enabled: boolean;
  reserve_soc: number;
  safety_factor: number;
  ramp_limit_w_per_step: number;
}

export interface SimConfig {
  dt_min: number;
  coupling_mode: 'mppt_bus';
}

export interface FullConfig {
  site: SiteConfig;
  weather: WeatherConfig;
  pv: PVConfig;
  battery: BatteryConfig;
  gpu: GPUConfig;
  governor: GovernorConfig;
  sim: SimConfig;
}

export interface RunOptions {
  single_year: number | null;
  use_all_years: boolean;
  pv_kw_list: number[];
  batt_kwh_list: number[];
}

export interface RunRequest {
  mode: 'single' | 'sweep';
  config: FullConfig;
  run_options: RunOptions;
}

export interface RunResponse {
  run_id: string;
}

export interface RunStatus {
  status: 'queued' | 'running' | 'done' | 'error';
  progress: number;
  message: string;
  metrics?: Record<string, number>;
}

export interface HealthCheck {
  nsrdb_configured: boolean;
  status: string;
}

export interface TimeseriesData {
  index: string[];
  columns: string[];
  data: number[][];
}

export interface SweepData {
  columns: string[];
  data: Record<string, number>[];
}

// Default configuration
export const defaultConfig: FullConfig = {
  site: {
    name: 'Default Site',
    latitude: 31.9686,
    longitude: -99.9018,
    timezone: 'America/Chicago',
    altitude_m: null,
  },
  weather: {
    source: 'nsrdb',
    years: Array.from({ length: 20 }, (_, i) => 2003 + i),
    interval_min: 30,
    leap_day: false,
    cache_dir: './cache',
  },
  pv: {
    surface_tilt_deg: 20.0,
    surface_azimuth_deg: 180.0,
    dc_nameplate_kw: 1.0,
    dc_model: 'pvwatts',
    gamma_pdc_per_c: -0.003,
    mppt_eff: 0.99,
    dc_wiring_eff: 0.99,
  },
  battery: {
    energy_capacity_kwh: 10.0,
    soc_init: 0.5,
    soc_min: 0.05,
    soc_max: 0.95,
    ocv_soc: [0.0, 0.2, 0.5, 0.8, 1.0],
    ocv_v: [3.0, 3.4, 3.65, 3.9, 4.1],
    r_internal_ohm: 0.02,
    i_charge_max_a: 200.0,
    i_discharge_max_a: 200.0,
    charge_eff: 0.97,
    discharge_eff: 0.97,
  },
  gpu: {
    n_gpus: 1,
    p_idle_w: 80.0,
    p_max_w: 700.0,
    flops_peak_per_gpu: 1e15,
    power_exponent: 3.0,
  },
  governor: {
    enabled: true,
    reserve_soc: 0.07,
    safety_factor: 0.95,
    ramp_limit_w_per_step: 200.0,
  },
  sim: {
    dt_min: 30,
    coupling_mode: 'mppt_bus',
  },
};

export const defaultRunOptions: RunOptions = {
  single_year: 2021,
  use_all_years: false,
  pv_kw_list: [0, 0.5, 1, 2, 3, 4, 5],
  batt_kwh_list: [0, 2, 5, 10, 20],
};
