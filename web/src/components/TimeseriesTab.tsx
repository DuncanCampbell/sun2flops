// Timeseries tab with Plotly charts

import { useState, useMemo } from 'react';
import Plot from 'react-plotly.js';
import type { TimeseriesData } from '../types';

interface TimeseriesTabProps {
  data: TimeseriesData;
}

export function TimeseriesTab({ data }: TimeseriesTabProps) {
  const [range, setRange] = useState<[number, number] | null>(null);

  // Convert data to Plotly format
  const traces = useMemo(() => {
    const timestamps = data.index;
    const getColumn = (name: string): number[] | null => {
      const idx = data.columns.indexOf(name);
      if (idx === -1) return null;
      return data.data.map((row) => row[idx]);
    };

    // Apply range filter if set
    let filteredTimestamps = timestamps;
    let startIdx = 0;
    let endIdx = timestamps.length;

    if (range) {
      startIdx = range[0];
      endIdx = range[1];
      filteredTimestamps = timestamps.slice(startIdx, endIdx);
    }

    const sliceData = (arr: number[] | null) =>
      arr ? arr.slice(startIdx, endIdx) : null;

    return {
      timestamps: filteredTimestamps,
      pv_bus: sliceData(getColumn('P_pv_bus_w'))?.map((v) => v / 1000),
      gpu_served: sliceData(getColumn('P_gpu_served_w'))?.map((v) => v / 1000),
      gpu_req: sliceData(getColumn('P_gpu_req_w'))?.map((v) => v / 1000),
      batt_bus: sliceData(getColumn('P_batt_bus_w'))?.map((v) => v / 1000),
      soc: sliceData(getColumn('soc'))?.map((v) => v * 100),
    };
  }, [data, range]);

  // Quick select winter window
  const selectWinterWindow = () => {
    // Find a 10-day window in winter (January or December)
    const windowDays = 10;
    const stepsPerDay = 48; // 30-min intervals
    const windowSteps = windowDays * stepsPerDay;

    // Find January dates
    let startIdx = 0;
    for (let i = 0; i < data.index.length; i++) {
      const date = new Date(data.index[i]);
      if (date.getMonth() === 0 && date.getDate() === 15) {
        // Mid-January
        startIdx = Math.max(0, i - Math.floor(windowSteps / 2));
        break;
      }
    }

    setRange([startIdx, Math.min(startIdx + windowSteps, data.index.length)]);
  };

  const resetRange = () => setRange(null);

  const commonLayout: Partial<Plotly.Layout> = {
    margin: { l: 50, r: 20, t: 30, b: 40 },
    height: 200,
    showlegend: true,
    legend: { orientation: 'h', y: 1.1 },
    paper_bgcolor: 'transparent',
    plot_bgcolor: 'transparent',
    font: { color: '#94a3b8' },
    xaxis: { gridcolor: '#334155' },
    yaxis: { gridcolor: '#334155' },
  };

  return (
    <div className="timeseries-tab">
      <div className="chart-controls">
        <button className="btn btn-small" onClick={selectWinterWindow}>
          10-Day Winter Window
        </button>
        <button className="btn btn-small" onClick={resetRange}>
          Reset Zoom
        </button>
        <span className="data-points">
          Showing {traces.timestamps.length.toLocaleString()} points
        </span>
      </div>

      {/* PV Power Chart */}
      <div className="chart-container">
        <Plot
          data={[
            {
              x: traces.timestamps,
              y: traces.pv_bus || [],
              type: 'scatter',
              mode: 'lines',
              name: 'PV Bus Power',
              line: { color: '#f59e0b', width: 1 },
            },
          ]}
          layout={{
            ...commonLayout,
            title: { text: 'PV Bus Power (kW)' },
            yaxis: { ...commonLayout.yaxis, title: { text: 'kW' } },
          }}
          config={{ responsive: true }}
          style={{ width: '100%' }}
        />
      </div>

      {/* GPU Power Chart */}
      <div className="chart-container">
        <Plot
          data={[
            {
              x: traces.timestamps,
              y: traces.gpu_req || [],
              type: 'scatter',
              mode: 'lines',
              name: 'GPU Requested',
              line: { color: '#94a3b8', width: 1 },
            },
            {
              x: traces.timestamps,
              y: traces.gpu_served || [],
              type: 'scatter',
              mode: 'lines',
              name: 'GPU Served',
              line: { color: '#22c55e', width: 1 },
            },
          ]}
          layout={{
            ...commonLayout,
            title: { text: 'GPU Power (kW)' },
            yaxis: { ...commonLayout.yaxis, title: { text: 'kW' } },
          }}
          config={{ responsive: true }}
          style={{ width: '100%' }}
        />
      </div>

      {/* Battery Power Chart */}
      <div className="chart-container">
        <Plot
          data={[
            {
              x: traces.timestamps,
              y: traces.batt_bus || [],
              type: 'scatter',
              mode: 'lines',
              name: 'Battery Power',
              line: { color: '#3b82f6', width: 1 },
              fill: 'tozeroy',
            },
          ]}
          layout={{
            ...commonLayout,
            title: { text: 'Battery Bus Power (kW) (+charge / -discharge)' },
            yaxis: { ...commonLayout.yaxis, title: { text: 'kW' } },
          }}
          config={{ responsive: true }}
          style={{ width: '100%' }}
        />
      </div>

      {/* SOC Chart */}
      <div className="chart-container">
        <Plot
          data={[
            {
              x: traces.timestamps,
              y: traces.soc || [],
              type: 'scatter',
              mode: 'lines',
              name: 'SOC',
              line: { color: '#8b5cf6', width: 1 },
              fill: 'tozeroy',
            },
          ]}
          layout={{
            ...commonLayout,
            title: { text: 'Battery State of Charge (%)' },
            yaxis: { ...commonLayout.yaxis, title: { text: '%' }, range: [0, 100] },
          }}
          config={{ responsive: true }}
          style={{ width: '100%' }}
        />
      </div>
    </div>
  );
}
