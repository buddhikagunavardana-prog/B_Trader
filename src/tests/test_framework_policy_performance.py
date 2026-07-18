from time import perf_counter
import pandas as pd
from src.tests.framework_policy_test_data import T0, controller, decision
from src.trading_frameworks.models import FrameworkSignal


def test_controller_scales_linearly_for_synthetic_hold_rows():
    durations = []
    for rows in (1000, 10000):
        c = controller("ema_ribbon_trend", enable_controller_timing=True)
        started = perf_counter()
        for i in range(rows):
            c.apply(decision(FrameworkSignal.HOLD, "ema_ribbon_trend"), T0 + pd.Timedelta(minutes=i))
        durations.append(perf_counter() - started)
    assert durations[1] < durations[0] * 20 and durations[1] < 10


if __name__ == "__main__":
    test_controller_scales_linearly_for_synthetic_hold_rows(); print("test_framework_policy_performance passed")
