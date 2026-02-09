from __future__ import annotations

from pathlib import Path
import pandas as pd


def _has_pyarrow() -> bool:
    try:
        import pyarrow  # noqa: F401
    except Exception:
        return False
    return True


def save_dataframe(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix == ".parquet":
        df.to_parquet(path)
    else:
        df.to_csv(path)


def load_dataframe(path: Path) -> pd.DataFrame:
    if path.suffix == ".parquet":
        return pd.read_parquet(path)
    return pd.read_csv(path, index_col=0, parse_dates=True)


def preferred_extension() -> str:
    return ".parquet" if _has_pyarrow() else ".csv"
