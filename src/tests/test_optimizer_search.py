from src.research.optimizer.optimizer_constraints import (
    validate_optimizer_parameters,
)
from src.research.optimizer.optimizer_context import build_optimizer_context
from src.research.optimizer.optimizer_executor import run_optimizer_metadata_smoke
from src.research.optimizer.optimizer_space import build_space_from_parameter_sets
from src.research.optimizer.search.early_stopping import EarlyStoppingController
from src.research.optimizer.search.grid_search import GridSearch
from src.research.optimizer.search.random_search import RandomSearch
from src.research.optimizer.search.search_registry import get_search_algorithm
from src.research.optimizer.search.search_result import SearchResult
from src.research.optimizer.optimizer_runner import run_parameter_optimizer


def _context(**overrides):
    config = {
        "enabled": True,
        "search_algorithm": "grid",
        "random_seed": 42,
        "max_candidates": 5,
        "optimization_budget": 5,
        "max_random_attempts": 100,
        "resume_enabled": True,
        "strict_constraints": True,
        "pairs": ["BTCUSDT"],
        "output_report": None,
        "search_metadata_report": None,
    }
    config.update(overrides)
    return build_optimizer_context(config)


def _trend_parameter_set(fast_values=None, slow_values=None):
    return {
        "template_name": "trend",
        "template_id": "TRD001",
        "enabled": True,
        "max_candidates": 20,
        "parameters": {
            "fast_ema": fast_values or [20, 50],
            "slow_ema": slow_values or [100, 200],
            "rsi_period": [14],
            "rsi_pullback": [40],
            "stop_loss_pct": [1.0],
            "take_profit_pct": [2.0, 3.0],
        },
    }


def _small_space():
    return build_space_from_parameter_sets([_trend_parameter_set()])


def _invalid_ema_space():
    return build_space_from_parameter_sets([
        _trend_parameter_set(fast_values=[100], slow_values=[20])
    ])


def _run_grid(context=None, space=None, existing=None):
    search = GridSearch(
        context=context or _context(),
        parameter_space=space or _small_space(),
        existing_candidate_ids=existing,
    )
    return search.run()


def test_base_search_contract_methods():
    search = GridSearch(context=_context(max_candidates=1), parameter_space=_small_space())

    assert hasattr(search, "prepare_candidates")
    assert hasattr(search, "select_candidates")
    assert hasattr(search, "run")
    assert hasattr(search, "get_state")


def test_grid_search_deterministic_ordering():
    first_candidates, first_result = _run_grid()
    second_candidates, second_result = _run_grid()

    assert first_result.to_dict() == second_result.to_dict()
    assert [item.candidate_id for item in first_candidates] == [
        item.candidate_id for item in second_candidates
    ]


def test_grid_search_budget_limits():
    candidates, result = _run_grid(_context(max_candidates=2, optimization_budget=2))

    assert len(candidates) == 2
    assert result.selected_count == 2
    assert result.stop_reason == "budget reached"


def test_grid_search_exhaustion():
    candidates, result = _run_grid(_context(max_candidates=50, optimization_budget=50))

    assert len(candidates) == 8
    assert result.exhausted is True
    assert result.stop_reason == "search space exhausted"


def test_random_search_same_seed_reproducibility():
    context = _context(search_algorithm="random", random_seed=42)
    first_candidates, _ = RandomSearch(context, _small_space()).run()
    second_candidates, _ = RandomSearch(context, _small_space()).run()

    assert [item.candidate_id for item in first_candidates] == [
        item.candidate_id for item in second_candidates
    ]


def test_random_search_different_seed_changes_order():
    first_candidates, _ = RandomSearch(
        _context(search_algorithm="random", random_seed=42),
        _small_space(),
    ).run()
    second_candidates, _ = RandomSearch(
        _context(search_algorithm="random", random_seed=7),
        _small_space(),
    ).run()

    assert [item.candidate_id for item in first_candidates] != [
        item.candidate_id for item in second_candidates
    ]


def test_random_search_maximum_attempts():
    candidates, result = RandomSearch(
        _context(search_algorithm="random", max_candidates=5),
        _small_space(),
        max_attempts=2,
    ).run()

    assert len(candidates) == 2
    assert result.attempt_count == 2
    assert result.stop_reason == "maximum random attempts reached"


def test_constraint_rejection_and_invalid_ema_rejection():
    candidates, result = _run_grid(
        _context(max_candidates=5),
        _invalid_ema_space(),
    )

    assert candidates == []
    assert result.rejected_count == 2
    assert result.exhausted is True


def test_invalid_rsi_and_macd_constraints():
    rsi = validate_optimizer_parameters({"rsi_buy": 20, "rsi_sell": 30})
    macd = validate_optimizer_parameters({"macd_fast": 26, "macd_slow": 12})

    assert rsi.is_valid is False
    assert "RSI buy must be greater than sell" in rsi.reasons
    assert macd.is_valid is False
    assert "MACD fast must be lower than slow" in macd.reasons


