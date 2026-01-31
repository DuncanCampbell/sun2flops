"""Test the simulation engine."""

import pytest
import pandas as pd
import numpy as np

from sun2flops.config import (
    SiteConfig, WeatherConfig, PVConfig, BatteryConfig,
    GPUConfig, GovernorConfig, SimConfig,
)
from sun2flops.data.nsrdb import generate_synthetic_weather
from sun2flops.pv.poa import add_poa_irradiance
from sun2flops.pv.dc_power import pv_dc_power_mpp
from sun2flops.battery.model import BatteryState, step_battery, ocv_from_soc
from sun2flops.gpu.model import gpu_power_w, gpu_flops, u_from_power
from sun2flops.sim.engine import run_simulation
from sun2flops.sweep.runner import run_sweep


@pytest.fixture
def site_config():
    return SiteConfig(
        name="Test Site",
        latitude=31.9686,
        longitude=-99.9018,
        timezone="America/Chicago",
    )


@pytest.fixture
def pv_config():
    return PVConfig(
        surface_tilt_deg=20.0,
        surface_azimuth_deg=180.0,
        dc_nameplate_kw=2.0,
    )


@pytest.fixture
def battery_config():
    return BatteryConfig(
        energy_capacity_kwh=10.0,
        soc_init=0.5,
    )


@pytest.fixture
def gpu_config():
    return GPUConfig(
        n_gpus=1,
        p_idle_w=80.0,
        p_max_w=700.0,
    )


@pytest.fixture
def governor_config():
    return GovernorConfig(enabled=True)


@pytest.fixture
def sim_config():
    return SimConfig(dt_min=30)


@pytest.fixture
def weather(site_config):
    return generate_synthetic_weather(site_config, year=2021)


class TestSyntheticWeather:
    def test_generates_year_of_data(self, site_config):
        weather = generate_synthetic_weather(site_config, year=2021)
        # Should have 48 * 365 = 17520 timesteps
        assert len(weather) == 17520

    def test_has_required_columns(self, site_config):
        weather = generate_synthetic_weather(site_config, year=2021)
        required = ['ghi', 'dni', 'dhi', 'temp_air', 'wind_speed']
        for col in required:
            assert col in weather.columns

    def test_irradiance_non_negative(self, site_config):
        weather = generate_synthetic_weather(site_config, year=2021)
        assert (weather['ghi'] >= 0).all()
        assert (weather['dni'] >= 0).all()


class TestPOA:
    def test_adds_poa_columns(self, weather, site_config, pv_config):
        poa_df = add_poa_irradiance(weather, site_config, pv_config)
        assert 'poa_global' in poa_df.columns
        assert 'temp_cell' in poa_df.columns

    def test_poa_non_negative(self, weather, site_config, pv_config):
        poa_df = add_poa_irradiance(weather, site_config, pv_config)
        assert (poa_df['poa_global'] >= -0.1).all()  # Allow small numerical errors


class TestPVPower:
    def test_produces_power(self, weather, site_config, pv_config):
        poa_df = add_poa_irradiance(weather, site_config, pv_config)
        power = pv_dc_power_mpp(poa_df, pv_config)
        assert (power >= 0).all()
        assert power.max() > 0  # Should produce some power

    def test_power_scales_with_size(self, weather, site_config, pv_config):
        poa_df = add_poa_irradiance(weather, site_config, pv_config)
        power1 = pv_dc_power_mpp(poa_df, pv_config)

        pv_config.dc_nameplate_kw = 4.0  # Double the size
        power2 = pv_dc_power_mpp(poa_df, pv_config)

        # Power should approximately double
        assert abs(power2.sum() / power1.sum() - 2.0) < 0.1


