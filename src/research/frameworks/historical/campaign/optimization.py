from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from math import isfinite
from typing import Any

from src.research.frameworks.historical.campaign.research_models import (
    FrameworkOptimizationResult,
)
from src.research.optimizer.optimizer_candidate import OptimizationCandidate


CandidateEvaluator = Callable[
    [OptimizationCandidate],
    Mapping[str, Any],
]


_REQUIRED_METRIC_KEYS = {
    "roi_pct",
    "win_rate_pct",
    "profit_factor",
    "max_drawdown_pct",
    "expectancy",
    "total_trades",
    "wins",
    "losses",
}


def _require_non_empty_string(value: Any, field_name: str) -> str:
    normalized = str(value).strip()
    if not normalized:
        raise ValueError(f"{field_name} must be a non-empty string.")

    return normalized


def _as_finite_float(value: Any, field_name: str) -> float:
    try:
        normalized = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"{field_name} must be numeric; received {value!r}."
        ) from exc

    if not isfinite(normalized):
        raise ValueError(
            f"{field_name} must be finite; received {normalized!r}."
        )

    return normalized


def _as_non_negative_int(value: Any, field_name: str) -> int:
    if isinstance(value, bool):
        raise ValueError(
            f"{field_name} must be an integer, not a boolean."
        )

    try:
        normalized = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"{field_name} must be an integer; received {value!r}."
        ) from exc

    if normalized < 0:
        raise ValueError(
            f"{field_name} must be greater than or equal to zero."
        )

    return normalized


