from __future__ import annotations

from typing import Iterable
import matplotlib.pyplot as plt
import pandas as pd


def _select_window(df: pd.DataFrame, year: int | None, window: Iterable | None) -> pd.DataFrame:
    out = df
    if year is not None:
        out = out[out.index.year == year]
    if window is not None:
        out = out.loc[window]
    return out


def plot_timeseries(df: pd.DataFrame, year: int | None = None, window: Iterable | None = None):
    view = _select_window(df, year, window)

    fig, axes = plt.subplots(4, 1, figsize=(12, 10), sharex=True)

    axes[0].plot(view.index, view["P_pv_bus_w"], label="PV bus")
    axes[0].set_ylabel("PV W")
    axes[0].legend()

    axes[1].plot(view.index, view["P_gpu_served_w"], label="GPU served")
    axes[1].plot(view.index, view["P_gpu_req_w"], label="GPU requested", alpha=0.7)
    axes[1].set_ylabel("GPU W")
    axes[1].legend()

    axes[2].plot(view.index, view["P_batt_bus_w"], label="Battery bus")
    axes[2].set_ylabel("Battery W")
    axes[2].legend()

    axes[3].plot(view.index, view["soc"], label="SOC")
    axes[3].set_ylabel("SOC")
    axes[3].set_xlabel("Time")
    axes[3].legend()

    fig.tight_layout()
    return fig


def plot_winter_window(df: pd.DataFrame, year: int):
    start = pd.Timestamp(f"{year}-01-01", tz=df.index.tz)
    end = start + pd.Timedelta(days=10)
    return plot_timeseries(df, window=slice(start, end))
