// Hook for managing simulation runs

import { useState, useCallback, useEffect } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { api } from '../api/client';
import type {
  FullConfig,
  RunOptions,
  RunStatus,
  TimeseriesData,
  SweepData,
} from '../types';

interface UseSimulationResult {
  // State
  runId: string | null;
  status: RunStatus | null;
  isRunning: boolean;
  error: string | null;

  // Data
  timeseries: TimeseriesData | null;
  sweep: SweepData | null;

  // Actions
  runSingle: (config: FullConfig, options: RunOptions) => Promise<void>;
  runSweep: (config: FullConfig, options: RunOptions) => Promise<void>;
  reset: () => void;
}

export function useSimulation(): UseSimulationResult {
  const [runId, setRunId] = useState<string | null>(null);
  const [status, setStatus] = useState<RunStatus | null>(null);
  const [timeseries, setTimeseries] = useState<TimeseriesData | null>(null);
  const [sweep, setSweep] = useState<SweepData | null>(null);
  const [error, setError] = useState<string | null>(null);

  const isRunning = status?.status === 'queued' || status?.status === 'running';

  // Create run mutation
  const createRunMutation = useMutation({
    mutationFn: api.createRun,
    onSuccess: (data) => {
      setRunId(data.run_id);
      setStatus({ status: 'queued', progress: 0, message: 'Run queued' });
      setError(null);
    },
    onError: (err: Error) => {
      setError(err.message);
    },
  });

  // Poll for status when running
  const { data: pollStatus } = useQuery({
    queryKey: ['runStatus', runId],
    queryFn: () => api.getRunStatus(runId!),
    enabled: !!runId && isRunning,
    refetchInterval: 1000, // Poll every second
  });

  // Update status when poll returns
  useEffect(() => {
    if (pollStatus) {
      setStatus(pollStatus);
    }
  }, [pollStatus]);

  // Fetch timeseries when done
  const { data: timeseriesData } = useQuery({
    queryKey: ['timeseries', runId],
    queryFn: () => api.getTimeseries(runId!),
    enabled: !!runId && status?.status === 'done',
    staleTime: Infinity, // Don't refetch
  });

  useEffect(() => {
    if (timeseriesData) {
      setTimeseries(timeseriesData);
    }
  }, [timeseriesData]);

  // Fetch sweep when done
  const { data: sweepData } = useQuery({
    queryKey: ['sweep', runId],
    queryFn: () => api.getSweep(runId!),
    enabled: !!runId && status?.status === 'done',
    staleTime: Infinity,
    retry: false, // Don't retry if not found (single runs don't have sweep)
  });

  useEffect(() => {
    if (sweepData) {
      setSweep(sweepData);
    }
  }, [sweepData]);

  // Actions
  const runSingle = useCallback(
    async (config: FullConfig, options: RunOptions) => {
      setTimeseries(null);
      setSweep(null);
      await createRunMutation.mutateAsync({
        mode: 'single',
        config,
        run_options: options,
      });
    },
    [createRunMutation]
  );

  const runSweep = useCallback(
    async (config: FullConfig, options: RunOptions) => {
      setTimeseries(null);
      setSweep(null);
      await createRunMutation.mutateAsync({
        mode: 'sweep',
        config,
        run_options: options,
      });
    },
    [createRunMutation]
  );

  const reset = useCallback(() => {
    setRunId(null);
    setStatus(null);
    setTimeseries(null);
    setSweep(null);
    setError(null);
  }, []);

  return {
    runId,
    status,
    isRunning,
    error,
    timeseries,
    sweep,
    runSingle,
    runSweep,
    reset,
  };
}
