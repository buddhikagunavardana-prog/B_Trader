import json

from src.research.benchmark.benchmark_shortlist import build_final_ranking, write_shortlist_reports
from src.research.orchestrator.adapters.adapter_result import (
    FAILURE_ARTIFACT,
    artifact_path_from_state,
    benchmark_settings,
    blocked_payload,
    make_artifact,
    stage_payload,
)


def _load_json(path: str):
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def _selector_candidates(shortlist: list[dict], monte_carlo: dict) -> list[dict]:
    summaries = monte_carlo.get("candidates")
    if not isinstance(summaries, list):
        raise ValueError("ARTIFACT_CONTRACT_FAILURE: Monte Carlo candidates must be a list")
    by_id = {}
    for summary in summaries:
        candidate_id = str(summary.get("Candidate ID", ""))
        if not candidate_id or candidate_id in by_id:
            raise ValueError("ARTIFACT_CONTRACT_FAILURE: invalid or duplicate Monte Carlo candidate ID")
        by_id[candidate_id] = summary
    candidates = []
    for item in shortlist:
        strategy_id = str(item.get("strategy_id", ""))
        candidate_id = str(item.get("candidate_id") or strategy_id)
        if candidate_id not in by_id:
            raise ValueError(
                f"ARTIFACT_CONTRACT_FAILURE: orphan selector candidate {candidate_id}"
            )
        mc = by_id.pop(candidate_id)
        metrics = dict(item.get("minimum_expected_metrics") or {})
        candidates.append({
            "Candidate ID": candidate_id,
            "Strategy ID": strategy_id,
            "Pair": mc.get("Pair"),
            "Timeframe": mc.get("Timeframe"),
            "Profit Factor": metrics.get("profit_factor"),
            "Max Drawdown %": metrics.get("max_drawdown_pct"),
            "Trades": metrics.get("trades"),
            "Expectancy": metrics.get("expectancy", 0.0),
            "Walk Forward Score": item.get("walk_forward_score", 0.0),
            "Walk Forward Pass Rate": item.get("walk_forward_pass_rate", 0.0),
            "Robustness Score": item.get("robustness_score"),
            "Overfitting Risk": item.get("overfitting_risk_score"),
            "Pair Consistency": item.get("pair_consistency_score", 0.0),
            "Regime Consistency": item.get("regime_consistency_score", 0.0),
            "Profitable Regime Count": len(item.get("recommended_regimes") or []),
            "Monte Carlo Stability": mc.get("Stability Score"),
            "Monte Carlo Positive Run Rate": mc.get("Positive Run Rate"),
            "Monte Carlo Ruin Probability": mc.get("Ruin Probability"),
        })
    if by_id:
        raise ValueError(
            f"ARTIFACT_CONTRACT_FAILURE: orphan Monte Carlo results {sorted(by_id)}"
        )
    return candidates


def run_best_selector_stage(context, stage, state):
    ranking_path = context.run_directory() / "final_benchmark_ranking.csv"
    shortlist_path = context.run_directory() / "final_benchmark_shortlist.json"
    rejections_path = context.run_directory() / "final_benchmark_rejections.csv"
    robustness_path = artifact_path_from_state(state, "robustness_shortlist")
    monte_carlo_path = artifact_path_from_state(state, "monte_carlo_summary")
    if not robustness_path or not monte_carlo_path:
        return blocked_payload(
            stage.name,
            "ARTIFACT_CONTRACT_FAILURE: selector input artifacts are missing",
            FAILURE_ARTIFACT,
        )
    try:
        robustness = _load_json(robustness_path)
        monte_carlo = _load_json(monte_carlo_path)
        if not isinstance(robustness, list):
            raise ValueError("ARTIFACT_CONTRACT_FAILURE: robustness shortlist must be a list")
        candidates = _selector_candidates(robustness, monte_carlo)
        settings = benchmark_settings(context)
        ranking, shortlist, rejections = build_final_ranking(
            candidates,
            int(settings.get("final_shortlist_count", 10)),
            int(settings.get("paper_trading_shortlist_count", 5)),
        )
        write_shortlist_reports(
            ranking, shortlist, rejections,
            str(ranking_path), str(shortlist_path), str(rejections_path),
        )
        return stage_payload(
            stage.name,
            "Best selector completed from production candidate artifacts",
            task_usage=max(len(candidates), 1),
            artifacts=[
                make_artifact(ranking_path, "final_ranking", stage.name, "CSV", metadata={"contract_version": "2"}),
                make_artifact(shortlist_path, "paper_trading_shortlist", stage.name, "JSON", metadata={"contract_version": "2"}),
                make_artifact(rejections_path, "final_rejections", stage.name, "CSV", required=False),
                make_artifact(ranking_path, "final_candidate_metrics", stage.name, "CSV", metadata={"contract_version": "2"}),
            ],
            metrics={
                "candidate_count": len(candidates),
                "ranking_rows": len(ranking),
                "paper_ready_count": len(shortlist["paper_trading_ready"]),
                "rejected_count": len(rejections),
            },
            warnings=[] if candidates else ["Empty robustness shortlist produced an empty ranking"],
        )
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as error:
        return blocked_payload(stage.name, str(error), FAILURE_ARTIFACT)
