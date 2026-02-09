from __future__ import annotations

import pandas as pd


def ensure_tz_aware(index: pd.DatetimeIndex) -> None:
    if index.tz is None:
        raise ValueError("DatetimeIndex must be timezone-aware")


def ensure_fixed_interval(index: pd.DatetimeIndex, freq: str) -> None:
    expected = index.asfreq(freq)
    if expected.isna().any():
        raise ValueError(f"DatetimeIndex has missing timestamps for freq {freq}")
