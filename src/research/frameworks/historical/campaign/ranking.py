from __future__ import annotations

from collections.abc import Mapping, Sequence
from math import isfinite
from typing import Any

from src.research.frameworks.historical.campaign.research_models import (
    FrameworkOptimizationResult,
    FrameworkRankingRow,
    FrameworkValidationResult,
)


DEFAULT_SCORE_WEIGHTS = {
    "optimization": 0.30,
    "validation": 0.45,
    "robustness": 0.25,
}

DEFAULT_PAPER_TRADING_THRESHOLDS = {
    "minimum_final_score": 60.0,
    "minimum_validation_score": 60.0,
    "minimum_robustness_score": 60.0,
    "minimum_profit_factor": 1.20,
    "maximum_drawdown_pct": 20.0,
    "minimum_expectancy": 0.0,
    "minimum_total_trades": 30,
}


def _bounded_score(value: Any) -> float | None:
    if value is None:
        return None

    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None

    if not isfinite(numeric):
        return None

    return round(max(0.0, min(numeric, 100.0)), 2)


def _finite_float(value: Any) -> float | None:
    if value is None:
        return None

    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None

    if not isfinite(numeric):
        return None

    return numeric


def _normalize_weights(
    weights: Mapping[str, float] | None,
) -> dict[str, float]:
    source = dict(weights or DEFAULT_SCORE_WEIGHTS)

    required = {
        "optimization",
        "validation",
        "robustness",
    }

    missing = required.difference(source)
    if missing:
        raise ValueError(
            "ranking weights are missing required keys: "
            f"{sorted(missing)}"
        )

    normalized: dict[str, float] = {}

    for name in sorted(required):
        value = float(source[name])

        if not isfinite(value) or value < 0:
            raise ValueError(
                f"ranking weight {name!r} must be finite and non-negative"
            )

        normalized[name] = value

    if sum(normalized.values()) <= 0:
        raise ValueError(
            "at least one ranking weight must be greater than zero"
        )

    return normalized


def _framework_key(
    framework_name: str,
    framework_version: str,
) -> tuple[str, str]:
    return (
        str(framework_name).strip(),
        str(framework_version).strip(),
    )


def _index_optimization_results(
    results: Sequence[FrameworkOptimizationResult],
) -> dict[tuple[str, str], FrameworkOptimizationResult]:
    indexed: dict[
        tuple[str, str],
        FrameworkOptimizationResult,
    ] = {}

    for result in results:
        if not isinstance(result, FrameworkOptimizationResult):
            raise TypeError(
                "optimization_results must contain only "
                "FrameworkOptimizationResult instances"
            )

        key = _framework_key(
            result.framework_name,
            result.framework_version,
        )

        if key in indexed:
            raise ValueError(
                "duplicate optimization result for framework "
                f"{key[0]!r} version {key[1]!r}"
            )

        indexed[key] = result

    return indexed


def _index_validation_results(
    results: Sequence[FrameworkValidationResult],
) -> dict[tuple[str, str], FrameworkValidationResult]:
    indexed: dict[
        tuple[str, str],
        FrameworkValidationResult,
    ] = {}

    for result in results:
        if not isinstance(result, FrameworkValidationResult):
            raise TypeError(
                "validation_results must contain only "
                "FrameworkValidationResult instances"
            )

        key = _framework_key(
            result.framework_name,
            result.framework_version,
        )

        if key in indexed:
            raise ValueError(
                "duplicate validation result for framework "
                f"{key[0]!r} version {key[1]!r}"
            )

        indexed[key] = result

    return indexed


def _diagnostic_value(
    diagnostics: Mapping[str, Any] | None,
    names: Sequence[str],
) -> Any:
    if not isinstance(diagnostics, Mapping):
        return None

    for name in names:
        if name in diagnostics:
            return diagnostics[name]

    return None


