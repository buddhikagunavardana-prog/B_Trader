from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd


@dataclass(frozen=True)
class ResearchPeriodSplit:
    total_start: pd.Timestamp
    optimization_start: pd.Timestamp
    optimization_end: pd.Timestamp
    validation_start: pd.Timestamp
    validation_end: pd.Timestamp
    total_months: int
    optimization_months: int
    validation_months: int

    def __post_init__(self) -> None:
        for field_name in (
            "total_start",
            "optimization_start",
            "optimization_end",
            "validation_start",
            "validation_end",
        ):
            value = getattr(self, field_name)
            if value.tzinfo is None:
                raise ValueError(f"{field_name} must be timezone-aware")
            if str(value.tz) != "UTC":
                raise ValueError(f"{field_name} must use UTC")

        if self.total_months < 1:
            raise ValueError("total_months must be positive")

        if self.optimization_months < 1:
            raise ValueError("optimization_months must be positive")

        if self.validation_months < 1:
            raise ValueError("validation_months must be positive")

        if self.optimization_months + self.validation_months != self.total_months:
            raise ValueError(
                "optimization_months + validation_months must equal total_months"
            )

        if self.total_start != self.optimization_start:
            raise ValueError("optimization_start must equal total_start")

        if self.optimization_start >= self.optimization_end:
            raise ValueError("optimization period must be non-empty")

        if self.validation_start >= self.validation_end:
            raise ValueError("validation period must be non-empty")

        if self.optimization_end != self.validation_start:
            raise ValueError(
                "optimization_end must equal validation_start for half-open periods"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_start": self.total_start.isoformat(),
            "optimization_start": self.optimization_start.isoformat(),
            "optimization_end": self.optimization_end.isoformat(),
            "validation_start": self.validation_start.isoformat(),
            "validation_end": self.validation_end.isoformat(),
            "total_months": self.total_months,
            "optimization_months": self.optimization_months,
            "validation_months": self.validation_months,
        }


def _as_utc_timestamp(value: Any) -> pd.Timestamp:
    timestamp = pd.Timestamp(value)

    if timestamp.tzinfo is None:
        timestamp = timestamp.tz_localize("UTC")
    else:
        timestamp = timestamp.tz_convert("UTC")

    return timestamp


def build_research_period_split(
    end_timestamp: Any,
    total_months: int = 12,
    optimization_months: int = 6,
) -> ResearchPeriodSplit:
    if total_months < 2:
        raise ValueError("total_months must be at least 2")

    if optimization_months < 1:
        raise ValueError("optimization_months must be positive")

    if optimization_months >= total_months:
        raise ValueError("optimization_months must be less than total_months")

    validation_months = total_months - optimization_months
    validation_end = _as_utc_timestamp(end_timestamp)
    total_start = validation_end - pd.DateOffset(months=total_months)
    validation_start = total_start + pd.DateOffset(months=optimization_months)

    total_start = _as_utc_timestamp(total_start)
    validation_start = _as_utc_timestamp(validation_start)

    return ResearchPeriodSplit(
        total_start=total_start,
        optimization_start=total_start,
        optimization_end=validation_start,
        validation_start=validation_start,
        validation_end=validation_end,
        total_months=total_months,
        optimization_months=optimization_months,
        validation_months=validation_months,
    )
    