def _normalize_metric_payload(
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    missing = sorted(_REQUIRED_METRIC_KEYS.difference(payload))
    if missing:
        raise ValueError(
            "Candidate evaluation result is missing required fields: "
            + ", ".join(missing)
        )

    total_trades = _as_non_negative_int(
        payload["total_trades"],
        "total_trades",
    )
    wins = _as_non_negative_int(payload["wins"], "wins")
    losses = _as_non_negative_int(payload["losses"], "losses")

    if wins + losses > total_trades:
        raise ValueError(
            "wins + losses cannot be greater than total_trades."
        )

    return {
        "roi_pct": _as_finite_float(payload["roi_pct"], "roi_pct"),
        "win_rate_pct": _as_finite_float(
            payload["win_rate_pct"],
            "win_rate_pct",
        ),
        "profit_factor": _as_finite_float(
            payload["profit_factor"],
            "profit_factor",
        ),
        "max_drawdown_pct": _as_finite_float(
            payload["max_drawdown_pct"],
            "max_drawdown_pct",
        ),
        "expectancy": _as_finite_float(
            payload["expectancy"],
            "expectancy",
        ),
        "total_trades": total_trades,
        "wins": wins,
        "losses": losses,
        "diagnostics": dict(payload.get("diagnostics", {})),
    }


def calculate_optimization_score(
    metrics: Mapping[str, Any],
) -> float:
    """
    Produce a deterministic research score in the approximate 0-100 range.

    The score rewards:
    - positive ROI
    - higher win rate
    - profit factor above 1.0
    - positive expectancy
    - sufficient trade count

    The score penalizes:
    - maximum drawdown

    This is a research ranking score only. It is not a profitability
    guarantee and does not authorize live trading.
    """
    normalized = _normalize_metric_payload(metrics)

    roi_component = max(
        -25.0,
        min(25.0, normalized["roi_pct"]),
    )
    win_rate_component = max(
        0.0,
        min(20.0, normalized["win_rate_pct"] * 0.20),
    )
    profit_factor_component = max(
        0.0,
        min(25.0, (normalized["profit_factor"] - 1.0) * 25.0),
    )
    expectancy_component = max(
        -10.0,
        min(10.0, normalized["expectancy"] * 10.0),
    )
    trade_count_component = min(
        10.0,
        normalized["total_trades"] / 20.0,
    )
    drawdown_penalty = min(
        30.0,
        abs(normalized["max_drawdown_pct"]) * 0.75,
    )

    score = (
        40.0
        + roi_component
        + win_rate_component
        + profit_factor_component
        + expectancy_component
        + trade_count_component
        - drawdown_penalty
    )

    return round(max(0.0, min(100.0, score)), 8)


def _candidate_sort_key(
    evaluated_candidate: Mapping[str, Any],
) -> tuple[Any, ...]:
    """
    Deterministic best-candidate ordering.

    Higher values are preferred except drawdown, where a smaller absolute
    value is preferred. Candidate hash is the final deterministic tie-breaker.
    """
    metrics = evaluated_candidate["metrics"]
    candidate = evaluated_candidate["candidate"]

    return (
        -evaluated_candidate["optimization_score"],
        -metrics["profit_factor"],
        -metrics["roi_pct"],
        abs(metrics["max_drawdown_pct"]),
        -metrics["expectancy"],
        -metrics["total_trades"],
        candidate.candidate_hash,
    )


def optimize_framework_candidates(
    *,
    framework_name: str,
    framework_version: str,
    candidates: Iterable[OptimizationCandidate],
    evaluator: CandidateEvaluator,
) -> FrameworkOptimizationResult:
    """
    Evaluate optimizer candidates and return the deterministic best result.

    The evaluator must return:

    {
        "roi_pct": float,
        "win_rate_pct": float,
        "profit_factor": float,
        "max_drawdown_pct": float,
        "expectancy": float,
        "total_trades": int,
        "wins": int,
        "losses": int,
        "diagnostics": dict,  # optional
    }

    Invalid candidates and evaluator failures are retained as rejection
    reasons instead of terminating the whole framework research run.
    """
    normalized_framework_name = _require_non_empty_string(
        framework_name,
        "framework_name",
    )
    normalized_framework_version = _require_non_empty_string(
        framework_version,
        "framework_version",
    )

    candidate_list = list(candidates)
    evaluated: list[dict[str, Any]] = []
    rejection_reasons: list[str] = []
    errors: list[str] = []

    for candidate in candidate_list:
        if not isinstance(candidate, OptimizationCandidate):
            rejection_reasons.append(
                f"Rejected unsupported candidate type: "
                f"{type(candidate).__name__}"
            )
            continue

        if candidate.validation_status != "VALID":
            reasons = ", ".join(candidate.validation_reasons)
            rejection_reasons.append(
                f"{candidate.candidate_id}: invalid optimizer candidate"
                + (f" ({reasons})" if reasons else "")
            )
            continue

        try:
            raw_metrics = evaluator(candidate)
            if not isinstance(raw_metrics, Mapping):
                raise TypeError(
                    "Evaluator must return a mapping of research metrics."
                )

            metrics = _normalize_metric_payload(raw_metrics)
            score = calculate_optimization_score(metrics)

            evaluated.append({
                "candidate": candidate,
                "metrics": metrics,
                "optimization_score": score,
            })
        except Exception as exc:
            errors.append(
                f"{candidate.candidate_id}: "
                f"{type(exc).__name__}: {exc}"
            )

    if not evaluated:
        return FrameworkOptimizationResult(
            framework_name=normalized_framework_name,
            framework_version=normalized_framework_version,
            status="failed",
            selected_configuration={},
            selected_configuration_fingerprint="",
            optimization_score=0.0,
            roi_pct=0.0,
            win_rate_pct=0.0,
            profit_factor=0.0,
            max_drawdown_pct=0.0,
            expectancy=0.0,
            total_trades=0,
            wins=0,
            losses=0,
            candidate_count=len(candidate_list),
            rejection_reasons=rejection_reasons,
            errors=errors or [
                "No valid framework optimization result was produced."
            ],
            diagnostics={
                "evaluated_candidate_count": 0,
                "valid_candidate_count": 0,
                "rejected_candidate_count": len(rejection_reasons),
                "error_count": len(errors),
            },
        )

    evaluated.sort(key=_candidate_sort_key)
    best = evaluated[0]

    best_candidate: OptimizationCandidate = best["candidate"]
    best_metrics = best["metrics"]

    diagnostics = {
        "selected_candidate_id": best_candidate.candidate_id,
        "selected_strategy_id": best_candidate.strategy_id,
        "selected_template_type": best_candidate.template_type,
        "evaluated_candidate_count": len(evaluated),
        "valid_candidate_count": len(evaluated),
        "rejected_candidate_count": len(rejection_reasons),
        "error_count": len(errors),
        "selected_candidate_metadata": dict(
            best_candidate.optimization_metadata
        ),
        "selected_evaluation_diagnostics": dict(
            best_metrics["diagnostics"]
        ),
    }

    return FrameworkOptimizationResult(
        framework_name=normalized_framework_name,
        framework_version=normalized_framework_version,
        status="completed",
        selected_configuration=dict(best_candidate.parameters),
        selected_configuration_fingerprint=best_candidate.candidate_hash,
        optimization_score=best["optimization_score"],
        roi_pct=best_metrics["roi_pct"],
        win_rate_pct=best_metrics["win_rate_pct"],
        profit_factor=best_metrics["profit_factor"],
        max_drawdown_pct=best_metrics["max_drawdown_pct"],
        expectancy=best_metrics["expectancy"],
        total_trades=best_metrics["total_trades"],
        wins=best_metrics["wins"],
        losses=best_metrics["losses"],
        candidate_count=len(candidate_list),
        rejection_reasons=rejection_reasons,
        errors=errors,
        diagnostics=diagnostics,
    )


def build_and_optimize_framework(
    *,
    framework_name: str,
    framework_version: str,
    evaluator: CandidateEvaluator,
    max_candidates: int,
    strict_constraints: bool = True,
) -> FrameworkOptimizationResult:
    """
    Generate candidates through the existing optimizer architecture and
    evaluate them for a Phase 27 framework research run.

    Importing the candidate builder locally avoids introducing import cycles
    into the historical campaign package.
    """
    if isinstance(max_candidates, bool) or max_candidates <= 0:
        raise ValueError("max_candidates must be a positive integer.")

    from src.research.optimizer.optimizer_runner import (
        build_optimization_candidates,
    )

    candidates = build_optimization_candidates(
        max_candidates=int(max_candidates),
        strict_constraints=bool(strict_constraints),
    )

    return optimize_framework_candidates(
        framework_name=framework_name,
        framework_version=framework_version,
        candidates=candidates,
        evaluator=evaluator,
    )