from __future__ import annotations

import pandas as pd

from src.trading_frameworks.exceptions import FrameworkDataError


def validate_completed_bar_frame(frame: pd.DataFrame, role: str) -> None:
    if not isinstance(frame, pd.DataFrame):
        raise FrameworkDataError(f"frame for role '{role}' must be a DataFrame")
    if not isinstance(frame.index, pd.DatetimeIndex):
        raise FrameworkDataError(f"frame for role '{role}' must use a DatetimeIndex")
    if not frame.index.is_monotonic_increasing:
        raise FrameworkDataError(f"frame for role '{role}' must be timestamp-sorted")
    if frame.index.has_duplicates:
        raise FrameworkDataError(f"frame for role '{role}' contains duplicate timestamps")


def causal_slice(frame: pd.DataFrame, timestamp: pd.Timestamp | None) -> pd.DataFrame:
    if timestamp is None:
        return frame
    try:
        return frame.loc[frame.index <= pd.Timestamp(timestamp)]
    except TypeError as error:
        raise FrameworkDataError("decision timestamp timezone does not match frame index") from error


def latest_common_timestamp(
    frames: dict[str, pd.DataFrame] | object,
    preferred_role: str,
) -> pd.Timestamp | None:
    mapping = dict(frames)  # type: ignore[arg-type]
    preferred = mapping[preferred_role]
    if not preferred.empty:
        return pd.Timestamp(preferred.index[-1])
    available = [pd.Timestamp(frame.index[-1]) for frame in mapping.values() if not frame.empty]
    return min(available) if available else None
