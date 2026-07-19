from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from src.research.frameworks.historical.campaign.ranking import (
    rank_framework_results,
)
from src.research.frameworks.historical.campaign.research_models import (
    FrameworkOptimizationResult,
    FrameworkRankingRow,
    FrameworkResearchSummary,
    FrameworkValidationResult,
)
from src.research.frameworks.historical.campaign.selection import (
    build_framework_research_summary,
)


OptimizationExecutor = Callable[
    [],
    Sequence[FrameworkOptimizationResult],
]

ValidationExecutor = Callable[
    [Sequence[FrameworkOptimizationResult]],
    Sequence[FrameworkValidationResult],
]


def _normalize_messages(
    messages: Sequence[str],
) -> tuple[str, ...]:
    normalized: list[str] = []

    for message in messages:
        text = str(message).strip()

        if text and text not in normalized:
            normalized.append(text)

    return tuple(normalized)


@dataclass(frozen=True)
class FrameworkResearchRunResult:
    """
    Immutable result of one Phase 27 framework research run.
    """

    campaign_id: str
    configuration_fingerprint: str
    status: str

    optimization_results: tuple[
        FrameworkOptimizationResult,
        ...,
    ] = ()

    validation_results: tuple[
        FrameworkValidationResult,
        ...,
    ] = ()

    ranking_rows: tuple[
        FrameworkRankingRow,
        ...,
    ] = ()

    summary: FrameworkResearchSummary | None = None

    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()

    diagnostics: Mapping[str, Any] = field(
        default_factory=dict
    )

    def __post_init__(self) -> None:
        campaign_id = str(self.campaign_id).strip()

        configuration_fingerprint = str(
            self.configuration_fingerprint
        ).strip()

        status = str(self.status).strip().lower()

        if not campaign_id:
            raise ValueError(
                "campaign_id must be a non-empty string"
            )

        if not configuration_fingerprint:
            raise ValueError(
                "configuration_fingerprint must be a "
                "non-empty string"
            )

        allowed_statuses = {
            "completed",
            "completed_with_warnings",
            "failed",
        }

        if status not in allowed_statuses:
            raise ValueError(
                "status must be one of "
                f"{sorted(allowed_statuses)}"
            )

        if status == "failed" and not self.errors:
            raise ValueError(
                "failed result must contain at least one error"
            )

        if status != "failed" and self.summary is None:
            raise ValueError(
                "successful result must contain a summary"
            )

        object.__setattr__(
            self,
            "campaign_id",
            campaign_id,
        )
        object.__setattr__(
            self,
            "configuration_fingerprint",
            configuration_fingerprint,
        )
        object.__setattr__(
            self,
            "status",
            status,
        )
        object.__setattr__(
            self,
            "optimization_results",
            tuple(self.optimization_results),
        )
        object.__setattr__(
            self,
            "validation_results",
            tuple(self.validation_results),
        )
        object.__setattr__(
            self,
            "ranking_rows",
            tuple(self.ranking_rows),
        )
        object.__setattr__(
            self,
            "warnings",
            _normalize_messages(self.warnings),
        )
        object.__setattr__(
            self,
            "errors",
            _normalize_messages(self.errors),
        )
        object.__setattr__(
            self,
            "diagnostics",
            dict(self.diagnostics),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "campaign_id": self.campaign_id,
            "configuration_fingerprint": (
                self.configuration_fingerprint
            ),
            "status": self.status,
            "optimization_results": [
                result.to_dict()
                for result in self.optimization_results
            ],
            "validation_results": [
                result.to_dict()
                for result in self.validation_results
            ],
            "ranking_rows": [
                row.to_dict()
                for row in self.ranking_rows
            ],
            "summary": (
                self.summary.to_dict()
                if self.summary is not None
                else None
            ),
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "diagnostics": dict(self.diagnostics),
        }


def _validate_optimization_results(
    results: Sequence[FrameworkOptimizationResult],
) -> tuple[FrameworkOptimizationResult, ...]:
    normalized = tuple(results)

    seen: set[tuple[str, str]] = set()

    for result in normalized:
        if not isinstance(
            result,
            FrameworkOptimizationResult,
        ):
            raise TypeError(
                "optimization executor must return only "
                "FrameworkOptimizationResult instances"
            )

        key = (
            result.framework_name,
            result.framework_version,
        )

        if key in seen:
            raise ValueError(
                "duplicate optimization result: "
                f"{result.framework_name}@"
                f"{result.framework_version}"
            )

        seen.add(key)

    return normalized


def _validate_validation_results(
    results: Sequence[FrameworkValidationResult],
) -> tuple[FrameworkValidationResult, ...]:
    normalized = tuple(results)

    seen: set[tuple[str, str]] = set()

    for result in normalized:
        if not isinstance(
            result,
            FrameworkValidationResult,
        ):
            raise TypeError(
                "validation executor must return only "
                "FrameworkValidationResult instances"
            )

        key = (
            result.framework_name,
            result.framework_version,
        )

        if key in seen:
            raise ValueError(
                "duplicate validation result: "
                f"{result.framework_name}@"
                f"{result.framework_version}"
            )

        seen.add(key)

    return normalized


def _collect_warnings(
    optimization_results: Sequence[
        FrameworkOptimizationResult
    ],
    validation_results: Sequence[
        FrameworkValidationResult
    ],
) -> tuple[str, ...]:
    warnings: list[str] = []

    for result in optimization_results:
        if result.status != "completed":
            warnings.append(
                "Optimization did not complete for "
                f"{result.framework_name}@"
                f"{result.framework_version}."
            )

        for error in result.errors:
            warnings.append(
                "Optimization issue for "
                f"{result.framework_name}: {error}"
            )

    for result in validation_results:
        if result.status != "completed":
            warnings.append(
                "Validation did not complete for "
                f"{result.framework_name}@"
                f"{result.framework_version}."
            )

        for error in result.errors:
            warnings.append(
                "Validation issue for "
                f"{result.framework_name}: {error}"
            )

    return _normalize_messages(warnings)


