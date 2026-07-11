from pathlib import Path
from tempfile import TemporaryDirectory

from src.research.optimizer.optimizer_candidate import OptimizationCandidate
from src.research.optimizer.optimizer_constraints import (
    validate_optimizer_parameters,
)
from src.research.optimizer.optimizer_context import (
    build_optimizer_context,
    load_optimizer_config,
)
from src.research.optimizer.optimizer_executor import (
    build_optimizer_tasks,
    run_optimizer_metadata_smoke,
)
from src.research.optimizer.optimizer_report import candidates_to_report
from src.research.optimizer.optimizer_runner import (
    build_optimization_candidates,
    run_parameter_optimizer,
)
from src.research.optimizer.optimizer_space import (
    build_space_from_parameter_sets,
    load_current_optimization_space,
    parameter_family,
)
from src.research.pipeline.pipeline_context import PipelineContext
from src.strategies.parameter_generator import ParameterGenerator


def _valid_parameters() -> dict:
    return {
        "template_id": "TRD001",
        "timeframe": "15m",
        "fast_ema": 20,
        "slow_ema": 100,
        "rsi_period": 14,
        "rsi_pullback": 40,
        "stop_loss_pct": 1.0,
        "take_profit_pct": 2.0,
    }


def _sample_parameter_sets() -> list[dict]:
    return [{
        "template_name": "trend",
        "template_id": "TRD001",
        "enabled": True,
        "max_candidates": 2,
        "parameters": {
            "fast_ema": [20],
            "slow_ema": [100],
            "rsi_period": [14],
            "rsi_pullback": [40],
            "stop_loss_pct": [1.0],
            "take_profit_pct": [2.0],
        },
    }]


def test_optimizer_config_disabled_by_default():
    config = load_optimizer_config()

    assert config["enabled"] is False
    assert config["parameter_space"] == "current"
    assert config["strict_constraints"] is True


def test_optimizer_context_converts_to_pipeline_context():
    context = build_optimizer_context({
        "enabled": False,
        "max_candidates": 3,
        "optimization_budget": 3,
        "pairs": ["BTCUSDT"],
    })
    pipeline_context = context.to_pipeline_context()

    assert isinstance(pipeline_context, PipelineContext)
    assert pipeline_context.name == "parameter_optimizer"
    assert pipeline_context.pairs == ["BTCUSDT"]


def test_current_parameter_space_loads_existing_json():
    space = load_current_optimization_space()

    assert space.source == "current"
    assert len(space.templates) >= 1
    assert "EMA" in space.supported_families()
    assert "RSI" in space.supported_families()


def test_parameter_space_uses_parameter_json_shape():
    space = build_space_from_parameter_sets(_sample_parameter_sets())
    template = space.templates[0]

    assert template.template_name == "trend"
    assert template.to_parameter_set()["parameters"]["fast_ema"] == [20]
    assert parameter_family("macd_fast") == "MACD"
    assert parameter_family("supertrend_multiplier") == "SuperTrend"


def test_constraints_accept_valid_and_reject_invalid():
    valid = validate_optimizer_parameters(_valid_parameters())
    invalid = validate_optimizer_parameters({
        "fast_ema": 100,
        "slow_ema": 20,
        "macd_fast": 26,
        "macd_slow": 12,
        "volume_multiplier": 0,
        "atr_multiplier": -1,
    })

    assert valid.is_valid is True
    assert invalid.is_valid is False
    assert "EMA fast must be lower than slow" in invalid.reasons
    assert "MACD fast must be lower than slow" in invalid.reasons


def test_candidate_creation_and_hash_are_deterministic():
    validation = validate_optimizer_parameters(_valid_parameters())
    first = OptimizationCandidate.create(
        strategy_id="TRD001_TEST",
        template_type="trend",
        parameters=_valid_parameters(),
        validation=validation,
        optimization_metadata={"space": "unit"},
    )
    second = OptimizationCandidate.create(
        strategy_id="TRD001_TEST",
        template_type="trend",
        parameters=dict(reversed(list(_valid_parameters().items()))),
        validation=validation,
        optimization_metadata={"space": "unit"},
    )

    assert first.candidate_hash == second.candidate_hash
    assert first.candidate_id == second.candidate_id
    assert first.validation_status == "VALID"


def test_candidate_report_schema():
    candidate = OptimizationCandidate.create(
        strategy_id="TRD001_TEST",
        template_type="trend",
        parameters=_valid_parameters(),
        validation=validate_optimizer_parameters(_valid_parameters()),
    )
    report = candidates_to_report([candidate])

    assert list(report.columns) == [
        "Candidate ID",
        "Strategy ID",
        "Template Type",
        "Parameters",
        "Validation Status",
        "Validation Reasons",
        "Optimization Metadata",
        "Hash",
    ]


def test_pipeline_compatibility_for_optimizer_tasks():
    candidate = OptimizationCandidate.create(
        strategy_id="TRD001_TEST",
        template_type="trend",
        parameters=_valid_parameters(),
        validation=validate_optimizer_parameters(_valid_parameters()),
    )
    tasks = build_optimizer_tasks([candidate], ["BTCUSDT"], "15m")
    rows, failures = run_optimizer_metadata_smoke(
        [candidate],
        ["BTCUSDT"],
        "15m",
        max_workers=1,
    )

    assert len(tasks) == 1
    assert len(rows) == 1
    assert failures == []
    assert rows[0]["Candidate ID"] == candidate.candidate_id


def test_disabled_optimizer_mode_is_lightweight():
    report, candidates = run_parameter_optimizer({"enabled": False})

    assert report.empty
    assert candidates == []


def test_small_optimizer_smoke_prepares_metadata_only():
    with TemporaryDirectory() as directory:
        output_report = str(Path(directory) / "optimizer_candidates.csv")
        report, candidates = run_parameter_optimizer({
            "enabled": True,
            "max_candidates": 3,
            "optimization_budget": 3,
            "parallel_workers": 1,
            "pairs": ["BTCUSDT"],
            "output_report": output_report,
        })

        assert Path(output_report).exists()

    assert len(candidates) == 3
    assert len(report) == 3
    assert all(candidate.validation_status == "VALID" for candidate in candidates)


def test_parameter_generator_backward_compatibility():
    generated = ParameterGenerator().generate_candidates(global_max_candidates=2)
    optimizer_candidates = build_optimization_candidates(2)

    assert len(generated) == 2
    assert len(optimizer_candidates) == 2
    assert generated[0]["strategy_id"] == optimizer_candidates[0].strategy_id


if __name__ == "__main__":
    test_optimizer_config_disabled_by_default()
    test_optimizer_context_converts_to_pipeline_context()
    test_current_parameter_space_loads_existing_json()
    test_parameter_space_uses_parameter_json_shape()
    test_constraints_accept_valid_and_reject_invalid()
    test_candidate_creation_and_hash_are_deterministic()
    test_candidate_report_schema()
    test_pipeline_compatibility_for_optimizer_tasks()
    test_disabled_optimizer_mode_is_lightweight()
    test_small_optimizer_smoke_prepares_metadata_only()
    test_parameter_generator_backward_compatibility()
    print("test_optimizer_foundation passed")
