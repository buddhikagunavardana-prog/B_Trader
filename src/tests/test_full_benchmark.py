from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

from src.research.benchmark.benchmark_context import (
    BENCHMARK_STAGE_ORDER,
    BenchmarkContext,
    build_benchmark_context,
    load_benchmark_config,
)
from src.research.benchmark.benchmark_preflight import READY, run_preflight_checks
from src.research.benchmark.benchmark_runner import run_full_benchmark
from src.research.benchmark.benchmark_shortlist import (
    build_final_ranking,
    calculate_final_benchmark_score,
    evaluate_paper_trading_gate,
)
from src.research.benchmark.data_coverage_audit import (
    COVERAGE_COLUMNS,
    audit_pair_timeframe,
    run_data_coverage_audit,
)


def _coverage_ok() -> pd.DataFrame:
    return pd.DataFrame([{
        "Pair": "BTCUSDT",
        "Timeframe": "15m",
        "Earliest Timestamp": "2025-01-01T00:00:00",
        "Latest Timestamp": "2026-01-01T00:00:00",
        "Available Days": 365.0,
        "Available Years": 1.0,
        "Expected Candles": 35041,
        "Actual Candles": 35041,
        "Missing Candle Estimate": 0,
        "Duplicate Count": 0,
        "Invalid Row Count": 0,
        "Coverage Status": "OK",
        "Notes": "",
    }], columns=COVERAGE_COLUMNS)


def _candidate(overrides: dict | None = None) -> dict:
    payload = {
        "Candidate ID": "CAND_001",
        "Strategy ID": "STRAT_001",
        "Pair": "BTCUSDT",
        "Robustness Score": 80,
        "Walk Forward Score": 75,
        "Walk Forward Pass Rate": 0.70,
        "Monte Carlo Stability": 82,
        "Monte Carlo Positive Run Rate": 0.80,
        "Monte Carlo Ruin Probability": 0.01,
        "Profit Factor": 1.35,
        "Max Drawdown %": -12,
        "Expectancy": 0.12,
        "Trades": 120,
        "Minimum Trades": 30,
        "Overfitting Risk": 25,
        "Pair Consistency": 78,
        "Regime Consistency": 70,
        "Profitable Regime Count": 2,
    }
    if overrides:
        payload.update(overrides)
    return payload


def _fake_run_manager(config_override, orchestrator_override):
    return {
        "status": "COMPLETED",
        "run_id": config_override.get("run_id", "fake_run"),
        "manifest": {
            "artifacts": [],
            "warnings": [],
            "errors": [],
        },
        "reproducibility": {"status": "REPRODUCIBLE"},
        "orchestrator_result": {
            "task_usage": 3,
            "runtime_usage": 0.1,
            "completed_stages": ["load_data", "optimization_search", "monte_carlo"],
            "failed_stages": [],
            "blocked_stages": [],
            "stage_results": {
                "load_data": {"status": "COMPLETED", "task_usage": 1},
                "optimization_search": {"status": "COMPLETED", "task_usage": 1},
                "monte_carlo": {"status": "COMPLETED", "task_usage": 1},
            },
        },
    }


def test_config_loading_and_disabled_behavior():
    config = load_benchmark_config()
    result = run_full_benchmark({"enabled": False})

    assert config["enabled"] is False
    assert result["status"] == "DISABLED"


def test_dry_run_behavior_with_fake_run_manager():
    result = run_full_benchmark(
        {
            "enabled": True,
            "mode": "DRY_RUN",
            "pairs": ["BTCUSDT"],
            "timeframes": ["15m"],
        },
        run_manager=_fake_run_manager,
    )

    assert result["status"] == "COMPLETED"
    assert result["context"]["mode"] == "DRY_RUN"


def test_preflight_ready_for_small_and_full_after_production_adapters():
    small = build_benchmark_context({
        "enabled": True,
        "mode": "SMALL_BENCHMARK",
        "pairs": ["BTCUSDT"],
        "timeframes": ["15m"],
    })
    full = build_benchmark_context({
        "enabled": True,
        "mode": "FULL_BENCHMARK",
        "pairs": ["BTCUSDT"],
        "timeframes": ["15m"],
    })

    assert run_preflight_checks(small, _coverage_ok())["status"] == READY
    assert run_preflight_checks(full, _coverage_ok())["status"] == READY


def test_coverage_audit_schema_with_synthetic_cache():
    with TemporaryDirectory() as directory:
        cache_path = Path(directory) / "btcusdt_15m_1_year_ago_utc_none.csv"
        pd.DataFrame([
            {
                "open_time": "2026-01-01 00:00:00",
                "open": 1.0,
                "high": 2.0,
                "low": 0.5,
                "close": 1.5,
                "volume": 10.0,
                "close_time": "2026-01-01 00:14:59",
            },
            {
                "open_time": "2026-01-01 00:15:00",
                "open": 1.5,
                "high": 2.5,
                "low": 1.0,
                "close": 2.0,
                "volume": 12.0,
                "close_time": "2026-01-01 00:29:59",
            },
        ]).to_csv(cache_path, index=False)

        row = audit_pair_timeframe("BTCUSDT", "15m", directory)
        report = run_data_coverage_audit(
            ["BTCUSDT"],
            ["15m"],
            output_report=str(Path(directory) / "coverage.csv"),
            cache_dir=directory,
        )

        assert list(report.columns) == COVERAGE_COLUMNS
        assert row["Actual Candles"] == 2