def _resolve_category(
    optimization_result: FrameworkOptimizationResult,
    validation_result: FrameworkValidationResult | None,
    framework_categories: Mapping[str, str] | None,
) -> str:
    if framework_categories:
        explicit = framework_categories.get(
            optimization_result.framework_name
        )

        if explicit is not None and str(explicit).strip():
            return str(explicit).strip()

    validation_category = _diagnostic_value(
        (
            validation_result.diagnostics
            if validation_result is not None
            else None
        ),
        (
            "category",
            "framework_category",
            "strategy_category",
        ),
    )

    if validation_category is not None:
        normalized = str(validation_category).strip()
        if normalized:
            return normalized

    optimization_category = _diagnostic_value(
        optimization_result.diagnostics,
        (
            "category",
            "framework_category",
            "strategy_category",
        ),
    )

    if optimization_category is not None:
        normalized = str(optimization_category).strip()
        if normalized:
            return normalized

    # A non-empty deterministic fallback keeps the ranking contract valid
    # without inventing a framework classification.
    return "uncategorized"


def _resolve_robustness_score(
    optimization_result: FrameworkOptimizationResult,
    validation_result: FrameworkValidationResult | None,
    robustness_scores: Mapping[str, float] | None,
) -> float | None:
    framework_name = optimization_result.framework_name

    if robustness_scores and framework_name in robustness_scores:
        return _bounded_score(robustness_scores[framework_name])

    if validation_result is not None:
        diagnostic_score = _diagnostic_value(
            validation_result.diagnostics,
            (
                "robustness_score",
                "walk_forward_score",
                "average_walk_forward_score",
                "repeatability_score",
                "integrity_score",
            ),
        )

        normalized = _bounded_score(diagnostic_score)
        if normalized is not None:
            return normalized

        # Until a dedicated campaign robustness stage exists, the validated
        # score is the safest available deterministic proxy.
        normalized = _bounded_score(
            validation_result.validation_score
        )
        if normalized is not None:
            return normalized

    diagnostic_score = _diagnostic_value(
        optimization_result.diagnostics,
        (
            "robustness_score",
            "stability_score",
        ),
    )

    return _bounded_score(diagnostic_score)


def calculate_framework_final_score(
    optimization_score: float | None,
    validation_score: float | None,
    robustness_score: float | None,
    *,
    weights: Mapping[str, float] | None = None,
) -> float | None:
    normalized_weights = _normalize_weights(weights)

    component_values = {
        "optimization": _bounded_score(optimization_score),
        "validation": _bounded_score(validation_score),
        "robustness": _bounded_score(robustness_score),
    }

    if all(value is None for value in component_values.values()):
        return None

    # Missing components receive zero rather than being silently ignored.
    # This prevents incomplete framework results from gaining an advantage.
    weighted_score = sum(
        (component_values[name] or 0.0) * normalized_weights[name]
        for name in component_values
    )

    total_weight = sum(normalized_weights.values())

    return _bounded_score(weighted_score / total_weight)


def _merge_rejection_reasons(
    optimization_result: FrameworkOptimizationResult,
    validation_result: FrameworkValidationResult | None,
) -> list[str]:
    reasons: list[str] = []

    for reason in optimization_result.rejection_reasons:
        normalized = str(reason).strip()
        if normalized and normalized not in reasons:
            reasons.append(normalized)

    for error in optimization_result.errors:
        normalized = str(error).strip()
        if normalized and normalized not in reasons:
            reasons.append(normalized)

    if validation_result is not None:
        for reason in validation_result.rejection_reasons:
            normalized = str(reason).strip()
            if normalized and normalized not in reasons:
                reasons.append(normalized)

        for error in validation_result.errors:
            normalized = str(error).strip()
            if normalized and normalized not in reasons:
                reasons.append(normalized)

    return reasons


