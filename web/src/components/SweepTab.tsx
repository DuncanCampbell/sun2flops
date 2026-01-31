// Sweep tab with heatmaps

import { useMemo } from 'react';
import Plot from 'react-plotly.js';
import type { SweepData } from '../types';

interface SweepTabProps {
  data: SweepData;
}

export function SweepTab({ data }: SweepTabProps) {
  const { utilizationHeatmap, flopsHeatmap } = useMemo(() => {
    // Extract unique PV and battery sizes
    const pvSizes = [...new Set(data.data.map((r) => r.pv_kw))].sort(
      (a, b) => a - b
    );
    const battSizes = [...new Set(data.data.map((r) => r.batt_kwh))].sort(
      (a, b) => a - b
    );

    // Create 2D arrays for heatmaps
    const utilizationMatrix: number[][] = [];
    const flopsMatrix: number[][] = [];

    for (const batt of battSizes) {
      const utilizationRow: number[] = [];
      const flopsRow: number[] = [];

      for (const pv of pvSizes) {
        const row = data.data.find(
          (r) => r.pv_kw === pv && r.batt_kwh === batt
        );
        utilizationRow.push(row ? (row.utilization || 0) * 100 : 0);
        flopsRow.push(row ? row.total_flops || 0 : 0);
      }

      utilizationMatrix.push(utilizationRow);
      flopsMatrix.push(flopsRow);
    }

    return {
      utilizationHeatmap: {
        z: utilizationMatrix,
        x: pvSizes,
        y: battSizes,
      },
      flopsHeatmap: {
        z: flopsMatrix.map((row) => row.map((v) => v / 1e15)), // Convert to PFLOPs
        x: pvSizes,
        y: battSizes,
      },
    };
  }, [data]);

  const commonLayout: Partial<Plotly.Layout> = {
    margin: { l: 60, r: 20, t: 40, b: 50 },
    height: 350,
    paper_bgcolor: 'transparent',
    plot_bgcolor: 'transparent',
    font: { color: '#94a3b8' },
  };

  return (
    <div className="sweep-tab">
      <div className="heatmap-container">
        <Plot
          data={[
            {
              ...utilizationHeatmap,
              type: 'heatmap',
              colorscale: 'Viridis',
              hoverongaps: false,
              hovertemplate:
                'PV: %{x} kW<br>Battery: %{y} kWh<br>Utilization: %{z:.1f}%<extra></extra>',
            },
          ]}
          layout={{
            ...commonLayout,
            title: { text: 'GPU Utilization (%)' },
            xaxis: { title: { text: 'PV Size (kW)' } },
            yaxis: { title: { text: 'Battery Size (kWh)' } },
          }}
          config={{ responsive: true }}
          style={{ width: '100%' }}
        />
      </div>

      <div className="heatmap-container">
        <Plot
          data={[
            {
              ...flopsHeatmap,
              type: 'heatmap',
              colorscale: 'Plasma',
              hoverongaps: false,
              hovertemplate:
                'PV: %{x} kW<br>Battery: %{y} kWh<br>FLOPs: %{z:.2f} PFLOPs<extra></extra>',
            },
          ]}
          layout={{
            ...commonLayout,
            title: { text: 'Total FLOPs (PFLOPs)' },
            xaxis: { title: { text: 'PV Size (kW)' } },
            yaxis: { title: { text: 'Battery Size (kWh)' } },
          }}
          config={{ responsive: true }}
          style={{ width: '100%' }}
        />
      </div>

      {/* Sweep results table */}
      <div className="sweep-table-container">
        <h4>Sweep Results</h4>
        <table className="sweep-table">
          <thead>
            <tr>
              <th>PV (kW)</th>
              <th>Battery (kWh)</th>
              <th>Utilization</th>
              <th>Total FLOPs</th>
              <th>Unserved Hours</th>
              <th>Curtailment</th>
            </tr>
          </thead>
          <tbody>
            {data.data.map((row, i) => (
              <tr key={i}>
                <td>{row.pv_kw}</td>
                <td>{row.batt_kwh}</td>
                <td>{((row.utilization || 0) * 100).toFixed(1)}%</td>
                <td>{((row.total_flops || 0) / 1e15).toFixed(2)} PFLOPs</td>
                <td>{(row.hours_unserved || 0).toFixed(1)} hrs</td>
                <td>{((row.curtailment_fraction || 0) * 100).toFixed(1)}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
