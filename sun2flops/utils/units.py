from __future__ import annotations


def dt_hours(dt_min: int) -> float:
    return dt_min / 60.0


def dt_seconds(dt_min: int) -> int:
    return dt_min * 60