def test_benchmark_context_conversion_and_overrides():
    context = build_benchmark_context({
        "enabled": True,
        "mode": "SMALL_BENCHMARK",
        "pairs": ["BTCUSDT", "ETHUSDT"],
        "timeframes": ["15m"],
    })
    pipeline_context = context.to_pipeline_context()
    orchestrator_override = context.to_orchestrator_override()

    assert isinstance(context, BenchmarkContext)
    assert pipeline_context.name == "full_benchmark"
    assert context.pairs == ["BTCUSDT"]
    assert orchestrator_override["metadata"]["adapter_mode"] == "PRODUCTION"
    assert orchestrator_override["enabled_stages"][0] == "load_data"
    assert orchestrator_override["enabled_stages"][-1] == "final_summary"


def test_stage_order_and_candidate_budget_enforcement():
    context = build_benchmark_context({
        "enabled": True,
        "mode": "SMALL_BENCHMARK",
        "generated_candidate_limit": 60,
        "optimization_candidate_budget": 500,
        "walk_forward_windows": 5,
        "monte_carlo_simulations": 1000,
        "global_task_budget": 100000,
    })

    assert BENCHMARK_STAGE_ORDER[0] == "load_data"
    assert context.generated_candidate_limit == 5
    assert context.optimization_candidate_budget == 10
    assert context.walk_forward_windows == 2
    assert context.monte_carlo_simulations == 20
    assert context.global_task_budget == 100


def test_full_mode_uses_fake_manager_after_production_preflight_ready():
    result = run_full_benchmark({
        "enabled": True,
        "mode": "FULL_BENCHMARK",
        "pairs": ["BTCUSDT"],
        "timeframes": ["15m"],
    }, run_manager=_fake_run_manager)

    assert result["status"] == "COMPLETED"
    assert result["preflight"]["status"] == READY


def test_empty_shortlist_behavior():
    ranking, shortlist, rejections = build_final_ranking([])

    assert ranking.empty
    assert shortlist["paper_trading_ready"] == []
    assert rejections.empty


def test_paper_trading_gate_pass_and_fail():
    pass_status, pass_reasons = evaluate_paper_trading_gate(_candidate())
    fail_status, fail_reasons = evaluate_paper_trading_gate(_candidate({
        "Profit Factor": 1.0,
        "Trades": 3,
    }))

    assert pass_status == "PAPER_TRADING_READY"
    assert pass_reasons == []
    assert fail_status == "REJECTED"
    assert fail_reasons


def test_final_ranking_score_bounds_and_determinism():
    first = calculate_final_benchmark_score(_candidate())
    second = calculate_final_benchmark_score(_candidate())
    ranking, shortlist, rejections = build_final_ranking([
        _candidate({"Candidate ID": "B"}),
        _candidate({"Candidate ID": "A"}),
    ])

    assert 0 <= first["Final Benchmark Score"] <= 100
    assert first == second
    assert ranking.iloc[0]["Candidate ID"] == "A"
    assert shortlist["paper_trading_ready"]
    assert rejections.empty


def test_rejection_reasons_and_report_schema():
    ranking, shortlist, rejections = build_final_ranking([
        _candidate({
            "Candidate ID": "BAD",
            "Profit Factor": 0.8,
            "Trades": 0,
            "Profitable Regime Count": 0,
        })
    ])

    assert ranking.iloc[0]["Status"] == "REJECTED"
    assert "Profit factor" in ranking.iloc[0]["Rejection Reasons"]
    assert shortlist["rejected_count"] == 1
    assert len(rejections) == 1


def test_run_specific_output_isolation_and_reproducibility_metadata():
    result = run_full_benchmark(
        {
            "enabled": True,
            "mode": "SMALL_BENCHMARK",
            "run_id": "fake_small",
            "pairs": ["BTCUSDT"],
            "timeframes": ["15m"],
            "output_directory": "reports/research_runs",
        },
        run_manager=_fake_run_manager,
    )

    assert result["run_result"]["run_id"] == "fake_small"
    assert result["summary"]["reproducibility_status"] == "REPRODUCIBLE"


def test_resume_behavior_with_fake_run_manager():
    result = run_full_benchmark(
        {
            "enabled": True,
            "mode": "SMALL_BENCHMARK",
            "run_id": "resume_fake",
            "resume_enabled": True,
            "pairs": ["BTCUSDT"],
            "timeframes": ["15m"],
        },
        run_manager=_fake_run_manager,
    )

    assert result["context"]["resume_enabled"] is True
    assert result["status"] == "COMPLETED"


if __name__ == "__main__":
    test_config_loading_and_disabled_behavior()
    test_dry_run_behavior_with_fake_run_manager()
    test_preflight_ready_for_small_and_full_after_production_adapters()
    test_coverage_audit_schema_with_synthetic_cache()
    test_benchmark_context_conversion_and_overrides()
    test_stage_order_and_candidate_budget_enforcement()
    test_full_mode_uses_fake_manager_after_production_preflight_ready()
    test_empty_shortlist_behavior()
    test_paper_trading_gate_pass_and_fail()
    test_final_ranking_score_bounds_and_determinism()
    test_rejection_reasons_and_report_schema()
    test_run_specific_output_isolation_and_reproducibility_metadata()
    test_resume_behavior_with_fake_run_manager()
    print("test_full_benchmark passed")