def test_duplicate_prevention_and_resume_behavior():
    first_candidates, _ = _run_grid(_context(max_candidates=2, optimization_budget=2))
    existing = {first_candidates[0].candidate_id, first_candidates[0].candidate_hash}
    resumed_candidates, result = _run_grid(
        _context(max_candidates=2, optimization_budget=2),
        existing=existing,
    )

    assert result.duplicate_count == 1
    assert resumed_candidates[0].candidate_id == first_candidates[1].candidate_id
    assert all(item.candidate_id not in existing for item in resumed_candidates)


def test_stable_candidate_ids_across_algorithms():
    grid_candidates, _ = _run_grid(_context(max_candidates=1, optimization_budget=1))
    random_candidates, _ = RandomSearch(
        _context(
            search_algorithm="random",
            random_seed=4,
            max_candidates=8,
            optimization_budget=8,
        ),
        _small_space(),
    ).run()
    random_ids = {candidate.candidate_id for candidate in random_candidates}

    assert grid_candidates[0].candidate_id in random_ids


def test_search_registry_and_unknown_error():
    search = get_search_algorithm(
        "grid",
        context=_context(),
        parameter_space=_small_space(),
    )

    assert isinstance(search, GridSearch)

    try:
        get_search_algorithm("unknown", context=_context(), parameter_space=_small_space())
    except ValueError as error:
        assert "Unknown optimizer search algorithm" in str(error)
    else:
        raise AssertionError("Unknown search algorithm did not fail")


def test_search_result_serialization():
    result = SearchResult(
        algorithm="grid",
        seed=42,
        requested_budget=2,
        selected_count=1,
        rejected_count=0,
        duplicate_count=0,
        attempt_count=1,
        exhausted=False,
        early_stopped=False,
        stop_reason="budget reached",
        candidate_ids=["OPT_TEST"],
        metadata={"ok": True},
    )

    assert result.to_dict()["candidate_ids"] == ["OPT_TEST"]
    assert result.to_dict()["metadata"]["ok"] is True


def test_early_stopping_patience_and_minimum_improvement():
    controller = EarlyStoppingController(
        enabled=True,
        patience=2,
        minimum_improvement=1.0,
        maximum_failures=5,
    )
    controller.update(10.0)
    controller.update(10.5)
    controller.update(10.7)

    assert controller.should_stop() is True
    assert "non-improving" in controller.get_reason()


def test_early_stopping_failure_threshold():
    controller = EarlyStoppingController(
        enabled=True,
        patience=5,
        minimum_improvement=1.0,
        maximum_failures=2,
    )
    controller.update(None, success=False)
    controller.update(None, success=False)

    assert controller.should_stop() is True
    assert controller.get_reason() == "maximum failed evaluations reached"


def test_disabled_optimizer_behavior():
    report, candidates = run_parameter_optimizer({"enabled": False})

    assert report.empty
    assert candidates == []


def test_existing_optimizer_foundation_compatibility():
    report, candidates = run_parameter_optimizer({
        "enabled": True,
        "search_algorithm": "grid",
        "max_candidates": 3,
        "optimization_budget": 3,
        "output_report": None,
        "search_metadata_report": None,
    })

    assert len(candidates) == 3
    assert len(report) == 3


def test_unified_pipeline_metadata_smoke_compatibility():
    candidates, _ = _run_grid(_context(max_candidates=2, optimization_budget=2))
    rows, failures = run_optimizer_metadata_smoke(
        candidates,
        ["BTCUSDT"],
        "15m",
        max_workers=1,
    )

    assert len(rows) == 2
    assert failures == []
    assert rows[0]["Pair"] == "BTCUSDT"


if __name__ == "__main__":
    test_base_search_contract_methods()
    test_grid_search_deterministic_ordering()
    test_grid_search_budget_limits()
    test_grid_search_exhaustion()
    test_random_search_same_seed_reproducibility()
    test_random_search_different_seed_changes_order()
    test_random_search_maximum_attempts()
    test_constraint_rejection_and_invalid_ema_rejection()
    test_invalid_rsi_and_macd_constraints()
    test_duplicate_prevention_and_resume_behavior()
    test_stable_candidate_ids_across_algorithms()
    test_search_registry_and_unknown_error()
    test_search_result_serialization()
    test_early_stopping_patience_and_minimum_improvement()
    test_early_stopping_failure_threshold()
    test_disabled_optimizer_behavior()
    test_existing_optimizer_foundation_compatibility()
    test_unified_pipeline_metadata_smoke_compatibility()
    print("test_optimizer_search passed")
