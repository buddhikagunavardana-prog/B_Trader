import csv
import json
from pathlib import Path


ALLOWED_INPUT_ROLES = {
    "benchmark_summary",
    "benchmark_shortlist",
    "benchmark_stages",
    "phase_21_1",
    "phase_21_2",
    "phase_21_3",
}
FORBIDDEN_PATH_PARTS = {
    "candidate_trades", "ohlcv", "source", ".env", "secret", "api_key",
}
SENSITIVE_TEXT_MARKERS = {
    "api_key", "apikey", "authorization", "bearer ", "private key",
    "secret", "access_token", "refresh_token",
}
READINESS_THRESHOLDS = {
    "profit_factor": 1.20,
    "walk_forward_pass_rate": 0.60,
    "robustness_score": 60.0,
    "overfitting_risk": 50.0,
    "monte_carlo_positive_run_rate": 0.70,
    "monte_carlo_ruin_probability": 0.05,
    "max_drawdown_pct": 20.0,
    "trades": 30,
    "expectancy": 0.0,
    "profitable_regime_count": 2,
}
METRIC_MAP = {
    "profit_factor": "Profit Factor",
    "walk_forward_pass_rate": "Walk Forward Pass Rate",
    "robustness_score": "Robustness Score",
    "overfitting_risk": "Overfitting Risk",
    "monte_carlo_positive_run_rate": "Monte Carlo Positive Run Rate",
    "monte_carlo_ruin_probability": "Monte Carlo Ruin Probability",
    "max_drawdown_pct": "Max Drawdown %",
    "trades": "Trades",
    "expectancy": "Expectancy",
    "profitable_regime_count": "Profitable Regime Count",
}
FAILURE_LABELS = {
    "profit_factor": "Profit factor is below the deterministic gate",
    "walk_forward_pass_rate": "Walk-forward stability is below the deterministic gate",
    "robustness_score": "Robustness is below the deterministic gate",
    "overfitting_risk": "Overfitting risk exceeds the deterministic gate",
    "monte_carlo_positive_run_rate": "Monte Carlo positive-run rate is below the deterministic gate",
    "monte_carlo_ruin_probability": "Monte Carlo ruin probability exceeds the deterministic gate",
    "max_drawdown_pct": "Maximum drawdown exceeds the deterministic gate",
    "trades": "Trade count is below the deterministic gate",
    "expectancy": "Expectancy is not positive",
    "profitable_regime_count": "Profitable-regime coverage is below the deterministic gate",
}


def _safe_report_path(path_value: str) -> Path:
    path = Path(path_value)
    lowered = str(path).lower()
    if path.suffix.lower() not in {".json", ".csv"}:
        raise ValueError(f"AI context input must be a compact JSON or CSV report: {path}")
    if any(part in lowered for part in FORBIDDEN_PATH_PARTS):
        raise ValueError(f"AI context rejected sensitive or raw input path: {path.name}")
    if not path.is_file():
        raise FileNotFoundError(f"AI context report not found: {path}")
    return path


def _compact_safe_text(value) -> str | None:
    if value is None:
        return None
    text = str(value)[:500]
    if any(marker in text.lower() for marker in SENSITIVE_TEXT_MARKERS):
        return "[REDACTED SENSITIVE REPORT TEXT]"
    return text


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as file:
        payload = json.load(file)
    return payload if isinstance(payload, dict) else {}


def _load_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def _failed_gates(candidate: dict) -> list[dict]:
    reasons = str(candidate.get("Rejection Reasons", "")).split(" | ")
    gates = []
    checks = [
        ("Profit factor", "profit_factor"),
        ("Walk-forward", "walk_forward_pass_rate"),
        ("Robustness score", "robustness_score"),
        ("Overfitting risk", "overfitting_risk"),
        ("Monte Carlo positive", "monte_carlo_positive_run_rate"),
        ("Monte Carlo ruin", "monte_carlo_ruin_probability"),
        ("Max drawdown", "max_drawdown_pct"),
        ("Trade count", "trades"),
        ("Expectancy", "expectancy"),
        ("Fewer than", "profitable_regime_count"),
    ]
    for reason in filter(None, reasons):
        for prefix, metric in checks:
            if reason.startswith(prefix):
                gates.append({
                    "metric": metric,
                    "reason": FAILURE_LABELS[metric],
                })
                break
    return gates


