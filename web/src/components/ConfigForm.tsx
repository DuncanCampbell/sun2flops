// Configuration form component

import type { FullConfig, RunOptions } from '../types';

interface ConfigFormProps {
  config: FullConfig;
  runOptions: RunOptions;
  onConfigChange: (config: FullConfig) => void;
  onRunOptionsChange: (options: RunOptions) => void;
  onRunSingle: () => void;
  onRunSweep: () => void;
  isRunning: boolean;
}

export function ConfigForm({
  config,
  runOptions,
  onConfigChange,
  onRunOptionsChange,
  onRunSingle,
  onRunSweep,
  isRunning,
}: ConfigFormProps) {
  const updateSite = (updates: Partial<typeof config.site>) => {
    onConfigChange({
      ...config,
      site: { ...config.site, ...updates },
    });
  };

  const updatePV = (updates: Partial<typeof config.pv>) => {
    onConfigChange({
      ...config,
      pv: { ...config.pv, ...updates },
    });
  };

  const updateBattery = (updates: Partial<typeof config.battery>) => {
    onConfigChange({
      ...config,
      battery: { ...config.battery, ...updates },
    });
  };

  const updateGPU = (updates: Partial<typeof config.gpu>) => {
    onConfigChange({
      ...config,
      gpu: { ...config.gpu, ...updates },
    });
  };

  const updateGovernor = (updates: Partial<typeof config.governor>) => {
    onConfigChange({
      ...config,
      governor: { ...config.governor, ...updates },
    });
  };

  return (
    <div className="config-form">
      {/* Site Configuration */}
      <section className="form-section">
        <h3>Site</h3>
        <div className="form-row">
          <label>
            Latitude
            <input
              type="number"
              step="0.0001"
              value={config.site.latitude}
              onChange={(e) => updateSite({ latitude: parseFloat(e.target.value) })}
            />
          </label>
          <label>
            Longitude
            <input
              type="number"
              step="0.0001"
              value={config.site.longitude}
              onChange={(e) => updateSite({ longitude: parseFloat(e.target.value) })}
            />
          </label>
        </div>
        <div className="form-row">
          <label>
            Timezone
            <select
              value={config.site.timezone}
              onChange={(e) => updateSite({ timezone: e.target.value })}
            >
              <option value="America/New_York">America/New_York</option>
              <option value="America/Chicago">America/Chicago</option>
              <option value="America/Denver">America/Denver</option>
              <option value="America/Los_Angeles">America/Los_Angeles</option>
              <option value="America/Phoenix">America/Phoenix</option>
              <option value="UTC">UTC</option>
            </select>
          </label>
        </div>
      </section>

      {/* Weather Configuration */}
      <section className="form-section">
        <h3>Weather</h3>
        <div className="form-row">
          <label>
            Year
            <input
              type="number"
              min={2003}
              max={2022}
              value={runOptions.single_year || 2021}
              onChange={(e) =>
                onRunOptionsChange({
                  ...runOptions,
                  single_year: parseInt(e.target.value),
                })
              }
            />
          </label>
        </div>
      </section>

      {/* PV Configuration */}
      <section className="form-section">
        <h3>PV System</h3>
        <div className="form-row">
          <label>
            DC Size (kW)
            <input
              type="number"
              step="0.1"
              min={0}
              value={config.pv.dc_nameplate_kw}
              onChange={(e) => updatePV({ dc_nameplate_kw: parseFloat(e.target.value) })}
            />
          </label>
        </div>
        <div className="form-row">
          <label>
            Tilt (deg)
            <input
              type="number"
              step="1"
              min={0}
              max={90}
              value={config.pv.surface_tilt_deg}
              onChange={(e) => updatePV({ surface_tilt_deg: parseFloat(e.target.value) })}
            />
          </label>
          <label>
            Azimuth (deg)
            <input
              type="number"
              step="1"
              min={0}
              max={360}
              value={config.pv.surface_azimuth_deg}
              onChange={(e) => updatePV({ surface_azimuth_deg: parseFloat(e.target.value) })}
            />
          </label>
        </div>
        <div className="form-row">
          <label>
            MPPT Efficiency
            <input
              type="number"
              step="0.01"
              min={0.9}
              max={1}
              value={config.pv.mppt_eff}
              onChange={(e) => updatePV({ mppt_eff: parseFloat(e.target.value) })}
            />
          </label>
          <label>
            Wiring Efficiency
            <input
              type="number"
              step="0.01"
              min={0.9}
              max={1}
              value={config.pv.dc_wiring_eff}
              onChange={(e) => updatePV({ dc_wiring_eff: parseFloat(e.target.value) })}
            />
          </label>
        </div>
      </section>

      {/* Battery Configuration */}
      <section className="form-section">
        <h3>Battery</h3>
        <div className="form-row">
          <label>
            Capacity (kWh)
            <input
              type="number"
              step="0.5"
              min={0}
              value={config.battery.energy_capacity_kwh}
              onChange={(e) =>
                updateBattery({ energy_capacity_kwh: parseFloat(e.target.value) })
              }
            />
          </label>
        </div>
        <div className="form-row">
          <label>
            Initial SOC
            <input
              type="number"
              step="0.05"
              min={0}
              max={1}
              value={config.battery.soc_init}
              onChange={(e) => updateBattery({ soc_init: parseFloat(e.target.value) })}
            />
          </label>
          <label>
            Min SOC
            <input
              type="number"
              step="0.05"
              min={0}
              max={1}
              value={config.battery.soc_min}
              onChange={(e) => updateBattery({ soc_min: parseFloat(e.target.value) })}
            />
          </label>
          <label>
            Max SOC
            <input
              type="number"
              step="0.05"
              min={0}
              max={1}
              value={config.battery.soc_max}
              onChange={(e) => updateBattery({ soc_max: parseFloat(e.target.value) })}
            />
          </label>
        </div>
        <div className="form-row">
          <label>
            Charge Efficiency
            <input
              type="number"
              step="0.01"
              min={0.8}
              max={1}
              value={config.battery.charge_eff}
              onChange={(e) => updateBattery({ charge_eff: parseFloat(e.target.value) })}
            />
          </label>
          <label>
            Discharge Efficiency
            <input
              type="number"
              step="0.01"
              min={0.8}
              max={1}
              value={config.battery.discharge_eff}
              onChange={(e) =>
                updateBattery({ discharge_eff: parseFloat(e.target.value) })
              }
            />
          </label>
        </div>
      </section>

      {/* GPU Configuration */}
      <section className="form-section">
        <h3>GPU (H100-like)</h3>
        <div className="form-row">
          <label>
            Number of GPUs
            <input
              type="number"
              step="1"
              min={1}
              max={8}
              value={config.gpu.n_gpus}
              onChange={(e) => updateGPU({ n_gpus: parseInt(e.target.value) })}
            />
          </label>
        </div>
        <div className="form-row">
          <label>
            Idle Power (W)
            <input
              type="number"
              step="10"
              min={0}
              value={config.gpu.p_idle_w}
              onChange={(e) => updateGPU({ p_idle_w: parseFloat(e.target.value) })}
            />
          </label>
          <label>
            Max Power (W)
            <input
              type="number"
              step="10"
              min={0}
              value={config.gpu.p_max_w}
              onChange={(e) => updateGPU({ p_max_w: parseFloat(e.target.value) })}
            />
          </label>
        </div>
      </section>

      {/* Governor Configuration */}
      <section className="form-section">
        <h3>Governor</h3>
        <div className="form-row">
          <label className="checkbox-label">
            <input
              type="checkbox"
              checked={config.governor.enabled}
              onChange={(e) => updateGovernor({ enabled: e.target.checked })}
            />
            Enabled
          </label>
        </div>
        <div className="form-row">
          <label>
            Reserve SOC
            <input
              type="number"
              step="0.01"
              min={0}
              max={0.5}
              value={config.governor.reserve_soc}
              onChange={(e) =>
                updateGovernor({ reserve_soc: parseFloat(e.target.value) })
              }
            />
          </label>
          <label>
            Safety Factor
            <input
              type="number"
              step="0.05"
              min={0.5}
              max={1}
              value={config.governor.safety_factor}
              onChange={(e) =>
                updateGovernor({ safety_factor: parseFloat(e.target.value) })
              }
            />
          </label>
        </div>
        <div className="form-row">
          <label>
            Ramp Limit (W/step)
            <input
              type="number"
              step="50"
              min={0}
              value={config.governor.ramp_limit_w_per_step}
              onChange={(e) =>
                updateGovernor({ ramp_limit_w_per_step: parseFloat(e.target.value) })
              }
            />
          </label>
        </div>
      </section>

      {/* Sweep Configuration */}
      <section className="form-section">
        <h3>Sweep Parameters</h3>
        <div className="form-row">
          <label>
            PV Sizes (kW, comma-separated)
            <input
              type="text"
              value={runOptions.pv_kw_list.join(', ')}
              onChange={(e) =>
                onRunOptionsChange({
                  ...runOptions,
                  pv_kw_list: e.target.value.split(',').map((s) => parseFloat(s.trim())),
                })
              }
            />
          </label>
        </div>
        <div className="form-row">
          <label>
            Battery Sizes (kWh, comma-separated)
            <input
              type="text"
              value={runOptions.batt_kwh_list.join(', ')}
              onChange={(e) =>
                onRunOptionsChange({
                  ...runOptions,
                  batt_kwh_list: e.target.value.split(',').map((s) => parseFloat(s.trim())),
                })
              }
            />
          </label>
        </div>
      </section>

      {/* Run Buttons */}
      <section className="form-actions">
        <button
          className="btn btn-primary"
          onClick={onRunSingle}
          disabled={isRunning}
        >
          {isRunning ? 'Running...' : 'Run Single'}
        </button>
        <button
          className="btn btn-secondary"
          onClick={onRunSweep}
          disabled={isRunning}
        >
          {isRunning ? 'Running...' : 'Run Sweep'}
        </button>
      </section>
    </div>
  );
}
