import shutil
from pathlib import Path

from src.research.benchmark.benchmark_context import BENCHMARK_STAGE_ORDER
from src.research.benchmark.data_coverage_audit import run_data_coverage_audit
from src.research.orchestrator.orchestrator_registry import build_default_stage_registry
from src.research.run_management.run_manager import run_research_run_management


READY = "READY"
READY_WITH_WARNINGS = "READY_WITH_WARNINGS"
BLOCKED = "BLOCKED"


def _stage_registry_uses_smoke_adapters(registry: dict) -> bool:
    production_stage_names = set(BENCHMARK_STAGE_ORDER) - {"load_data", "optimization_search", "monte_carlo", "final_summary"}
    for stage_name in production_stage_names:
        runner = registry.get(stage_name).runner if stage_name in registry else None
        if runner and "smoke_adapter" not in getattr(runner, "__module__", ""):
            return False
    return True


def run_preflight_checks(context, coverage_report=None) -> dict:
    errors = []
    warnings = []

    required_configs = [
        "src/config/full_benchmark.json",
        "src/config/research_run_management.json",
        "src/config/research_orchestrator.json",
        "src/config/optimizer.json",
        "src/config/portfolio.json",
        "src/config/monte_carlo.json",
    ]
    for path in required_configs:
        if not Path(path).exists():
            errors.append(f"CONFIG_FAILURE: Missing config {path}")

    if not callable(run_research_run_management):
        errors.append("CODE_FAILURE: Run manager is unavailable")

    registry = build_default_stage_registry("PRODUCTION")
    missing_stages = [stage for stage in BENCHMARK_STAGE_ORDER if stage not in registry]
    if missing_stages:
        errors.append(f"STAGE_FAILURE: Missing stages {missing_stages}")

    if context.mode == "FULL_BENCHMARK" and _stage_registry_uses_smoke_adapters(registry):
        errors.append(
            "STAGE_FAILURE: Full benchmark blocked because production stage adapters "
            "are not registered; current orchestrator registry is smoke/synthetic only"
        )

    smoke_stages = [
        name
        for name, stage in registry.items()
        if stage.metadata.get("adapter_mode") != "PRODUCTION"
        or (
            stage.runner is not None
            and "smoke_adapter" in getattr(stage.runner, "__module__", "")
        )
    ]
    if smoke_stages:
        errors.append(f"STAGE_FAILURE: Production registry contains smoke stages {smoke_stages}")

    if context.global_task_budget <= 0:
        errors.append("BUDGET_EXCEEDED: Global task budget must be positive")
    if context.global_runtime_budget_seconds <= 0:
        errors.append("BUDGET_EXCEEDED: Runtime budget must be positive")
    if context.generated_candidate_limit <= 0:
        errors.append("CONFIG_FAILURE: Generated candidate limit must be positive")
    if context.monte_carlo_simulations <= 0:
        errors.append("CONFIG_FAILURE: Monte Carlo simulations must be positive")

    supported_timeframes = {"15m"}
    unsupported = [timeframe for timeframe in context.timeframes if timeframe not in supported_timeframes]
    if unsupported:
        errors.append(f"CONFIG_FAILURE: Unsupported timeframes {unsupported}")

    if not context.pairs:
        errors.append("CONFIG_FAILURE: At least one pair is required")

    Path("reports").mkdir(exist_ok=True)
    if not Path("reports").exists():
        errors.append("CODE_FAILURE: reports directory is not writable")

    free_space = shutil.disk_usage(Path.cwd()).free
    if free_space < 1_000_000_000:
        warnings.append("Disk space warning: less than 1GB available")

    if coverage_report is None:
        coverage_report = run_data_coverage_audit(
            context.pairs,
            context.timeframes,
            output_report="reports/data_coverage_audit.csv",
        )

    missing_coverage = coverage_report[
        coverage_report["Coverage Status"].isin(["MISSING_CACHE", "EMPTY_CACHE"])
    ]
    if not missing_coverage.empty:
        errors.append(
            "DATA_FAILURE: Missing cached data for "
            + ", ".join(missing_coverage["Pair"].astype(str).tolist())
        )

    insufficient = coverage_report[
        coverage_report["Coverage Status"] == "INSUFFICIENT_HISTORY"
    ]
    if not insufficient.empty:
        warnings.append(
            "INSUFFICIENT_HISTORY: Some pairs have less than 180 days cached history"
        )

    if errors:
        status = BLOCKED
    elif warnings:
        status = READY_WITH_WARNINGS
    else:
        status = READY

    return {
        "status": status,
        "errors": errors,
        "warnings": warnings,
        "coverage_rows": len(coverage_report),
    }
