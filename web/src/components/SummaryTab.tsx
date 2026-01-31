// Summary tab with KPI cards


interface SummaryTabProps {
  metrics?: Record<string, number>;
}

function formatNumber(value: number, decimals: number = 2): string {
  if (Math.abs(value) >= 1e12) {
    return (value / 1e12).toFixed(decimals) + ' T';
  }
  if (Math.abs(value) >= 1e9) {
    return (value / 1e9).toFixed(decimals) + ' G';
  }
  if (Math.abs(value) >= 1e6) {
    return (value / 1e6).toFixed(decimals) + ' M';
  }
  if (Math.abs(value) >= 1e3) {
    return (value / 1e3).toFixed(decimals) + ' k';
  }
  return value.toFixed(decimals);
}

function formatFlops(value: number): string {
  if (value >= 1e18) {
    return (value / 1e18).toFixed(2) + ' EFLOPs';
  }
  if (value >= 1e15) {
    return (value / 1e15).toFixed(2) + ' PFLOPs';
  }
  if (value >= 1e12) {
    return (value / 1e12).toFixed(2) + ' TFLOPs';
  }
  return formatNumber(value) + ' FLOPs';
}

export function SummaryTab({ metrics }: SummaryTabProps) {
  if (!metrics) {
    return <div className="summary-tab">No metrics available.</div>;
  }

  const cards = [
    {
      label: 'Total FLOPs',
      value: formatFlops(metrics.total_flops || 0),
      description: 'Total floating point operations',
    },
    {
      label: 'GPU Utilization',
      value: ((metrics.utilization || 0) * 100).toFixed(1) + '%',
      description: 'Average GPU utilization',
    },
    {
      label: 'Unserved Hours',
      value: (metrics.hours_unserved || 0).toFixed(1) + ' hrs',
      description: 'Hours with unmet demand',
    },
    {
      label: 'Curtailment',
      value: ((metrics.curtailment_fraction || 0) * 100).toFixed(1) + '%',
      description: 'PV energy curtailed',
    },
    {
      label: 'PV Energy',
      value: (metrics.total_pv_energy_kwh || 0).toFixed(1) + ' kWh',
      description: 'Total PV energy generated',
    },
    {
      label: 'GPU Energy',
      value: (metrics.total_gpu_energy_kwh || 0).toFixed(1) + ' kWh',
      description: 'Total GPU energy consumed',
    },
    {
      label: 'Peak PV',
      value: (metrics.peak_pv_kw || 0).toFixed(2) + ' kW',
      description: 'Peak PV output',
    },
    {
      label: 'Battery Cycles',
      value: (metrics.battery_equivalent_cycles || 0).toFixed(1),
      description: 'Equivalent full cycles',
    },
  ];

  return (
    <div className="summary-tab">
      <div className="kpi-grid">
        {cards.map((card) => (
          <div key={card.label} className="kpi-card">
            <div className="kpi-value">{card.value}</div>
            <div className="kpi-label">{card.label}</div>
            <div className="kpi-description">{card.description}</div>
          </div>
        ))}
      </div>

      {/* Warnings */}
      <div className="warnings">
        {metrics.battery_capacity_kwh === 0 && (
          <div className="warning">
            Battery capacity is 0 - no overnight compute possible
          </div>
        )}
        {metrics.pv_nameplate_kw === 0 && (
          <div className="warning">PV size is 0 - no solar energy available</div>
        )}
        {(metrics.hours_unserved || 0) > metrics.total_hours * 0.1 && (
          <div className="warning">
            High unserved hours - consider larger PV or battery
          </div>
        )}
      </div>
    </div>
  );
}
