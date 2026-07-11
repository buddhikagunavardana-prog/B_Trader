import pandas as pd

from src.research.optimizer.optimizer_candidate import OptimizationCandidate
from src.research.pipeline.pipeline_reporter import save_csv_report


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
