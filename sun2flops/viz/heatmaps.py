from __future__ import annotations

import matplotlib.pyplot as plt
import pandas as pd


def plot_heatmap(tidy_df: pd.DataFrame, x: str = "pv_kw", y: str = "batt_kwh", z: str = "utilization"):
    pivot = tidy_df.pivot(index=y, columns=x, values=z)
    fig, ax = plt.subplots(figsize=(8, 6))
    im = ax.imshow(pivot.values, origin="lower", aspect="auto")
    ax.set_xticks(range(len(pivot.columns)))
    ax.set_xticklabels(pivot.columns)
    ax.set_yticks(range(len(pivot.index)))
    ax.set_yticklabels(pivot.index)
    ax.set_xlabel(x)
    ax.set_ylabel(y)
    ax.set_title(z)
    fig.colorbar(im, ax=ax)
    fig.tight_layout()
    return fig
