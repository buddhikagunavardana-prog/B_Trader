import pandas as pd

from src.research.optimizer.optimizer_candidate import OptimizationCandidate
from src.research.optimizer.search.search_result import SearchResult
from src.research.pipeline.pipeline_reporter import save_csv_report, save_json_report


def candidates_to_report(
    candidates: list[OptimizationCandidate],
) -> pd.DataFrame:
    return pd.DataFrame([candidate.to_dict() for candidate in candidates])


def save_candidate_report(
    candidates: list[OptimizationCandidate],
    output_report: str,
) -> pd.DataFrame:
    report = candidates_to_report(candidates)
    save_csv_report(report, output_report)

    return report


def save_search_metadata(
    search_result: SearchResult,
    output_report: str,
) -> dict:
    payload = search_result.to_dict()
    save_json_report(payload, output_report)

    return payload
