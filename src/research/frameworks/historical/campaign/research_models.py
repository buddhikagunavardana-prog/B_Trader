from __future__ import annotations

from dataclasses import dataclass, field
from math import isfinite
from typing import Any, Mapping


def _validate_non_empty(value: str, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")


def _finite_or_none(value: float | None, field_name: str) -> None:
    if value is not None and not isfinite(float(value)):
        raise ValueError(f"{field_name} must be finite or None")


def _sorted_mapping(values: Mapping[str, Any]) -> dict[str, Any]:
    return {str(key): values[key] for key in sorted(values)}


@dataclass(frozen=True)
class FrameworkOptimizationResult:
    framework_name: str
    framework_version: str
    status: str
    selected_configuration: Mapping[str, Any]
    selected_configuration_fingerprint: str
    optimization_score: float | None
    roi_pct: float | None
    win_rate_pct: float | None
    profit_factor: float | None
    max_drawdown_pct: float | None
    expectancy: float | None
    total_trades: int
    wins: int
    losses: int
    candidate_count: int
    rejection_reasons: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()
    diagnostics: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _validate_non_empty(self.framework_name, "framework_name")
        _validate_non_empty(self.framework_version, "framework_version")
        _validate_non_empty(self.status, "status")

        if self.status == "completed":
            _validate_non_empty(
                self.selected_configuration_fingerprint,
                "selected_configuration_fingerprint",
            )

        for field_name in (
            "optimization_score",
            "roi_pct",
            "win_rate_pct",
            "profit_factor",
            "max_drawdown_pct",
            "expectancy",
        ):
            _finite_or_none(getattr(self, field_name), field_name)

        for field_name in (
            "total_trades",
            "wins",
            "losses",
            "candidate_count",
        ):
            if getattr(self, field_name) < 0:
                raise ValueError(f"{field_name} cannot be negative")

        if self.wins + self.losses > self.total_trades:
            raise ValueError("wins + losses cannot exceed total_trades")

    def to_dict(self) -> dict[str, Any]:
        return {
            "framework_name": self.framework_name,
            "framework_version": self.framework_version,
            "status": self.status,
            "selected_configuration": _sorted_mapping(
                self.selected_configuration
            ),
            "selected_configuration_fingerprint": (
                self.selected_configuration_fingerprint
            ),
            "optimization_score": self.optimization_score,
            "roi_pct": self.roi_pct,
            "win_rate_pct": self.win_rate_pct,
            "profit_factor": self.profit_factor,
            "max_drawdown_pct": self.max_drawdown_pct,
            "expectancy": self.expectancy,
            "total_trades": self.total_trades,
            "wins": self.wins,
            "losses": self.losses,
            "candidate_count": self.candidate_count,
            "rejection_reasons": list(self.rejection_reasons),
            "errors": list(self.errors),
            "diagnostics": _sorted_mapping(self.diagnostics),
        }


@dataclass(frozen=True)
class FrameworkValidationResult:
    framework_name: str
    framework_version: str
    status: str
    configuration_fingerprint: str
    validation_score: float | None
    roi_pct: float | None
    win_rate_pct: float | None
    profit_factor: float | None
    max_drawdown_pct: float | None
    expectancy: float | None
    total_trades: int
    wins: int
    losses: int
    fold_count: int = 1
    completed_fold_count: int = 0
    rejection_reasons: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()
    diagnostics: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _validate_non_empty(self.framework_name, "framework_name")
        _validate_non_empty(self.framework_version, "framework_version")
        _validate_non_empty(self.status, "status")

        if self.status == "completed":
            _validate_non_empty(
                self.configuration_fingerprint,
                "configuration_fingerprint",
            )

        for field_name in (
            "validation_score",
            "roi_pct",
            "win_rate_pct",
            "profit_factor",
            "max_drawdown_pct",
            "expectancy",
        ):
            _finite_or_none(getattr(self, field_name), field_name)

        for field_name in (
            "total_trades",
            "wins",
            "losses",
            "fold_count",
            "completed_fold_count",
        ):
            if getattr(self, field_name) < 0:
                raise ValueError(f"{field_name} cannot be negative")

        if self.wins + self.losses > self.total_trades:
            raise ValueError("wins + losses cannot exceed total_trades")

        if self.completed_fold_count > self.fold_count:
            raise ValueError(
                "completed_fold_count cannot exceed fold_count"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "framework_name": self.framework_name,
            "framework_version": self.framework_version,
            "status": self.status,
            "configuration_fingerprint": self.configuration_fingerprint,
            "validation_score": self.validation_score,
            "roi_pct": self.roi_pct,
            "win_rate_pct": self.win_rate_pct,
            "profit_factor": self.profit_factor,
            "max_drawdown_pct": self.max_drawdown_pct,
            "expectancy": self.expectancy,
            "total_trades": self.total_trades,
            "wins": self.wins,
            "losses": self.losses,
            "fold_count": self.fold_count,
            "completed_fold_count": self.completed_fold_count,
            "rejection_reasons": list(self.rejection_reasons),
            "errors": list(self.errors),
            "diagnostics": _sorted_mapping(self.diagnostics),
        }


@dataclass(frozen=True)
class FrameworkRankingRow:
    rank: int
    framework_name: str
    category: str
    framework_version: str
    selected_configuration_fingerprint: str
    optimization_score: float | None
    validation_score: float | None
    robustness_score: float | None
    final_score: float | None
    validation_roi_pct: float | None
    validation_win_rate_pct: float | None
    validation_profit_factor: float | None
    validation_max_drawdown_pct: float | None
    validation_expectancy: float | None
    validation_total_trades: int
    validation_wins: int
    validation_losses: int
    status: str
    eligible_for_paper_trading: bool
    rejection_reasons: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.rank < 1:
            raise ValueError("rank must be at least 1")

        _validate_non_empty(self.framework_name, "framework_name")
        _validate_non_empty(self.category, "category")
        _validate_non_empty(self.framework_version, "framework_version")
        _validate_non_empty(self.status, "status")

        for field_name in (
            "optimization_score",
            "validation_score",
            "robustness_score",
            "final_score",
            "validation_roi_pct",
            "validation_win_rate_pct",
            "validation_profit_factor",
            "validation_max_drawdown_pct",
            "validation_expectancy",
        ):
            _finite_or_none(getattr(self, field_name), field_name)

        for field_name in (
            "validation_total_trades",
            "validation_wins",
            "validation_losses",
        ):
            if getattr(self, field_name) < 0:
                raise ValueError(f"{field_name} cannot be negative")

        if (
            self.validation_wins + self.validation_losses
            > self.validation_total_trades
        ):
            raise ValueError(
                "validation wins + losses cannot exceed total trades"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "rank": self.rank,
            "framework_name": self.framework_name,
            "category": self.category,
            "framework_version": self.framework_version,
            "selected_configuration_fingerprint": (
                self.selected_configuration_fingerprint
            ),
            "optimization_score": self.optimization_score,
            "validation_score": self.validation_score,
            "robustness_score": self.robustness_score,
            "final_score": self.final_score,
            "validation_roi_pct": self.validation_roi_pct,
            "validation_win_rate_pct": self.validation_win_rate_pct,
            "validation_profit_factor": self.validation_profit_factor,
            "validation_max_drawdown_pct": (
                self.validation_max_drawdown_pct
            ),
            "validation_expectancy": self.validation_expectancy,
            "validation_total_trades": self.validation_total_trades,
            "validation_wins": self.validation_wins,
            "validation_losses": self.validation_losses,
            "status": self.status,
            "eligible_for_paper_trading": (
                self.eligible_for_paper_trading
            ),
            "rejection_reasons": list(self.rejection_reasons),
        }


@dataclass(frozen=True)
class FrameworkResearchSummary:
    campaign_id: str
    configuration_fingerprint: str
    ranking_fingerprint: str
    framework_count: int
    optimization_completed_count: int
    validation_completed_count: int
    failed_framework_count: int
    eligible_framework_count: int
    selected_framework_count: int
    top_frameworks: tuple[FrameworkRankingRow, ...]
    warnings: tuple[str, ...] = ()
    diagnostics: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _validate_non_empty(self.campaign_id, "campaign_id")
        _validate_non_empty(
            self.configuration_fingerprint,
            "configuration_fingerprint",
        )
        _validate_non_empty(
            self.ranking_fingerprint,
            "ranking_fingerprint",
        )

        for field_name in (
            "framework_count",
            "optimization_completed_count",
            "validation_completed_count",
            "failed_framework_count",
            "eligible_framework_count",
            "selected_framework_count",
        ):
            if getattr(self, field_name) < 0:
                raise ValueError(f"{field_name} cannot be negative")

        if self.selected_framework_count > self.eligible_framework_count:
            raise ValueError(
                "selected_framework_count cannot exceed "
                "eligible_framework_count"
            )

        if len(self.top_frameworks) != self.selected_framework_count:
            raise ValueError(
                "top_frameworks length must equal selected_framework_count"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "campaign_id": self.campaign_id,
            "configuration_fingerprint": (
                self.configuration_fingerprint
            ),
            "ranking_fingerprint": self.ranking_fingerprint,
            "framework_count": self.framework_count,
            "optimization_completed_count": (
                self.optimization_completed_count
            ),
            "validation_completed_count": (
                self.validation_completed_count
            ),
            "failed_framework_count": self.failed_framework_count,
            "eligible_framework_count": self.eligible_framework_count,
            "selected_framework_count": self.selected_framework_count,
            "top_frameworks": [
                row.to_dict() for row in self.top_frameworks
            ],
            "warnings": list(self.warnings),
            "diagnostics": _sorted_mapping(self.diagnostics),
        }