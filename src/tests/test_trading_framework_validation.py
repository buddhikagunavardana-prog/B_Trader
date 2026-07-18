from src.tests.trading_framework_test_data import context_for, framework_frame
from src.trading_frameworks.exceptions import FrameworkDataError
from src.trading_frameworks.loader import load_trading_framework
from src.trading_frameworks.models import FrameworkContext, FrameworkSignal
from src.trading_frameworks.registry import trading_framework_registry
from src.trading_frameworks.validator import validate_runtime


def test_runtime_validation_is_deterministic_and_non_mutating():
    for name in ("triple_screen_trading","turtle_trading","ichimoku_cloud_trading","bollinger_mean_reversion","donchian_breakout"):
        result = validate_runtime(load_trading_framework(name), context_for(name))
        assert result.valid, result.to_dict()


def test_empty_short_missing_and_unsorted_inputs_fail_predictably():
    turtle = load_trading_framework("turtle")
    empty = framework_frame(0)
    assert turtle.execute(FrameworkContext({"execution": empty})).signal is FrameworkSignal.NO_TRADE
    short = framework_frame(1)
    assert turtle.execute(FrameworkContext({"execution": short})).signal is FrameworkSignal.NO_TRADE
    missing = framework_frame().drop(columns=["ATR"])
    try:
        turtle.execute(FrameworkContext({"execution": missing}))
    except FrameworkDataError as error:
        assert "ATR" in str(error)
    else:
        raise AssertionError("missing column accepted")
    unsorted = framework_frame().sort_index(ascending=False)
    try:
        turtle.execute(FrameworkContext({"execution": unsorted}))
    except FrameworkDataError as error:
        assert "sorted" in str(error)
    else:
        raise AssertionError("unsorted frame accepted")


if __name__ == "__main__":
    test_runtime_validation_is_deterministic_and_non_mutating()
    test_empty_short_missing_and_unsorted_inputs_fail_predictably()
    print("test_trading_framework_validation passed")
