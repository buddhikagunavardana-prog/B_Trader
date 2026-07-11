import pandas as pd

from src.research.pipeline.pipeline_reporter import save_csv_report, save_json_report
from src.research.portfolio.portfolio_candidate import PortfolioCandidate


def candidates_to_report(candidates: list[PortfolioCandidate]) -> pd.DataFrame:
    return pd.DataFrame([candidate.to_dict() for candidate in candidates])


def save_portfolio_report(
    candidates: list[PortfolioCandidate],
    output_report: str,
) -> pd.DataFrame:
    report = candidates_to_report(candidates)
    save_csv_report(report, output_report)

    return report


def save_portfolio_metrics(metrics: dict, metrics_report: str) -> dict:
    save_json_report(metrics, metrics_report)
    return metrics
