// Results display component with tabs

import { useState } from 'react';
import type { RunStatus, TimeseriesData, SweepData } from '../types';
import { SummaryTab } from './SummaryTab';
import { TimeseriesTab } from './TimeseriesTab';
import { SweepTab } from './SweepTab';
import { ExportTab } from './ExportTab';

interface ResultsProps {
  status: RunStatus | null;
  timeseries: TimeseriesData | null;
  sweep: SweepData | null;
  runId: string | null;
  error: string | null;
}

type TabId = 'summary' | 'timeseries' | 'sweep' | 'export';

export function Results({ status, timeseries, sweep, runId, error }: ResultsProps) {
  const [activeTab, setActiveTab] = useState<TabId>('summary');

  if (error) {
    return (
      <div className="results error-state">
        <h3>Error</h3>
        <pre className="error-message">{error}</pre>
      </div>
    );
  }

  if (!status) {
    return (
      <div className="results empty-state">
        <p>Configure parameters and click Run to start a simulation.</p>
      </div>
    );
  }

  if (status.status === 'queued' || status.status === 'running') {
    return (
      <div className="results loading-state">
        <div className="progress-container">
          <div className="progress-bar">
            <div
              className="progress-fill"
              style={{ width: `${status.progress}%` }}
            />
          </div>
          <p className="progress-message">{status.message}</p>
          <p className="progress-percent">{status.progress}%</p>
        </div>
      </div>
    );
  }

  if (status.status === 'error') {
    return (
      <div className="results error-state">
        <h3>Simulation Error</h3>
        <pre className="error-message">{status.message}</pre>
      </div>
    );
  }

  // Done state - show results
  return (
    <div className="results">
      <div className="tabs">
        <button
          className={`tab ${activeTab === 'summary' ? 'active' : ''}`}
          onClick={() => setActiveTab('summary')}
        >
          Summary
        </button>
        <button
          className={`tab ${activeTab === 'timeseries' ? 'active' : ''}`}
          onClick={() => setActiveTab('timeseries')}
          disabled={!timeseries}
        >
          Timeseries
        </button>
        <button
          className={`tab ${activeTab === 'sweep' ? 'active' : ''}`}
          onClick={() => setActiveTab('sweep')}
          disabled={!sweep}
        >
          Sweep
        </button>
        <button
          className={`tab ${activeTab === 'export' ? 'active' : ''}`}
          onClick={() => setActiveTab('export')}
        >
          Export
        </button>
      </div>

      <div className="tab-content">
        {activeTab === 'summary' && <SummaryTab metrics={status.metrics} />}
        {activeTab === 'timeseries' && timeseries && (
          <TimeseriesTab data={timeseries} />
        )}
        {activeTab === 'sweep' && sweep && <SweepTab data={sweep} />}
        {activeTab === 'export' && <ExportTab runId={runId} hasSweep={!!sweep} />}
      </div>
    </div>
  );
}
