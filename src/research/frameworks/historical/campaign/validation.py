from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import MISSING, fields, is_dataclass
from math import isfinite
from pathlib import Path
from typing import Any

import pandas as pd

from src.research.frameworks.historical.campaign.research_models import (
    FrameworkOptimizationResult,
    FrameworkValidationResult,
)
from src.research.frameworks.validator import (
    validate_decision_series,
    validate_repeatability,
)


_REQUIRED_VALIDATION_METRICS = {
    "roi_pct",
    "win_rate_pct",
    "profit_factor",
    "max_drawdown_pct",
    "expectancy",
    "total_trades",
    "wins",
    "losses",
}


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


def _normalize_metrics(
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    missing = sorted(
        _REQUIRED_VALIDATION_METRICS.difference(payload)
    )

    if missing:
        raise ValueError(
            "Validation metrics are missing required fields: "
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

    win_rate_pct = _as_finite_float(
        payload["win_rate_pct"],
        "win_rate_pct",
    )

    if not 0.0 <= win_rate_pct <= 100.0:
        raise ValueError(
            "win_rate_pct must be between 0 and 100."
        )

    return {
        "roi_pct": _as_finite_float(
            payload["roi_pct"],
            "roi_pct",
        ),
        "win_rate_pct": win_rate_pct,
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


def calculate_validation_score(
    metrics: Mapping[str, Any],
    *,
    minimum_trades: int = 30,
) -> float:
    """
    Calculate a deterministic out-of-sample validation score.

    This score is intended only for research comparison.
    It does not authorize paper trading or live trading.
    """
    if isinstance(minimum_trades, bool) or minimum_trades < 1:
        raise ValueError(
            "minimum_trades must be a positive integer."
        )

    normalized = _normalize_metrics(metrics)

    roi_score = max(
        0.0,
        min(
            100.0,
            50.0 + normalized["roi_pct"] * 2.0,
        ),
    )

    win_rate_score = max(
        0.0,
        min(100.0, normalized["win_rate_pct"]),
    )

    profit_factor_score = max(
        0.0,
        min(
            100.0,
            normalized["profit_factor"] * 50.0,
        ),
    )

    drawdown_score = max(
        0.0,
        100.0
        - abs(normalized["max_drawdown_pct"]) * 2.0,
    )

    expectancy_score = max(
        0.0,
        min(
            100.0,
            50.0 + normalized["expectancy"] * 10.0,
        ),
    )

    trade_score = max(
        0.0,
        min(
            100.0,
            normalized["total_trades"]
            / minimum_trades
            * 100.0,
        ),
    )

    score = (
        roi_score * 0.25
        + win_rate_score * 0.15
        + profit_factor_score * 0.25
        + drawdown_score * 0.15
        + expectancy_score * 0.10
        + trade_score * 0.10
    )

    return round(
        max(0.0, min(100.0, score)),
        8,
    )


def summarize_walk_forward_rows(
    rows: Iterable[Mapping[str, Any]],
    *,
    pass_score: float = 60.0,
) -> dict[str, Any]:
    """
    Normalize walk-forward rows produced by the existing engine.

    Supports both:
    - Walk Forward Score / Status
    - walk_forward_score / status
    """
    normalized_pass_score = _as_finite_float(
        pass_score,
        "pass_score",
    )

    normalized_rows: list[dict[str, Any]] = []

    for index, row in enumerate(rows):
        if not isinstance(row, Mapping):
            raise TypeError(
                f"Walk-forward row {index} must be a mapping."
            )

        score_value = row.get(
            "walk_forward_score",
            row.get("Walk Forward Score"),
        )

        if score_value is None:
            raise ValueError(
                f"Walk-forward row {index} has no score."
            )

        score = _as_finite_float(
            score_value,
            f"walk_forward_score[{index}]",
        )

        raw_status = str(
            row.get(
                "status",
                row.get("Status", ""),
            )
        ).strip().upper()

        passed = (
            raw_status == "PASS"
            if raw_status
            else score >= normalized_pass_score
        )

        normalized_rows.append({
            "index": index,
            "score": score,
            "status": "PASS" if passed else "FAIL",
            "passed": passed,
        })

    window_count = len(normalized_rows)

    passed_window_count = sum(
        1
        for row in normalized_rows
        if row["passed"]
    )

    failed_window_count = (
        window_count - passed_window_count
    )

    average_score = (
        sum(row["score"] for row in normalized_rows)
        / window_count
        if window_count
        else 0.0
    )

    minimum_score = (
        min(row["score"] for row in normalized_rows)
        if normalized_rows
        else 0.0
    )

    maximum_score = (
        max(row["score"] for row in normalized_rows)
        if normalized_rows
        else 0.0
    )

    pass_rate_pct = (
        passed_window_count
        / window_count
        * 100.0
        if window_count
        else 0.0
    )

    passed = (
        window_count > 0
        and passed_window_count > failed_window_count
        and average_score >= normalized_pass_score
    )

    return {
        "window_count": window_count,
        "passed_window_count": passed_window_count,
        "failed_window_count": failed_window_count,
        "average_score": round(average_score, 8),
        "minimum_score": round(minimum_score, 8),
        "maximum_score": round(maximum_score, 8),
        "pass_rate_pct": round(pass_rate_pct, 8),
        "passed": passed,
        "rows": normalized_rows,
    }


def _extract_research_validation_issues(
    validation_result: Any,
) -> list[dict[str, str]]:
    issues = getattr(validation_result, "issues", ())

    normalized: list[dict[str, str]] = []

    for issue in issues:
        normalized.append({
            "code": str(
                getattr(issue, "code", "")
            ),
            "severity": str(
                getattr(issue, "severity", "")
            ).upper(),
            "message": str(
                getattr(issue, "message", "")
            ),
        })

    return normalized


def validate_decision_outputs(
    decision_frame: pd.DataFrame | None,
    repeated_decision_frame: pd.DataFrame | None = None,
) -> dict[str, Any]:
    if decision_frame is None:
        return {
            "checked": False,
            "valid": True,
            "repeatable": None,
            "issues": [],
            "row_count": 0,
        }

    if not isinstance(decision_frame, pd.DataFrame):
        raise TypeError(
            "decision_frame must be a pandas DataFrame."
        )

    decision_validation = validate_decision_series(
        decision_frame
    )

    issues = _extract_research_validation_issues(
        decision_validation
    )

    repeatable: bool | None = None

    if repeated_decision_frame is not None:
        if not isinstance(
            repeated_decision_frame,
            pd.DataFrame,
        ):
            raise TypeError(
                "repeated_decision_frame must be a pandas "
                "DataFrame."
            )

        repeatability_validation = validate_repeatability(
            decision_frame,
            repeated_decision_frame,
        )

        repeatability_issues = (
            _extract_research_validation_issues(
                repeatability_validation
            )
        )

        issues.extend(repeatability_issues)

        repeatable = not any(
            issue["severity"] == "ERROR"
            for issue in repeatability_issues
        )

    valid = not any(
        issue["severity"] == "ERROR"
        for issue in issues
    )

    return {
        "checked": True,
        "valid": valid,
        "repeatable": repeatable,
        "issues": issues,
        "row_count": len(decision_frame),
    }


def validate_historical_integrity(
    *,
    run_directory: str | Path | None,
    historical_plan: Any | None,
    strict: bool = True,
) -> dict[str, Any]:
    if run_directory is None and historical_plan is None:
        return {
            "checked": False,
            "valid": True,
            "details": {},
        }

    if run_directory is None or historical_plan is None:
        raise ValueError(
            "run_directory and historical_plan must be "
            "supplied together."
        )

    from src.research.frameworks.historical.integrity import (
        validate_historical_run,
    )

    result = validate_historical_run(
        run_directory,
        historical_plan,
        strict=bool(strict),
    )

    if not isinstance(result, Mapping):
        raise TypeError(
            "validate_historical_run() must return a mapping."
        )

    return {
        "checked": True,
        "valid": bool(result.get("valid", False)),
        "details": dict(result),
    }


def _construct_validation_result(
    payload: Mapping[str, Any],
) -> FrameworkValidationResult:
    """
    Build FrameworkValidationResult using the exact fields currently
    defined in research_models.py.

    Extra payload values are ignored. Any missing required field
    produces a clear error.
    """
    if not is_dataclass(FrameworkValidationResult):
        return FrameworkValidationResult(**dict(payload))

    model_fields = {
        model_field.name: model_field
        for model_field in fields(FrameworkValidationResult)
        if model_field.init
    }

    aliases = {
        "configuration_fingerprint": (
            "configuration_fingerprint",
            "selected_configuration_fingerprint",
        ),
        "validation_score": (
            "validation_score",
            "score",
        ),
        "score": (
            "score",
            "validation_score",
        ),
        "validation_passed": (
            "validation_passed",
            "passed",
        ),
        "passed": (
            "passed",
            "validation_passed",
        ),
        "walk_forward_score": (
            "walk_forward_score",
            "average_walk_forward_score",
        ),
        "average_walk_forward_score": (
            "average_walk_forward_score",
            "walk_forward_score",
        ),
        "walk_forward_passed": (
            "walk_forward_passed",
            "passed",
        ),
        "window_count": (
            "window_count",
            "walk_forward_window_count",
        ),
        "walk_forward_window_count": (
            "walk_forward_window_count",
            "window_count",
        ),
        "passed_window_count": (
            "passed_window_count",
            "walk_forward_passed_window_count",
        ),
        "failed_window_count": (
            "failed_window_count",
            "walk_forward_failed_window_count",
        ),
    }

    constructor_values: dict[str, Any] = {}

    for field_name, model_field in model_fields.items():
        candidate_names = aliases.get(
            field_name,
            (field_name,),
        )

        for candidate_name in candidate_names:
            if candidate_name in payload:
                constructor_values[field_name] = (
                    payload[candidate_name]
                )
                break

        if field_name in constructor_values:
            continue

        has_default = (
            model_field.default is not MISSING
            or model_field.default_factory is not MISSING
        )

        if not has_default:
            raise TypeError(
                "FrameworkValidationResult has an "
                "unsupported required field: "
                f"{field_name!r}. Add it to validation "
                "payload mapping."
            )

    return FrameworkValidationResult(
        **constructor_values
    )


def validate_framework_result(
    *,
    optimization_result: FrameworkOptimizationResult,
    validation_metrics: Mapping[str, Any],
    walk_forward_rows: Iterable[Mapping[str, Any]] = (),
    minimum_trades: int = 30,
    minimum_profit_factor: float = 1.0,
    maximum_drawdown_pct: float = 30.0,
    minimum_validation_score: float = 60.0,
    minimum_walk_forward_score: float = 60.0,
    decision_frame: pd.DataFrame | None = None,
    repeated_decision_frame: pd.DataFrame | None = None,
    historical_run_directory: str | Path | None = None,
    historical_plan: Any | None = None,
    strict_historical_validation: bool = True,
) -> FrameworkValidationResult:
    if not isinstance(
        optimization_result,
        FrameworkOptimizationResult,
    ):
        raise TypeError(
            "optimization_result must be "
            "FrameworkOptimizationResult."
        )

    metrics = _normalize_metrics(
        validation_metrics
    )

    normalized_minimum_trades = _as_non_negative_int(
        minimum_trades,
        "minimum_trades",
    )

    normalized_minimum_profit_factor = (
        _as_finite_float(
            minimum_profit_factor,
            "minimum_profit_factor",
        )
    )

    normalized_maximum_drawdown = abs(
        _as_finite_float(
            maximum_drawdown_pct,
            "maximum_drawdown_pct",
        )
    )

    normalized_minimum_validation_score = (
        _as_finite_float(
            minimum_validation_score,
            "minimum_validation_score",
        )
    )

    validation_score = calculate_validation_score(
        metrics,
        minimum_trades=max(
            1,
            normalized_minimum_trades,
        ),
    )

    walk_forward_summary = summarize_walk_forward_rows(
        walk_forward_rows,
        pass_score=minimum_walk_forward_score,
    )

    decision_validation = validate_decision_outputs(
        decision_frame,
        repeated_decision_frame,
    )

    historical_validation = validate_historical_integrity(
        run_directory=historical_run_directory,
        historical_plan=historical_plan,
        strict=strict_historical_validation,
    )

    rejection_reasons: list[str] = []
    errors: list[str] = []

    if optimization_result.status != "completed":
        rejection_reasons.append(
            "Optimization result was not completed."
        )

    if (
        metrics["total_trades"]
        < normalized_minimum_trades
    ):
        rejection_reasons.append(
            "Validation trade count is below the "
            "required minimum: "
            f"{metrics['total_trades']} < "
            f"{normalized_minimum_trades}."
        )

    if (
        metrics["profit_factor"]
        < normalized_minimum_profit_factor
    ):
        rejection_reasons.append(
            "Validation profit factor is below the "
            "required minimum: "
            f"{metrics['profit_factor']} < "
            f"{normalized_minimum_profit_factor}."
        )

    if (
        abs(metrics["max_drawdown_pct"])
        > normalized_maximum_drawdown
    ):
        rejection_reasons.append(
            "Validation drawdown exceeds the allowed "
            "maximum: "
            f"{abs(metrics['max_drawdown_pct'])} > "
            f"{normalized_maximum_drawdown}."
        )

    if (
        validation_score
        < normalized_minimum_validation_score
    ):
        rejection_reasons.append(
            "Validation score is below the required "
            "minimum: "
            f"{validation_score} < "
            f"{normalized_minimum_validation_score}."
        )

    if (
        walk_forward_summary["window_count"] > 0
        and not walk_forward_summary["passed"]
    ):
        rejection_reasons.append(
            "Walk-forward validation did not pass."
        )

    if not decision_validation["valid"]:
        rejection_reasons.append(
            "Decision-series validation failed."
        )

    if not historical_validation["valid"]:
        rejection_reasons.append(
            "Historical run integrity validation failed."
        )

    for issue in decision_validation["issues"]:
        if issue["severity"] == "ERROR":
            errors.append(
                f"{issue['code']}: "
                f"{issue['message']}"
            )

    passed = (
        not rejection_reasons
        and not errors
    )

    status = (
        "completed"
        if passed
        else "rejected"
    )

    diagnostics = {
        "optimization_status": (
            optimization_result.status
        ),
        "optimization_score": (
            optimization_result.optimization_score
        ),
        "optimization_configuration_fingerprint": (
            optimization_result
            .selected_configuration_fingerprint
        ),
        "minimum_trades": (
            normalized_minimum_trades
        ),
        "minimum_profit_factor": (
            normalized_minimum_profit_factor
        ),
        "maximum_drawdown_pct": (
            normalized_maximum_drawdown
        ),
        "minimum_validation_score": (
            normalized_minimum_validation_score
        ),
        "walk_forward": walk_forward_summary,
        "decision_validation": decision_validation,
        "historical_validation": historical_validation,
        "validation_metrics_diagnostics": dict(
            metrics["diagnostics"]
        ),
    }

    payload = {
        "framework_name": (
            optimization_result.framework_name
        ),
        "framework_version": (
            optimization_result.framework_version
        ),

        # Required by FrameworkValidationResult.
        "configuration_fingerprint": (
            optimization_result
            .selected_configuration_fingerprint
        ),
        "selected_configuration_fingerprint": (
            optimization_result
            .selected_configuration_fingerprint
        ),

        "status": status,
        "validation_passed": passed,
        "passed": passed,
        "validation_score": validation_score,
        "score": validation_score,

        "roi_pct": metrics["roi_pct"],
        "win_rate_pct": metrics["win_rate_pct"],
        "profit_factor": metrics["profit_factor"],
        "max_drawdown_pct": (
            metrics["max_drawdown_pct"]
        ),
        "expectancy": metrics["expectancy"],
        "total_trades": metrics["total_trades"],
        "wins": metrics["wins"],
        "losses": metrics["losses"],

        "walk_forward_score": (
            walk_forward_summary["average_score"]
        ),
        "average_walk_forward_score": (
            walk_forward_summary["average_score"]
        ),
        "walk_forward_passed": (
            walk_forward_summary["passed"]
        ),

        "window_count": (
            walk_forward_summary["window_count"]
        ),
        "walk_forward_window_count": (
            walk_forward_summary["window_count"]
        ),
        "passed_window_count": (
            walk_forward_summary[
                "passed_window_count"
            ]
        ),
        "walk_forward_passed_window_count": (
            walk_forward_summary[
                "passed_window_count"
            ]
        ),
        "failed_window_count": (
            walk_forward_summary[
                "failed_window_count"
            ]
        ),
        "walk_forward_failed_window_count": (
            walk_forward_summary[
                "failed_window_count"
            ]
        ),

        "rejection_reasons": rejection_reasons,
        "errors": errors,
        "diagnostics": diagnostics,
    }

    return _construct_validation_result(payload)