def _candidate_context(candidate: dict) -> dict:
    candidate_id = str(candidate.get("Candidate ID") or candidate.get("Strategy ID"))
    metrics = {
        name: candidate.get(source)
        for name, source in METRIC_MAP.items()
    }
    return {
        "candidate_id": candidate_id,
        "pair": candidate.get("Pair"),
        "timeframe": candidate.get("Timeframe"),
        "status": candidate.get("Status"),
        "position_sizing_mode": (
            "risk_normalized" if "_RISK" in candidate_id else "full_allocation"
        ),
        "exit_mode": (
            "atr_full_position" if "_ATREXIT" in candidate_id
            else "fixed_percent_full_position"
        ),
        "metrics": metrics,
        "failed_gates": _failed_gates(candidate),
    }


def _phase_summary(payload: dict) -> dict:
    if not payload:
        return {}
    return {
        "phase": payload.get("phase"),
        "title": _compact_safe_text(payload.get("title")),
        "conclusion": _compact_safe_text(
            payload.get("conclusion")
            or payload.get("trade_lifecycle_diagnosis", {}).get(
                "post_experiment_conclusion"
            )
        ),
        "paper_trading_status": (
            payload.get("paper_trading_readiness", {}).get("status")
            if isinstance(payload.get("paper_trading_readiness"), dict)
            else payload.get("monte_carlo_and_final", {}).get("paper_trading_status")
        ),
    }


def build_research_context(
    input_report_paths: dict[str, str],
    max_candidates: int,
) -> dict:
    unknown = set(input_report_paths).difference(ALLOWED_INPUT_ROLES)
    if unknown:
        raise ValueError(f"Unsupported AI context report roles: {sorted(unknown)}")
    paths = {
        role: _safe_report_path(path)
        for role, path in input_report_paths.items()
    }
    summary = _load_json(paths["benchmark_summary"])
    shortlist = _load_json(paths["benchmark_shortlist"])
    stages = _load_csv(paths["benchmark_stages"])
    candidates = list(shortlist.get("paper_trading_ready", []))
    candidates.extend(shortlist.get("promising_review", []))
    candidates = candidates[:max(0, int(max_candidates))]
    phase_payloads = [
        _load_json(paths[role])
        for role in ["phase_21_1", "phase_21_2", "phase_21_3"]
        if role in paths
    ]
    phase_21_3 = next(
        (payload for payload in phase_payloads if str(payload.get("phase")) == "21.3"),
        {},
    )
    comparison = phase_21_3.get("benchmark_comparison", {}).get("phase_21_3", {})
    stage_status = [
        {
            "stage": row.get("Stage"),
            "status": row.get("Status"),
            "task_usage": int(float(row.get("Task Usage") or 0)),
        }
        for row in stages
    ]
    data_issues = [
        text
        for item in summary.get("warnings", [])
        if (text := _compact_safe_text(item)) is not None
    ]
    if summary.get("reproducibility_status") != "REPRODUCIBLE":
        data_issues.append(
            f"Reproducibility status is {summary.get('reproducibility_status', 'UNKNOWN')}"
        )
    return {
        "context_version": "1.0",
        "run_id": str(summary.get("run_id", "UNKNOWN")),
        "benchmark_status": summary.get("status"),
        "paper_trading_readiness": summary.get(
            "paper_trading_readiness", "NOT_READY"
        ),
        "stage_status": stage_status,
        "candidate_counts": {
            "generated": summary.get("generated_candidate_count"),
            "funnel_3m_survivors": comparison.get("funnel_3m_survivors"),
            "funnel_6m_survivors": comparison.get("funnel_6m_survivors"),
            "funnel_1y_survivors": comparison.get("funnel_1y_survivors"),
            "promising_review": summary.get("promising_review_count"),
            "paper_trading_ready": summary.get("paper_trading_ready_count"),
        },
        "readiness_thresholds": dict(READINESS_THRESHOLDS),
        "candidates": [_candidate_context(item) for item in candidates],
        "cost_model": {
            "historical_fees": "zero",
            "historical_slippage": "zero",
        },
        "data_quality_issues": data_issues,
        "experiment_summaries": [_phase_summary(item) for item in phase_payloads],
    }
