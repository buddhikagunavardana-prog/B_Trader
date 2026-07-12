from collections.abc import Iterable

import pandas as pd


def require_columns(df: pd.DataFrame, columns: Iterable[str]) -> None:
    if not isinstance(df, pd.DataFrame):
        raise TypeError("indicator input must be a pandas DataFrame")
    missing = [column for column in columns if column not in df.columns]
    if missing:
        raise ValueError(f"indicator input missing columns: {missing}")


def positive_int(value: int, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return value


def positive_float(value: float, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
        raise ValueError(f"{name} must be positive")
    return float(value)


def require_source(df: pd.DataFrame, source: str) -> None:
    if not isinstance(source, str) or not source:
        raise ValueError("source must be a non-empty column name")
    require_columns(df, [source])
