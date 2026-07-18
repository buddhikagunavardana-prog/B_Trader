from src.research.frameworks.adapter import run_framework_decision_series
from src.tests.framework_research_test_data import precomputed_data, research_configuration
from src.tests.framework_research_test_data import raw_data
from src.research.frameworks.models import PreparationMode
from src.trading_frameworks.registry import trading_framework_registry


def test_all_framework_adapter_paths_are_future_change_invariant():
    for name in ("triple_screen_trading","turtle_trading","ichimoku_cloud_trading","bollinger_mean_reversion","donchian_breakout"):
        data = precomputed_data(name, 120); primary = trading_framework_registry.resolve(name).execution_role
        cutoff = data[primary].index[-25]
        config = research_configuration(name, end_timestamp=cutoff)
        before = run_framework_decision_series(config, data).decisions
        changed = {role: frame.copy(deep=True) for role, frame in data.items()}
        for frame in changed.values():
            numeric = list(frame.select_dtypes(include="number").columns); frame.loc[frame.index > cutoff, numeric] += 1_000_000.0
        after = run_framework_decision_series(config, changed).decisions
        assert before.equals(after), name


def test_confirmed_close_and_computed_missing_paths_remain_causal():
    data = precomputed_data("donchian_breakout", 120); cutoff = data["execution"].index[-20]
    config = research_configuration("donchian_breakout", parameters={"trigger_mode": "confirmed_close"}, end_timestamp=cutoff)
    assert run_framework_decision_series(config, data).validation.valid
    computed = raw_data("donchian_breakout", 120); computed_cutoff = computed["execution"].index[-20]
    computed_config = research_configuration("donchian_breakout", PreparationMode.COMPUTE_MISSING, end_timestamp=computed_cutoff)
    computed_before = run_framework_decision_series(computed_config, computed).decisions
    changed = {"execution": computed["execution"].copy(deep=True)}
    numeric = list(changed["execution"].select_dtypes(include="number").columns)
    changed["execution"].loc[changed["execution"].index > computed_cutoff, numeric] += 1_000_000.0
    assert computed_before.equals(run_framework_decision_series(computed_config, changed).decisions)


if __name__ == "__main__":
    test_all_framework_adapter_paths_are_future_change_invariant(); test_confirmed_close_and_computed_missing_paths_remain_causal(); print("test_framework_research_causality passed")