def _evaluate_paper_trading_eligibility(
    *,
    optimization_result: FrameworkOptimizationResult,
    validation_result: FrameworkValidationResult | None,
    robustness_score: float | None,
    final_score: float | None,
    thresholds: Mapping[str, float | int],
) -> tuple[bool, str, tuple[str, ...]]:
    reasons = _merge_rejection_reasons(
        optimization_result,
        validation_result,
    )

    if optimization_result.status != "completed":
        reasons.append("Optimization did not complete")

    if validation_result is None:
        reasons.append("Validation result is missing")
    elif validation_result.status != "completed":
        reasons.append("Validation did not complete")

    if (
        validation_result is not None
        and optimization_result.selected_configuration_fingerprint
        != validation_result.configuration_fingerprint
    ):
        reasons.append(
            "Optimization and validation configuration fingerprints differ"
        )

    validation_score = (
        _bounded_score(validation_result.validation_score)
        if validation_result is not None
        else None
    )

    if final_score is None:
        reasons.append("Final score is unavailable")
    elif final_score < float(thresholds["minimum_final_score"]):
        reasons.append(
            "Final score below "
            f"{float(thresholds['minimum_final_score']):.2f}"
        )

    if validation_score is None:
        reasons.append("Validation score is unavailable")
    elif validation_score < float(
        thresholds["minimum_validation_score"]
    ):
        reasons.append(
            "Validation score below "
            f"{float(thresholds['minimum_validation_score']):.2f}"
        )

    if robustness_score is None:
        reasons.append("Robustness score is unavailable")
    elif robustness_score < float(
        thresholds["minimum_robustness_score"]
    ):
        reasons.append(
            "Robustness score below "
            f"{float(thresholds['minimum_robustness_score']):.2f}"
        )

    if validation_result is not None:
        profit_factor = _finite_float(
            validation_result.profit_factor
        )
        drawdown = _finite_float(
            validation_result.max_drawdown_pct
        )
        expectancy = _finite_float(
            validation_result.expectancy
        )

        if profit_factor is None:
            reasons.append("Validation profit factor is unavailable")
        elif profit_factor < float(
            thresholds["minimum_profit_factor"]
        ):
            reasons.append(
                "Profit factor below "
                f"{float(thresholds['minimum_profit_factor']):.2f}"
            )

        if drawdown is None:
            reasons.append("Validation max drawdown is unavailable")
        elif abs(drawdown) > float(
            thresholds["maximum_drawdown_pct"]
        ):
            reasons.append(
                "Max drawdown above "
                f"{float(thresholds['maximum_drawdown_pct']):.2f}%"
            )

        if expectancy is None:
            reasons.append("Validation expectancy is unavailable")
        elif expectancy <= float(
            thresholds["minimum_expectancy"]
        ):
            reasons.append("Validation expectancy is not positive")

        if validation_result.total_trades < int(
            thresholds["minimum_total_trades"]
        ):
            reasons.append(
                "Validation trade count below "
                f"{int(thresholds['minimum_total_trades'])}"
            )

        if (
            validation_result.completed_fold_count
            < validation_result.fold_count
        ):
            reasons.append(
                "Not all validation folds completed"
            )

    # Preserve deterministic order while removing duplicates.
    unique_reasons = tuple(dict.fromkeys(reasons))

    eligible = not unique_reasons

    if eligible:
        status = "PAPER_TRADING_READY"
    elif (
        optimization_result.status == "completed"
        and validation_result is not None
        and validation_result.status == "completed"
        and final_score is not None
        and final_score >= 45.0
    ):
        status = "PROMISING_REVIEW"
    else:
        status = "REJECTED"

    return eligible, status, unique_reasons


def _ranking_sort_key(
    row: FrameworkRankingRow,
) -> tuple[Any, ...]:
    return (
        -(row.final_score if row.final_score is not None else -1.0),
        -(
            row.validation_score
            if row.validation_score is not None
            else -1.0
        ),
        -(
            row.robustness_score
            if row.robustness_score is not None
            else -1.0
        ),
        -(
            row.validation_profit_factor
            if row.validation_profit_factor is not None
            else -1.0
        ),
        row.framework_name,
        row.framework_version,
        row.selected_configuration_fingerprint,
    )


