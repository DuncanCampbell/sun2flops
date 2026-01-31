"""FastAPI application for sun2flops."""

import json
import os
import uuid
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from api.schemas import (
    RunRequestSchema,
    RunResponseSchema,
    RunStatusSchema,
    HealthCheckSchema,
    TimeseriesResponseSchema,
    SweepResponseSchema,
    FullConfigSchema,
)
from api.tasks import run_simulation_task, run_sweep_task

app = FastAPI(
    title="Sun2FLOPs API",
    description="Solar to GPU compute simulation API",
    version="0.1.0",
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Artifacts directory
ARTIFACTS_DIR = Path("./artifacts")
ARTIFACTS_DIR.mkdir(exist_ok=True)


def get_run_dir(run_id: str) -> Path:
    """Get the artifacts directory for a run."""
    return ARTIFACTS_DIR / run_id


def check_nsrdb_configured() -> bool:
    """Check if NSRDB credentials are configured."""
    api_key = os.environ.get("NSRDB_API_KEY", "")
    email = os.environ.get("NSRDB_EMAIL", "")
    return bool(api_key and email)


@app.get("/api/health", response_model=HealthCheckSchema)
async def health_check():
    """Health check endpoint."""
    return HealthCheckSchema(
        nsrdb_configured=check_nsrdb_configured(),
        status="ok",
    )


@app.post("/api/runs", response_model=RunResponseSchema)
async def create_run(request: RunRequestSchema, background_tasks: BackgroundTasks):
    """
    Create a new simulation run.

    For single runs, executes synchronously if fast.
    For sweeps, always queues async.
    """
    run_id = str(uuid.uuid4())
    run_dir = get_run_dir(run_id)
    run_dir.mkdir(parents=True, exist_ok=True)

    # Save initial status
    status = RunStatusSchema(status="queued", progress=0, message="Run queued")
    with open(run_dir / "status.json", "w") as f:
        json.dump(status.model_dump(), f)

    # Save config
    with open(run_dir / "config.json", "w") as f:
        json.dump(request.config.model_dump(), f, indent=2)

    # Save run options
    with open(run_dir / "run_options.json", "w") as f:
        json.dump(request.run_options.model_dump(), f, indent=2)

    # Queue the task
    if request.mode == "single":
        background_tasks.add_task(
            run_simulation_task,
            run_id=run_id,
            config=request.config,
            run_options=request.run_options,
        )
    else:
        background_tasks.add_task(
            run_sweep_task,
            run_id=run_id,
            config=request.config,
            run_options=request.run_options,
        )

    return RunResponseSchema(run_id=run_id)


@app.get("/api/runs/{run_id}", response_model=RunStatusSchema)
async def get_run_status(run_id: str):
    """Get the status of a run."""
    run_dir = get_run_dir(run_id)
    status_file = run_dir / "status.json"

    if not status_file.exists():
        raise HTTPException(status_code=404, detail="Run not found")

    with open(status_file, "r") as f:
        status_data = json.load(f)

    # Include metrics if available
    metrics_file = run_dir / "metrics.json"
    if metrics_file.exists() and status_data.get("status") == "done":
        with open(metrics_file, "r") as f:
            status_data["metrics"] = json.load(f)

    return RunStatusSchema(**status_data)


@app.get("/api/runs/{run_id}/timeseries")
async def get_timeseries(run_id: str):
    """Get timeseries data for a run."""
    run_dir = get_run_dir(run_id)
    ts_file = run_dir / "timeseries.json"

    if not ts_file.exists():
        raise HTTPException(status_code=404, detail="Timeseries not found")

    with open(ts_file, "r") as f:
        data = json.load(f)

    return JSONResponse(content=data)


@app.get("/api/runs/{run_id}/sweep")
async def get_sweep_results(run_id: str):
    """Get sweep results for a run."""
    run_dir = get_run_dir(run_id)
    sweep_file = run_dir / "sweep.json"

    if not sweep_file.exists():
        raise HTTPException(status_code=404, detail="Sweep results not found")

    with open(sweep_file, "r") as f:
        data = json.load(f)

    return JSONResponse(content=data)


@app.get("/api/runs/{run_id}/download/{artifact}")
async def download_artifact(run_id: str, artifact: str):
    """Download an artifact file."""
    allowed_artifacts = ["timeseries.csv", "sweep.csv", "metrics.json", "config.json"]

    if artifact not in allowed_artifacts:
        raise HTTPException(status_code=400, detail=f"Invalid artifact: {artifact}")

    run_dir = get_run_dir(run_id)
    file_path = run_dir / artifact

    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"Artifact not found: {artifact}")

    return FileResponse(
        path=file_path,
        filename=artifact,
        media_type="application/octet-stream",
    )


@app.get("/api/defaults")
async def get_defaults():
    """Get default configuration values."""
    return FullConfigSchema().model_dump()
