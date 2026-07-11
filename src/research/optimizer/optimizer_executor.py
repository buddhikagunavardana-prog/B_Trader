from src.research.optimizer.optimizer_candidate import OptimizationCandidate
from src.research.pipeline.pipeline_executor import execute_tasks
from src.research.pipeline.pipeline_runner import build_strategy_pair_tasks


def build_optimizer_tasks(
    candidates: list[OptimizationCandidate],
    pairs: list[str],
    timeframe: str,
):
    return build_strategy_pair_tasks(candidates, pairs, timeframe)


def _candidate_metadata_evaluator(task) -> dict:
    candidate = task.payload
    return {
        "Candidate ID": candidate.candidate_id,
        "Strategy ID": candidate.strategy_id,
        "Template Type": candidate.template_type,
        "Pair": task.pair,
        "Timeframe": task.timeframe,
        "Validation Status": candidate.validation_status,
        "Hash": candidate.candidate_hash,
    }


def run_optimizer_metadata_smoke(
    candidates: list[OptimizationCandidate],
    pairs: list[str],
    timeframe: str,
    max_workers: int = 1,
) -> tuple[list[dict], list[dict]]:
    tasks = build_optimizer_tasks(candidates, pairs, timeframe)
    return execute_tasks(
        tasks,
        _candidate_metadata_evaluator,
        max_workers=max_workers,
    )
