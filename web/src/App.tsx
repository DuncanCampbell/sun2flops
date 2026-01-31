import { useState } from 'react';
import { QueryClient, QueryClientProvider, useQuery } from '@tanstack/react-query';
import { api } from './api/client';
import { ConfigForm } from './components/ConfigForm';
import { Results } from './components/Results';
import { useSimulation } from './hooks/useSimulation';
import type { FullConfig, RunOptions } from './types';
import { defaultConfig, defaultRunOptions } from './types';
import './App.css';

const queryClient = new QueryClient();

function AppContent() {
  const [config, setConfig] = useState<FullConfig>(defaultConfig);
  const [runOptions, setRunOptions] = useState<RunOptions>(defaultRunOptions);

  const {
    runId,
    status,
    isRunning,
    error,
    timeseries,
    sweep,
    runSingle,
    runSweep,
  } = useSimulation();

  // Health check
  const { data: health } = useQuery({
    queryKey: ['health'],
    queryFn: api.health,
    refetchInterval: 30000,
  });

  const handleRunSingle = async () => {
    await runSingle(config, runOptions);
  };

  const handleRunSweep = async () => {
    await runSweep(config, runOptions);
  };

  return (
    <div className="app">
      <header className="app-header">
        <h1>Sun2FLOPs</h1>
        <span className="subtitle">Solar to GPU Compute Simulation</span>
        <div className="health-status">
          {health?.nsrdb_configured ? (
            <span className="status-ok">NSRDB configured</span>
          ) : (
            <span className="status-warn">Using synthetic data (NSRDB not configured)</span>
          )}
        </div>
      </header>

      <main className="app-main">
        <div className="panel panel-left">
          <h2>Configuration</h2>
          <ConfigForm
            config={config}
            runOptions={runOptions}
            onConfigChange={setConfig}
            onRunOptionsChange={setRunOptions}
            onRunSingle={handleRunSingle}
            onRunSweep={handleRunSweep}
            isRunning={isRunning}
          />
        </div>

        <div className="panel panel-right">
          <h2>Results</h2>
          <Results
            status={status}
            timeseries={timeseries}
            sweep={sweep}
            runId={runId}
            error={error}
          />
        </div>
      </main>

      <footer className="app-footer">
        <p>Sun2FLOPs - DC-only solar compute simulation</p>
      </footer>
    </div>
  );
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AppContent />
    </QueryClientProvider>
  );
}

export default App;