class TestBattery:
    def test_ocv_interpolation(self, battery_config):
        ocv_0 = ocv_from_soc(0.0, battery_config)
        ocv_50 = ocv_from_soc(0.5, battery_config)
        ocv_100 = ocv_from_soc(1.0, battery_config)

        assert ocv_0 < ocv_50 < ocv_100

    def test_charging_increases_soc(self, battery_config):
        state = BatteryState(soc=0.5)
        result = step_battery(state, 1000.0, 1.0, battery_config)  # 1kW for 1 hour
        assert result.soc_next > state.soc

    def test_discharging_decreases_soc(self, battery_config):
        state = BatteryState(soc=0.5)
        result = step_battery(state, -1000.0, 1.0, battery_config)  # -1kW for 1 hour
        assert result.soc_next < state.soc

    def test_soc_limits_respected(self, battery_config):
        # Try to overcharge
        state = BatteryState(soc=0.94)
        result = step_battery(state, 10000.0, 1.0, battery_config)
        assert result.soc_next <= battery_config.soc_max

        # Try to over-discharge
        state = BatteryState(soc=0.06)
        result = step_battery(state, -10000.0, 1.0, battery_config)
        assert result.soc_next >= battery_config.soc_min


class TestGPU:
    def test_power_at_idle(self, gpu_config):
        power = gpu_power_w(0.0, gpu_config)
        assert power == gpu_config.p_idle_w

    def test_power_at_max(self, gpu_config):
        power = gpu_power_w(1.0, gpu_config)
        assert power == gpu_config.p_max_w

    def test_power_curve_is_monotonic(self, gpu_config):
        powers = [gpu_power_w(u, gpu_config) for u in np.linspace(0, 1, 11)]
        assert all(p1 <= p2 for p1, p2 in zip(powers[:-1], powers[1:]))

    def test_u_from_power_inverts_correctly(self, gpu_config):
        for target_u in [0.0, 0.25, 0.5, 0.75, 1.0]:
            power = gpu_power_w(target_u, gpu_config)
            recovered_u = u_from_power(power, gpu_config)
            assert abs(recovered_u - target_u) < 0.01

    def test_flops_scales_with_utilization(self, gpu_config):
        flops_50 = gpu_flops(0.5, 1.0, gpu_config)
        flops_100 = gpu_flops(1.0, 1.0, gpu_config)
        assert abs(flops_100 / flops_50 - 2.0) < 0.01


class TestSimulation:
    def test_simulation_runs(
        self, weather, site_config, pv_config, battery_config,
        gpu_config, governor_config, sim_config
    ):
        result = run_simulation(
            weather=weather,
            site=site_config,
            pv=pv_config,
            batt=battery_config,
            gpu=gpu_config,
            gov=governor_config,
            sim=sim_config,
        )

        assert 'timeseries' in result
        assert 'metrics' in result

    def test_timeseries_has_expected_columns(
        self, weather, site_config, pv_config, battery_config,
        gpu_config, governor_config, sim_config
    ):
        result = run_simulation(
            weather=weather,
            site=site_config,
            pv=pv_config,
            batt=battery_config,
            gpu=gpu_config,
            gov=governor_config,
            sim=sim_config,
        )

        ts = result['timeseries']
        expected_cols = [
            'P_pv_bus_w', 'P_gpu_req_w', 'P_gpu_served_w',
            'P_batt_bus_w', 'soc', 'flops_step'
        ]
        for col in expected_cols:
            assert col in ts.columns

    def test_metrics_has_expected_values(
        self, weather, site_config, pv_config, battery_config,
        gpu_config, governor_config, sim_config
    ):
        result = run_simulation(
            weather=weather,
            site=site_config,
            pv=pv_config,
            batt=battery_config,
            gpu=gpu_config,
            gov=governor_config,
            sim=sim_config,
        )

        metrics = result['metrics']
        assert 'total_flops' in metrics
        assert 'utilization' in metrics
        assert metrics['total_flops'] > 0
        assert 0 <= metrics['utilization'] <= 1


class TestSweep:
    def test_sweep_runs(
        self, weather, site_config, pv_config, battery_config,
        gpu_config, governor_config, sim_config
    ):
        # Small sweep for testing
        result = run_sweep(
            weather=weather,
            site=site_config,
            pv=pv_config,
            batt=battery_config,
            gpu=gpu_config,
            gov=governor_config,
            sim=sim_config,
            pv_kw_list=[0, 1, 2],
            batt_kwh_list=[0, 5, 10],
        )

        assert len(result) == 9  # 3x3 grid
        assert 'pv_kw' in result.columns
        assert 'batt_kwh' in result.columns
        assert 'utilization' in result.columns
