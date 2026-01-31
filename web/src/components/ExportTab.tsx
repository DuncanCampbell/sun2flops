// Export tab for downloading results

import { api } from '../api/client';

interface ExportTabProps {
  runId: string | null;
  hasSweep: boolean;
}

export function ExportTab({ runId, hasSweep }: ExportTabProps) {
  if (!runId) {
    return <div className="export-tab">No run to export.</div>;
  }

  const downloads = [
    {
      name: 'Timeseries CSV',
      artifact: 'timeseries.csv',
      description: 'Time series data for all simulation variables',
    },
    ...(hasSweep
      ? [
          {
            name: 'Sweep CSV',
            artifact: 'sweep.csv',
            description: 'Sweep results for all parameter combinations',
          },
        ]
      : []),
    {
      name: 'Metrics JSON',
      artifact: 'metrics.json',
      description: 'Summary metrics from the simulation',
    },
    {
      name: 'Config JSON',
      artifact: 'config.json',
      description: 'Configuration used for this run',
    },
  ];

  return (
    <div className="export-tab">
      <h4>Download Results</h4>
      <p>Download simulation results in various formats.</p>

      <div className="download-list">
        {downloads.map((dl) => (
          <div key={dl.artifact} className="download-item">
            <div className="download-info">
              <span className="download-name">{dl.name}</span>
              <span className="download-description">{dl.description}</span>
            </div>
            <a
              href={api.getDownloadUrl(runId, dl.artifact)}
              download={dl.artifact}
              className="btn btn-small"
            >
              Download
            </a>
          </div>
        ))}
      </div>
    </div>
  );
}