def _failed_stage(
    optimization_results: Sequence[
        FrameworkOptimizationResult
    ],
    validation_results: Sequence[
        FrameworkValidationResult
    ],
    ranking_rows: Sequence[FrameworkRankingRow],
) -> str:
    if ranking_rows:
        return "selection"

    if validation_results:
        return "ranking"

    if optimization_results:
        return "validation"

    return "optimization"


class FrameworkResearchOrchestrator:
    """
    Run the Phase 27 framework research pipeline.

    Pipeline:

        optimization
        -> validation
        -> ranking
        -> shortlist selection
        -> summary

    This class is intentionally separate from the existing Phase 24.9
    Historical Campaign Orchestrator.
    """

    def __init__(
        self,
        *,
        optimization_executor: OptimizationExecutor,
        validation_executor: ValidationExecutor,
    ) -> None:
        if not callable(optimization_executor):
            raise TypeError(
                "optimization_executor must be callable"
            )

        if not callable(validation_executor):
            raise TypeError(
                "validation_executor must be callable"
            )

        self._optimization_executor = (
            optimization_executor
        )
        self._validation_executor = validation_executor

    def run(
        self,
        *,
        campaign_id: str,
        configuration_fingerprint: str,
        framework_categories: Mapping[
            str,
            str,
        ] | None = None,
        robustness_scores: Mapping[
            str,
            float,
        ] | None = None,
        score_weights: Mapping[
            str,
            float,
        ] | None = None,
        paper_trading_thresholds: Mapping[
            str,
            float | int,
        ] | None = None,
        maximum_selected: int = 5,
        maximum_per_category: int | None = None,
        fill_remaining: bool = True,
        warnings: Sequence[str] = (),
        diagnostics: Mapping[str, Any] | None = None,
        raise_on_error: bool = False,
    ) -> FrameworkResearchRunResult:
        normalized_campaign_id = str(
            campaign_id
        ).strip()

        normalized_configuration_fingerprint = str(
            configuration_fingerprint
        ).strip()

        if not normalized_campaign_id:
            raise ValueError(
                "campaign_id must be a non-empty string"
            )

        if not normalized_configuration_fingerprint:
            raise ValueError(
                "configuration_fingerprint must be a "
                "non-empty string"
            )

        optimization_results: tuple[
            FrameworkOptimizationResult,
            ...,
        ] = ()

        validation_results: tuple[
            FrameworkValidationResult,
            ...,
        ] = ()

        ranking_rows: tuple[
            FrameworkRankingRow,
            ...,
        ] = ()

        try:
            optimization_results = (
                _validate_optimization_results(
                    self._optimization_executor()
                )
            )

            validation_results = (
                _validate_validation_results(
                    self._validation_executor(
                        optimization_results
                    )
                )
            )

            ranking_rows = tuple(
                rank_framework_results(
                    optimization_results=(
                        optimization_results
                    ),
                    validation_results=(
                        validation_results
                    ),
                    framework_categories=(
                        framework_categories
                    ),
                    robustness_scores=robustness_scores,
                    score_weights=score_weights,
                    paper_trading_thresholds=(
                        paper_trading_thresholds
                    ),
                )
            )

            result_warnings = _collect_warnings(
                optimization_results,
                validation_results,
            )

            combined_warnings = _normalize_messages(
                tuple(warnings) + result_warnings
            )

            campaign_diagnostics: dict[str, Any] = {
                "optimization_result_count": len(
                    optimization_results
                ),
                "validation_result_count": len(
                    validation_results
                ),
                "ranking_row_count": len(
                    ranking_rows
                ),
            }

            if diagnostics:
                for key in sorted(diagnostics):
                    campaign_diagnostics[str(key)] = (
                        diagnostics[key]
                    )

            summary = build_framework_research_summary(
                campaign_id=normalized_campaign_id,
                configuration_fingerprint=(
                    normalized_configuration_fingerprint
                ),
                ranking_rows=ranking_rows,
                optimization_results=(
                    optimization_results
                ),
                validation_results=validation_results,
                maximum_selected=maximum_selected,
                maximum_per_category=(
                    maximum_per_category
                ),
                fill_remaining=fill_remaining,
                warnings=combined_warnings,
                diagnostics=campaign_diagnostics,
            )

            status = (
                "completed_with_warnings"
                if combined_warnings or summary.warnings
                else "completed"
            )

            return FrameworkResearchRunResult(
                campaign_id=normalized_campaign_id,
                configuration_fingerprint=(
                    normalized_configuration_fingerprint
                ),
                status=status,
                optimization_results=optimization_results,
                validation_results=validation_results,
                ranking_rows=ranking_rows,
                summary=summary,
                warnings=combined_warnings,
                errors=(),
                diagnostics=campaign_diagnostics,
            )

        except Exception as exc:
            if raise_on_error:
                raise

            return FrameworkResearchRunResult(
                campaign_id=normalized_campaign_id,
                configuration_fingerprint=(
                    normalized_configuration_fingerprint
                ),
                status="failed",
                optimization_results=optimization_results,
                validation_results=validation_results,
                ranking_rows=ranking_rows,
                summary=None,
                warnings=_normalize_messages(warnings),
                errors=(
                    f"{type(exc).__name__}: {exc}",
                ),
                diagnostics={
                    "failed_stage": _failed_stage(
                        optimization_results,
                        validation_results,
                        ranking_rows,
                    ),
                },
            )