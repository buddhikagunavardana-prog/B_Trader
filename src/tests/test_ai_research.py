import hashlib
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

from src.ai.providers.base_provider import AIProviderError
from src.ai.providers.gemini_provider import GeminiProvider
from src.ai.providers.mock_provider import MockProvider
from src.ai.research.research_analyst import (
    load_ai_research_config,
    run_research_analysis,
)
from src.ai.research.research_context_builder import build_research_context
from src.ai.research.research_prompt_builder import build_research_prompt
from src.ai.research.research_schema import (
    ResearchSchemaError,
    validate_research_analysis,
)
from src.research.benchmark.benchmark_context import build_benchmark_context
from src.research.orchestrator.adapters.ai_research_adapter import (
    run_ai_research_stage,
)
from src.research.orchestrator.adapters.adapter_result import stage_payload
from src.research.orchestrator.orchestrator_registry import (
    PRODUCTION,
    build_default_stage_registry,
)
from src.research.orchestrator.orchestrator_runner import (
    run_research_orchestrator,
)


def _context():
    config = load_ai_research_config()
    with TemporaryDirectory() as directory:
        root = Path(directory)
        summary = root / "summary.json"
        shortlist = root / "shortlist.json"
        stages = root / "stages.csv"
        summary.write_text(json.dumps({
            "run_id": "AI_TEST_RUN",
            "status": "COMPLETED",
            "generated_candidate_count": 120,
            "promising_review_count": 1,
            "paper_trading_ready_count": 0,
            "paper_trading_readiness": "NOT_READY",
            "reproducibility_status": "PARTIALLY_REPRODUCIBLE",
            "warnings": [],
        }), encoding="utf-8")
        shortlist.write_text(
            json.dumps(_sample_shortlist()), encoding="utf-8"
        )
        stages.write_text(
            "Stage,Status,Task Usage\nfinal_summary,COMPLETED,1\n",
            encoding="utf-8",
        )
        paths = dict(config["input_report_paths"])
        paths.update({
            "benchmark_summary": str(summary),
            "benchmark_shortlist": str(shortlist),
            "benchmark_stages": str(stages),
        })
        return build_research_context(paths, config["max_candidates"])


def _sample_shortlist():
    return {
        "paper_trading_ready": [],
        "promising_review": [{
            "Candidate ID": "TEST_RISK1P0_CAP25P0",
            "Strategy ID": "TEST_RISK1P0_CAP25P0",
            "Pair": "SOLUSDT",
            "Timeframe": "15m",
            "Profit Factor": 1.12,
            "Max Drawdown %": -8.75,
            "Trades": 463,
            "Expectancy": 2.98,
            "Walk Forward Pass Rate": 0.5,
            "Robustness Score": 74.69,
            "Overfitting Risk": 30.4,
            "Monte Carlo Positive Run Rate": 0.87,
            "Monte Carlo Ruin Probability": 0.0,
            "Profitable Regime Count": 2,
            "Status": "PROMISING_REVIEW",
            "Rejection Reasons": (
                "Profit factor below 1.20 | "
                "Walk-forward pass rate below 0.60"
            ),
        }],
        "rejected_count": 0,
        "formula": {},
    }


def _analysis(context=None):
    context = context or _context()
    provider = MockProvider()
    prompt = build_research_prompt(context, 3)
    return json.loads(provider.generate(prompt, context))


def _digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def test_context_extracts_compact_exact_metrics_and_excludes_sensitive_data():
    os.environ["B_TRADER_TEST_SECRET"] = "SHOULD_NOT_APPEAR"
    context = _context()
    serialized = json.dumps(context)

    assert context["run_id"] == "AI_TEST_RUN"
    assert context["candidates"][0]["metrics"]["profit_factor"] == 1.12
    assert context["candidates"][0]["metrics"]["max_drawdown_pct"] == -8.75
    assert context["cost_model"]["historical_fees"] == "zero"
    assert "SHOULD_NOT_APPEAR" not in serialized
    assert "GEMINI_API_KEY" not in serialized
    assert "candidate_trades" not in serialized
    assert "open_time" not in serialized
    assert "def " not in serialized
    os.environ.pop("B_TRADER_TEST_SECRET", None)


def test_context_rejects_raw_or_sensitive_report_paths():
    config = load_ai_research_config()
    paths = dict(config["input_report_paths"])
    paths["benchmark_summary"] = "reports/candidate_trades.csv"
    try:
        build_research_context(paths, 2)
    except ValueError as error:
        assert "rejected" in str(error)
    else:
        raise AssertionError("Raw trade input was accepted")


