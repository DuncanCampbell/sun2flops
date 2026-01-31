// API client for sun2flops backend

import type {
  RunRequest,
  RunResponse,
  RunStatus,
  HealthCheck,
  TimeseriesData,
  SweepData,
  FullConfig,
} from '../types';

// When running with Vite proxy, use empty string for relative URLs
// Otherwise use the environment variable or fallback
const API_BASE = import.meta.env.VITE_API_URL || '';

async function fetchJson<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${url}`, {
    headers: {
      'Content-Type': 'application/json',
    },
    ...options,
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`API error: ${response.status} - ${error}`);
  }

  return response.json();
}

export const api = {
  // Health check
  health: (): Promise<HealthCheck> => fetchJson('/api/health'),

  // Get default configuration
  defaults: (): Promise<FullConfig> => fetchJson('/api/defaults'),

  // Create a new run
  createRun: (request: RunRequest): Promise<RunResponse> =>
    fetchJson('/api/runs', {
      method: 'POST',
      body: JSON.stringify(request),
    }),

  // Get run status
  getRunStatus: (runId: string): Promise<RunStatus> =>
    fetchJson(`/api/runs/${runId}`),

  // Get timeseries data
  getTimeseries: (runId: string): Promise<TimeseriesData> =>
    fetchJson(`/api/runs/${runId}/timeseries`),

  // Get sweep results
  getSweep: (runId: string): Promise<SweepData> =>
    fetchJson(`/api/runs/${runId}/sweep`),

  // Download URLs
  getDownloadUrl: (runId: string, artifact: string): string =>
    `${API_BASE}/api/runs/${runId}/download/${artifact}`,
};
