import json
from pathlib import Path

import pandas as pd

from src.research.pipeline.pipeline_reporter import save_csv_report, save_json_report


FINAL_SCORE_WEIGHTS = {
    "Robustness Score": 25,
    "Walk Forward Score": 20,
    "Monte Carlo Stability": 20,
    "Profit Factor Score": 10,
    "Drawdown Score": 10,
    "Expectancy Score": 5,
    "Pair Consistency": 5,
    "Regime Consistency": 5,
}
RANKING_COLUMNS = [
    "Candidate ID",
    "Strategy ID",
    "Pair",
    "Final Benchmark Score",
    "Status",
    "Robustness Score",
    "Walk Forward Score",
    "Monte Carlo Stability",
    "Profit Factor",
    "Max Drawdown %",
    "Expectancy",
    "Trades",
    "Rejection Reasons",
]


def _bounded(value: float) -> float:
    return round(max(0.0, min(float(value), 100.0)), 2)


def calculate_final_benchmark_score(row: dict) -> dict:
    profit_factor_score = _bounded(float(row.get("Profit Factor", 0.0)) / 2.0 * 100)
    drawdown_score = _bounded(100 - abs(float(row.get("Max Drawdown %", 100.0))) / 20.0 * 100)
    expectancy_score = _bounded(float(row.get("Expectancy", 0.0)) * 100)
    components = {
        "Robustness Score": _bounded(row.get("Robustness Score", 0.0)),
        "Walk Forward Score": _bounded(row.get("Walk Forward Score", 0.0)),
        "Monte Carlo Stability": _bounded(row.get("Monte Carlo Stability", 0.0)),
        "Profit Factor Score": profit_factor_score,
        "Drawdown Score": drawdown_score,
        "Expectancy Score": expectancy_score,
        "Pair Consistency": _bounded(row.get("Pair Consistency", 0.0)),
        "Regime Consistency": _bounded(row.get("Regime Consistency", 0.0)),
    }
    weighted = sum(
        components[name] * weight
        for name, weight in FINAL_SCORE_WEIGHTS.items()
    ) / sum(FINAL_SCORE_WEIGHTS.values())
    components["Final Benchmark Score"] = _bounded(weighted)
    return components


def evaluate_paper_trading_gate(row: dict) -> tuple[str, list[str]]:
    reasons = []
    if float(row.get("Profit Factor", 0.0)) < 1.20:
        reasons.append("Profit factor below 1.20")
    if float(row.get("Walk Forward Pass Rate", 0.0)) < 0.60:
        reasons.append("Walk-forward pass rate below 0.60")
    if float(row.get("Robustness Score", 0.0)) < 60:
        reasons.append("Robustness score below 60")
    if float(row.get("Overfitting Risk", 100.0)) > 50:
        reasons.append("Overfitting risk above 50")
    if float(row.get("Monte Carlo Positive Run Rate", 0.0)) < 0.70:
        reasons.append("Monte Carlo positive-run rate below 0.70")
    if float(row.get("Monte Carlo Ruin Probability", 1.0)) > 0.05:
        reasons.append("Monte Carlo ruin probability above 0.05")
    if abs(float(row.get("Max Drawdown %", 100.0))) > 20:
        reasons.append("Max drawdown above 20%")
    if int(row.get("Trades", 0)) < int(row.get("Minimum Trades", 30)):
        reasons.append("Trade count below minimum")
    if float(row.get("Expectancy", 0.0)) <= 0:
        reasons.append("Expectancy is not positive")
    if int(row.get("Profitable Regime Count", 0)) < 2:
        reasons.append("Fewer than 2 profitable regimes")

    if not reasons:
        return "PAPER_TRADING_READY", []

    if (
        float(row.get("Robustness Score", 0.0)) >= 45
        and float(row.get("Profit Factor", 0.0)) >= 1.05
    ):
        return "PROMISING_REVIEW", reasons

    return "REJECTED", reasons


def build_final_ranking(
    candidates: list[dict],
    final_shortlist_count: int = 10,
    paper_trading_shortlist_count: int = 5,
) -> tuple[pd.DataFrame, dict, pd.DataFrame]:
    rows = []
    for index, candidate in enumerate(candidates):
        candidate = dict(candidate)
        candidate.setdefault("Candidate ID", candidate.get("Strategy ID", f"CAND_{index:03d}"))
        status, reasons = evaluate_paper_trading_gate(candidate)
        components = calculate_final_benchmark_score(candidate)
        rows.append({
            **candidate,
            **components,
            "Status": status,
            "Rejection Reasons": " | ".join(reasons),
        })

    ranking = pd.DataFrame(rows)
    if ranking.empty:
        ranking = pd.DataFrame(columns=RANKING_COLUMNS)
        rejections = pd.DataFrame(columns=RANKING_COLUMNS)
        shortlist = {
            "paper_trading_ready": [],
            "promising_review": [],
            "rejected_count": 0,
            "formula": FINAL_SCORE_WEIGHTS,
        }
        return ranking, shortlist, rejections

    ranking = ranking.sort_values(
        by=["Final Benchmark Score", "Robustness Score", "Profit Factor", "Candidate ID"],
        ascending=[False, False, False, True],
    )
    ranking = ranking.head(final_shortlist_count).copy()
    paper_ready = ranking[ranking["Status"] == "PAPER_TRADING_READY"].head(
        paper_trading_shortlist_count
    )
    promising = ranking[ranking["Status"] == "PROMISING_REVIEW"].copy()
    rejections = ranking[ranking["Status"] == "REJECTED"].copy()
    shortlist = {
        "paper_trading_ready": paper_ready.to_dict(orient="records"),
        "promising_review": promising.to_dict(orient="records"),
        "rejected_count": int(len(rejections)),
        "formula": FINAL_SCORE_WEIGHTS,
    }
    visible_columns = [column for column in RANKING_COLUMNS if column in ranking.columns]
    return ranking[visible_columns], shortlist, rejections[visible_columns]


def load_candidate_metrics(path: str | Path) -> list[dict]:
    report_path = Path(path)
    if not report_path.exists():
        return []
    if report_path.suffix.lower() == ".json":
        with open(report_path, "r", encoding="utf-8") as file:
            payload = json.load(file)
        return payload if isinstance(payload, list) else payload.get("candidates", [])
    return pd.read_csv(report_path).to_dict(orient="records")


def write_shortlist_reports(
    ranking: pd.DataFrame,
    shortlist: dict,
    rejections: pd.DataFrame,
    ranking_path: str = "reports/final_benchmark_ranking.csv",
    shortlist_path: str = "reports/final_benchmark_shortlist.json",
    rejections_path: str = "reports/final_benchmark_rejections.csv",
) -> None:
    save_csv_report(ranking, ranking_path)
    save_json_report(shortlist, shortlist_path)
    save_csv_report(rejections, rejections_path)