def test_mock_provider_is_deterministic_and_schema_accepts_valid_output():
    context = _context()
    provider = MockProvider()
    prompt = build_research_prompt(context, 3)
    first = provider.generate(prompt, context)
    second = provider.generate(prompt, context)

    assert first == second
    assert provider.call_count == 2
    validated = validate_research_analysis(json.loads(first), context, 3)
    assert validated["paper_trading_recommendation"] == "NOT_READY"


def test_schema_rejects_malformed_and_unsupported_numeric_claims():
    context = _context()
    malformed = _analysis(context)
    malformed.pop("confidence")
    try:
        validate_research_analysis(malformed, context, 3)
    except ResearchSchemaError as error:
        assert "fields invalid" in str(error)
    else:
        raise AssertionError("Malformed schema was accepted")

    unsupported = _analysis(context)
    unsupported["candidate_findings"][0]["evidence"][0]["observed"] = 9.99
    try:
        validate_research_analysis(unsupported, context, 3)
    except ResearchSchemaError as error:
        assert "Unsupported numeric claim" in str(error)
    else:
        raise AssertionError("Unsupported numeric claim was accepted")


def test_schema_blocks_readiness_threshold_and_configuration_authority():
    context = _context()
    readiness = _analysis(context)
    readiness["paper_trading_recommendation"] = "PAPER_TRADING_READY"
    try:
        validate_research_analysis(readiness, context, 3)
    except ResearchSchemaError as error:
        assert "cannot alter" in str(error)
    else:
        raise AssertionError("AI readiness change was accepted")

    threshold = _analysis(context)
    threshold["recommended_experiments"][0]["required_changes"] = [
        "Lower threshold for promotion"
    ]
    try:
        validate_research_analysis(threshold, context, 3)
    except ResearchSchemaError as error:
        assert "forbidden change" in str(error)
    else:
        raise AssertionError("AI threshold change was accepted")

    try:
        run_research_analysis({
            "enabled": True,
            "allow_configuration_changes": True,
        }, write_output=False)
    except ValueError as error:
        assert "forbidden authority" in str(error)
    else:
        raise AssertionError("Unsafe AI configuration was accepted")


def test_missing_gemini_key_fails_before_sdk_or_network_call():
    original = os.environ.pop("GEMINI_API_KEY", None)
    try:
        provider = GeminiProvider("models/gemini-3.5-flash", 1, 0)
        try:
            provider.generate("{}", {})
        except AIProviderError as error:
            assert "missing" in str(error)
        else:
            raise AssertionError("Missing Gemini key did not fail safely")
    finally:
        if original is not None:
            os.environ["GEMINI_API_KEY"] = original


def test_disabled_analysis_makes_zero_provider_calls_and_preserves_reports():
    provider = MockProvider()
    tracked = [
        "reports/final_benchmark_summary.json",
        "reports/final_benchmark_shortlist.json",
        "reports/final_benchmark_ranking.csv",
    ]
    before = {path: _digest(path) for path in tracked}
    result = run_research_analysis(
        {"enabled": False},
        provider=provider,
        write_output=False,
    )

    assert result["status"] == "DISABLED"
    assert provider.call_count == 0
    assert before == {path: _digest(path) for path in tracked}


def _adapter_fixture(directory, ai_override):
    run_directory = Path(directory) / "ai_stage_test"
    run_directory.mkdir(parents=True)
    (run_directory / "final_benchmark_shortlist.json").write_text(
        json.dumps(_sample_shortlist()), encoding="utf-8"
    )
    config = load_ai_research_config()
    ai_config = {
        **config,
        **ai_override,
        "output_path": str(Path(directory) / "root_ai_analysis.json"),
    }
    context = SimpleNamespace(
        run_id="ai_stage_test",
        metadata={
            "benchmark": {"generated_candidate_limit": 120},
            "ai_research": ai_config,
        },
        run_directory=lambda: run_directory,
    )
    state = SimpleNamespace(
        stage_results={
            "final_summary": {
                "status": "COMPLETED",
                "task_usage": 1,
            }
        }
    )
    stage = SimpleNamespace(name="ai_research_review")
    return context, stage, state, run_directory


