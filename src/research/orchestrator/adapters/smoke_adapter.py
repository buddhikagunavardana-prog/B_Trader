from pathlib import Path

from src.research.monte_carlo.monte_carlo_input import MonteCarloInput
from src.research.monte_carlo.monte_carlo_runner import run_monte_carlo_validation
from src.research.optimizer.optimizer_runner import run_parameter_optimizer
from src.research.pipeline.pipeline_reporter import save_json_report


def _artifact(path: Path, name: str, producer_stage: str, artifact_type: str = "JSON"):
    return {
        "name": name,
        "artifact_type": artifact_type,
        "path": str(path),
        "producer_stage": producer_stage,
        "schema_version": "1",
        "required": True,
        "status": "CREATED",
        "metadata": {},
    }


def run_synthetic_metadata_stage(context, stage, state):
    output_path = context.run_directory() / f"{stage.name}.json"
    payload = {
        "stage": stage.name,
        "run_id": context.run_id,
        "synthetic": True,
        "seed": context.random_seed,
    }
    save_json_report(payload, str(output_path))
    return {
        "message": "Synthetic metadata stage completed",
        "task_usage": 1,
        "artifacts": [_artifact(output_path, stage.name, stage.name)],
        "metadata": payload,
    }


def run_optimizer_smoke_stage(context, stage, state):
    output_path = context.run_directory() / "optimizer_candidates.csv"
    metadata_path = context.run_directory() / "optimizer_search_metadata.json"
    report, candidates = run_parameter_optimizer({
        "enabled": True,
        "search_algorithm": "grid",
        "random_seed": context.random_seed,
        "max_candidates": 3,
        "optimization_budget": 3,
        "parallel_workers": 1,
        "output_report": str(output_path),
        "search_metadata_report": str(metadata_path),
    })
    return {
        "message": "Optimizer smoke stage completed",
        "task_usage": len(candidates),
        "artifacts": [
            _artifact(output_path, "optimizer_candidates", stage.name, "CSV"),
            _artifact(metadata_path, "optimizer_search_metadata", stage.name),
        ],
        "metadata": {"candidate_count": len(candidates), "rows": len(report)},
    }


def run_monte_carlo_smoke_stage(context, stage, state):
    output_path = context.run_directory() / "monte_carlo_results.csv"
    summary_path = context.run_directory() / "monte_carlo_summary.json"
    mc_input = MonteCarloInput(
        strategy_id="SMOKE_STRAT",
        strategy_name="Smoke Strategy",
        pair="BTCUSDT",
        template_type="synthetic",
        initial_balance=10000,
        trade_returns=[1.0, -0.5, 1.25, -0.75, 0.6],
        trade_pnls=[100, -50, 125, -75, 60],
        fees=[1.0] * 5,
    )
    report, summary = run_monte_carlo_validation(mc_input, {
        "enabled": True,
        "simulation_count": 5,
        "random_seed": context.random_seed,
        "output_report": str(output_path),
        "output_summary": str(summary_path),
        "minimum_simulation_count": 1,
        "minimum_positive_run_rate": 0.0,
        "maximum_ruin_probability": 1.0,
    })
    return {
        "message": "Monte Carlo smoke stage completed",
        "task_usage": len(report),
        "artifacts": [
            _artifact(output_path, "monte_carlo_results", stage.name, "CSV"),
            _artifact(summary_path, "monte_carlo_summary", stage.name),
        ],
        "metadata": {
            "simulation_count": summary["Simulation Count"],
            "positive_run_rate": summary["Positive Run Rate"],
        },
    }


def run_final_summary_stage(context, stage, state):
    output_path = context.run_directory() / "final_summary.json"
    payload = {
        "run_id": context.run_id,
        "completed_stages": list(state.completed_stages),
        "failed_stages": list(state.failed_stages),
        "blocked_stages": list(state.blocked_stages),
    }
    save_json_report(payload, str(output_path))
    return {
        "message": "Final summary stage completed",
        "task_usage": 1,
        "artifacts": [_artifact(output_path, "final_summary", stage.name)],
        "metadata": payload,
    }