def rank_framework_results(
    *,
    optimization_results: Sequence[FrameworkOptimizationResult],
    validation_results: Sequence[FrameworkValidationResult],
    framework_categories: Mapping[str, str] | None = None,
    robustness_scores: Mapping[str, float] | None = None,
    score_weights: Mapping[str, float] | None = None,
    paper_trading_thresholds: Mapping[
        str,
        float | int,
    ] | None = None,
) -> tuple[FrameworkRankingRow, ...]:
    """
    Pair optimization and validation results, evaluate eligibility, and
    return a deterministic framework ranking.

    Frameworks with optimization results but missing validation results remain
    visible in the ranking as rejected rows.

    Validation results without matching optimization results are rejected as
    an input contract error because their selected configuration cannot be
    identified safely.
    """
    optimization_index = _index_optimization_results(
        optimization_results
    )
    validation_index = _index_validation_results(
        validation_results
    )

    orphan_validation_keys = sorted(
        set(validation_index).difference(optimization_index)
    )

    if orphan_validation_keys:
        rendered = [
            f"{name}@{version}"
            for name, version in orphan_validation_keys
        ]
        raise ValueError(
            "validation results have no matching optimization results: "
            f"{rendered}"
        )

    thresholds: dict[str, float | int] = dict(
        DEFAULT_PAPER_TRADING_THRESHOLDS
    )

    if paper_trading_thresholds:
        thresholds.update(paper_trading_thresholds)

    provisional_rows: list[FrameworkRankingRow] = []

    for key in sorted(optimization_index):
        optimization_result = optimization_index[key]
        validation_result = validation_index.get(key)

        robustness_score = _resolve_robustness_score(
            optimization_result,
            validation_result,
            robustness_scores,
        )

        validation_score = (
            _bounded_score(validation_result.validation_score)
            if validation_result is not None
            else None
        )

        optimization_score = _bounded_score(
            optimization_result.optimization_score
        )

        final_score = calculate_framework_final_score(
            optimization_score,
            validation_score,
            robustness_score,
            weights=score_weights,
        )

        eligible, status, rejection_reasons = (
            _evaluate_paper_trading_eligibility(
                optimization_result=optimization_result,
                validation_result=validation_result,
                robustness_score=robustness_score,
                final_score=final_score,
                thresholds=thresholds,
            )
        )

        provisional_rows.append(
            FrameworkRankingRow(
                rank=1,
                framework_name=optimization_result.framework_name,
                category=_resolve_category(
                    optimization_result,
                    validation_result,
                    framework_categories,
                ),
                framework_version=(
                    optimization_result.framework_version
                ),
                selected_configuration_fingerprint=(
                    optimization_result
                    .selected_configuration_fingerprint
                ),
                optimization_score=optimization_score,
                validation_score=validation_score,
                robustness_score=robustness_score,
                final_score=final_score,
                validation_roi_pct=(
                    validation_result.roi_pct
                    if validation_result is not None
                    else None
                ),
                validation_win_rate_pct=(
                    validation_result.win_rate_pct
                    if validation_result is not None
                    else None
                ),
                validation_profit_factor=(
                    validation_result.profit_factor
                    if validation_result is not None
                    else None
                ),
                validation_max_drawdown_pct=(
                    validation_result.max_drawdown_pct
                    if validation_result is not None
                    else None
                ),
                validation_expectancy=(
                    validation_result.expectancy
                    if validation_result is not None
                    else None
                ),
                validation_total_trades=(
                    validation_result.total_trades
                    if validation_result is not None
                    else 0
                ),
                validation_wins=(
                    validation_result.wins
                    if validation_result is not None
                    else 0
                ),
                validation_losses=(
                    validation_result.losses
                    if validation_result is not None
                    else 0
                ),
                status=status,
                eligible_for_paper_trading=eligible,
                rejection_reasons=rejection_reasons,
            )
        )

    ordered_rows = sorted(
        provisional_rows,
        key=_ranking_sort_key,
    )

    ranked_rows = tuple(
        FrameworkRankingRow(
            rank=index,
            framework_name=row.framework_name,
            category=row.category,
            framework_version=row.framework_version,
            selected_configuration_fingerprint=(
                row.selected_configuration_fingerprint
            ),
            optimization_score=row.optimization_score,
            validation_score=row.validation_score,
            robustness_score=row.robustness_score,
            final_score=row.final_score,
            validation_roi_pct=row.validation_roi_pct,
            validation_win_rate_pct=(
                row.validation_win_rate_pct
            ),
            validation_profit_factor=(
                row.validation_profit_factor
            ),
            validation_max_drawdown_pct=(
                row.validation_max_drawdown_pct
            ),
            validation_expectancy=row.validation_expectancy,
            validation_total_trades=row.validation_total_trades,
            validation_wins=row.validation_wins,
            validation_losses=row.validation_losses,
            status=row.status,
            eligible_for_paper_trading=(
                row.eligible_for_paper_trading
            ),
            rejection_reasons=row.rejection_reasons,
        )
        for index, row in enumerate(ordered_rows, start=1)
    )

    return ranked_rows