def test_mock_enabled_stage_completes_and_failure_is_non_fatal():
    with TemporaryDirectory() as directory:
        context, stage, state, run_directory = _adapter_fixture(
            directory,
            {"enabled": True, "provider": "mock"},
        )
        payload = run_ai_research_stage(context, stage, state)
        result = payload["metadata"]["adapter_result"]
        assert result["status"] == "COMPLETED"
        assert result["metrics"]["provider"] == "mock"
        assert (run_directory / "ai_research_analysis.json").exists()
        assert Path(directory, "root_ai_analysis.json").exists()

    with TemporaryDirectory() as directory:
        context, stage, state, run_directory = _adapter_fixture(
            directory,
            {"enabled": True, "provider": "unsupported"},
        )
        payload = run_ai_research_stage(context, stage, state)
        result = payload["metadata"]["adapter_result"]
        assert result["status"] == "PARTIAL"
        assert result["metrics"]["status"] == "FAILED_ADVISORY"
        failure = json.loads(
            (run_directory / "ai_research_analysis.json").read_text(
                encoding="utf-8"
            )
        )
        assert failure["deterministic_benchmark_unchanged"] is True


def test_default_benchmark_plan_unchanged_and_explicit_ai_appends_stage():
    baseline = build_benchmark_context({"enabled": True})
    baseline_override = baseline.to_orchestrator_override()
    assert len(baseline_override["enabled_stages"]) == 15
    assert baseline_override["enabled_stages"][-1] == "final_summary"

    enabled = build_benchmark_context({
        "enabled": True,
        "metadata": {"ai_research": {"enabled": True, "provider": "mock"}},
    })
    enabled_override = enabled.to_orchestrator_override()
    assert len(enabled_override["enabled_stages"]) == 16
    assert enabled_override["enabled_stages"][-1] == "ai_research_review"


def test_focused_mock_orchestration_completes_after_deterministic_final():
    with TemporaryDirectory() as directory:
        output = Path(directory)
        ai_config = load_ai_research_config()
        ai_config.update({
            "enabled": True,
            "provider": "mock",
            "output_path": str(output / "root_ai_analysis.json"),
        })

        def deterministic_final(context, stage, state):
            target = context.run_directory() / "final_benchmark_shortlist.json"
            target.write_text(
                json.dumps(_sample_shortlist()), encoding="utf-8"
            )
            return stage_payload(
                stage.name,
                "Deterministic final fixture completed",
                task_usage=1,
            )

        registry = build_default_stage_registry(PRODUCTION)
        registry["final_summary"] = registry["final_summary"].with_updates(
            dependencies=[],
            runner=deterministic_final,
        )
        result = run_research_orchestrator({
            "enabled": True,
            "run_id": "focused_mock_ai",
            "dry_run": False,
            "resume_enabled": False,
            "fail_fast": True,
            "continue_on_stage_failure": False,
            "global_task_budget": 10,
            "global_runtime_budget_seconds": 60,
            "output_directory": str(output),
            "smoke_mode": False,
            "enabled_stages": ["final_summary", "ai_research_review"],
            "stage_order": ["final_summary", "ai_research_review"],
            "metadata": {
                "adapter_mode": "PRODUCTION",
                "benchmark": {"generated_candidate_limit": 120},
                "ai_research": ai_config,
            },
        }, registry=registry)

        assert result.status == "COMPLETED"
        assert result.completed_stages == [
            "final_summary",
            "ai_research_review",
        ]
        analysis = json.loads(
            (output / "focused_mock_ai" / "ai_research_analysis.json")
            .read_text(encoding="utf-8")
        )
        assert analysis["provider"] == "mock"
        assert analysis["paper_trading_recommendation"] == "NOT_READY"


if __name__ == "__main__":
    test_context_extracts_compact_exact_metrics_and_excludes_sensitive_data()
    test_context_rejects_raw_or_sensitive_report_paths()
    test_mock_provider_is_deterministic_and_schema_accepts_valid_output()
    test_schema_rejects_malformed_and_unsupported_numeric_claims()
    test_schema_blocks_readiness_threshold_and_configuration_authority()
    test_missing_gemini_key_fails_before_sdk_or_network_call()
    test_disabled_analysis_makes_zero_provider_calls_and_preserves_reports()
    test_mock_enabled_stage_completes_and_failure_is_non_fatal()
    test_default_benchmark_plan_unchanged_and_explicit_ai_appends_stage()
    test_focused_mock_orchestration_completes_after_deterministic_final()
    print("test_ai_research passed")
