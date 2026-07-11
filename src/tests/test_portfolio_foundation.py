from pathlib import Path
from tempfile import TemporaryDirectory

from src.research.pipeline.pipeline_context import PipelineContext
from src.research.portfolio.portfolio_allocator import (
    allocate_equal_weight,
    allocate_fixed_weight,
    allocate_portfolio,
    allocate_score_weight,
)
from src.research.portfolio.portfolio_candidate import PortfolioCandidate
from src.research.portfolio.portfolio_constraints import (
    filter_valid_candidates,
    validate_allocations,
    validate_candidate_thresholds,
)
from src.research.portfolio.portfolio_context import (
    build_portfolio_context,
    load_portfolio_config,
)
from src.research.portfolio.portfolio_metrics import (
    calculate_diversification_score,
    calculate_portfolio_metrics,
)
from src.research.portfolio.portfolio_report import candidates_to_report
from src.research.portfolio.portfolio_runner import run_portfolio_builder


def _candidate(
    strategy_id="STRAT_A",
    pair="BTCUSDT",
    roi=20.0,
    pf=1.4,
    drawdown=-12.0,
    robustness=75.0,
    risk=20.0,
) -> PortfolioCandidate:
    return PortfolioCandidate.create(
        strategy_id=strategy_id,
        pair=pair,
        template_type="trend",
        expected_roi=roi,
        profit_factor=pf,
        drawdown=drawdown,
        walk_forward_score=70.0,
        robustness_score=robustness,
        risk_score=risk,
    )


def _candidate_list():
    return [
        _candidate("STRAT_A", "BTCUSDT", roi=20.0, pf=1.4),
        _candidate("STRAT_B", "ETHUSDT", roi=15.0, pf=1.3),
        _candidate("STRAT_C", "SOLUSDT", roi=25.0, pf=1.5),
    ]


def _context(**overrides):
    config = {
        "enabled": True,
        "allocation_method": "equal",
        "max_strategies": 10,
        "max_pair_weight": 1.0,
        "max_strategy_weight": 1.0,
        "minimum_diversification": 2,
        "maximum_drawdown_pct": 35.0,
        "minimum_robustness": 60.0,
        "minimum_profit_factor": 1.10,
        "output_report": None,
        "metrics_report": None,
    }
    config.update(overrides)
    return build_portfolio_context(config)


def test_portfolio_config_disabled_by_default():
    config = load_portfolio_config()

    assert config["enabled"] is False
    assert config["allocation_method"] == "equal"


def test_portfolio_context_pipeline_compatibility():
    pipeline_context = _context().to_pipeline_context()

    assert isinstance(pipeline_context, PipelineContext)
    assert pipeline_context.name == "portfolio_builder"
    assert pipeline_context.max_workers == 1


def test_candidate_model_and_report_schema():
    candidate = _candidate()
    report = candidates_to_report([candidate])

    assert candidate.candidate_id.startswith("PORT_")
    assert report.iloc[0]["Strategy ID"] == "STRAT_A"
    assert "Quality Score" in report.columns


def test_equal_weight_allocation():
    allocated = allocate_equal_weight(_candidate_list())

    assert len(allocated) == 3
    assert round(sum(item.allocation_weight for item in allocated), 6) == 1.0
    assert round(allocated[0].allocation_weight, 6) == round(1 / 3, 6)


def test_fixed_weight_allocation_normalizes_weights():
    candidates = _candidate_list()
    allocated = allocate_fixed_weight(
        candidates,
        {
            candidates[0].candidate_id: 2.0,
            candidates[1].candidate_id: 1.0,
            candidates[2].candidate_id: 1.0,
        },
    )

    assert allocated[0].allocation_weight == 0.5
    assert round(sum(item.allocation_weight for item in allocated), 6) == 1.0


def test_score_weight_allocation_is_deterministic():
    first = allocate_score_weight(_candidate_list())
    second = allocate_score_weight(_candidate_list())

    assert [item.allocation_weight for item in first] == [
        item.allocation_weight for item in second
    ]
    assert round(sum(item.allocation_weight for item in first), 6) == 1.0


def test_allocator_unknown_method_fails():
    try:
        allocate_portfolio(_candidate_list(), _context(allocation_method="bad"))
    except ValueError as error:
        assert "Unknown portfolio allocation method" in str(error)
    else:
        raise AssertionError("Unknown allocation method did not fail")


def test_candidate_threshold_constraints():
    context = _context()
    valid = validate_candidate_thresholds(_candidate(), context)
    invalid = validate_candidate_thresholds(
        _candidate(pf=1.0, drawdown=-50.0, robustness=40.0),
        context,
    )

    assert valid.is_valid is True
    assert invalid.is_valid is False
    assert len(invalid.reasons) == 3


def test_filter_valid_candidates_tracks_rejections():
    valid, rejections = filter_valid_candidates(
        [
            _candidate("STRAT_A", "BTCUSDT"),
            _candidate("STRAT_BAD", "XRPUSDT", pf=0.8),
        ],
        _context(),
    )

    assert len(valid) == 1
    assert len(rejections) == 1


def test_allocation_constraints():
    context = _context(max_pair_weight=0.4, max_strategy_weight=0.4)
    allocated = allocate_equal_weight(_candidate_list())
    result = validate_allocations(allocated, context)

    assert result.is_valid is True

    invalid = validate_allocations(
        allocate_equal_weight([
            _candidate("STRAT_A", "BTCUSDT"),
            _candidate("STRAT_A", "BTCUSDT"),
        ]),
        context,
    )

    assert invalid.is_valid is False


def test_portfolio_metrics():
    allocated = allocate_equal_weight(_candidate_list())
    metrics = calculate_portfolio_metrics(allocated)

    assert metrics["total_weight"] == 1.0
    assert metrics["candidate_count"] == 3
    assert metrics["diversification_score"] == 100.0
    assert metrics["expected_portfolio_score"] > 0


def test_diversification_score_handles_empty():
    assert calculate_diversification_score([]) == 0.0


def test_disabled_runner_is_lightweight():
    report, metrics = run_portfolio_builder(
        candidates=_candidate_list(),
        config_override={"enabled": False},
    )

    assert report.empty
    assert metrics == {}


def test_runner_small_smoke_with_temp_reports():
    with TemporaryDirectory() as directory:
        output_report = str(Path(directory) / "portfolio.csv")
        metrics_report = str(Path(directory) / "portfolio.json")
        report, metrics = run_portfolio_builder(
            candidates=_candidate_list(),
            config_override={
                "enabled": True,
                "allocation_method": "score",
                "output_report": output_report,
                "metrics_report": metrics_report,
                "max_pair_weight": 1.0,
                "max_strategy_weight": 1.0,
            },
        )

        assert Path(output_report).exists()
        assert Path(metrics_report).exists()

    assert len(report) == 3
    assert metrics["allocation_valid"] is True


if __name__ == "__main__":
    test_portfolio_config_disabled_by_default()
    test_portfolio_context_pipeline_compatibility()
    test_candidate_model_and_report_schema()
    test_equal_weight_allocation()
    test_fixed_weight_allocation_normalizes_weights()
    test_score_weight_allocation_is_deterministic()
    test_allocator_unknown_method_fails()
    test_candidate_threshold_constraints()
    test_filter_valid_candidates_tracks_rejections()
    test_allocation_constraints()
    test_portfolio_metrics()
    test_diversification_score_handles_empty()
    test_disabled_runner_is_lightweight()
    test_runner_small_smoke_with_temp_reports()
    print("test_portfolio_foundation passed")
