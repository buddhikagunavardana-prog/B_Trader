from src.tests.framework_policy_test_data import T0, controller, decision
from src.trading_frameworks.models import FrameworkSignal


def test_timing_can_be_enabled_and_disabled():
    disabled = controller("ema_ribbon_trend").apply(decision(FrameworkSignal.HOLD, "ema_ribbon_trend"), T0)
    enabled_controller = controller("ema_ribbon_trend", enable_controller_timing=True)
    enabled = enabled_controller.apply(decision(FrameworkSignal.HOLD, "ema_ribbon_trend"), T0)
    assert disabled["controller_time_ns"] == 0 and enabled["controller_time_ns"] > 0
    assert set(enabled_controller.last_timing.to_dict()) == {"framework_decision_time_ns", "generic_policy_time_ns", "setup_policy_time_ns", "position_policy_time_ns", "session_policy_time_ns", "level_policy_time_ns", "transition_application_time_ns", "state_serialization_time_ns", "total_controller_time_ns"}


if __name__ == "__main__":
    test_timing_can_be_enabled_and_disabled(); print("test_framework_controller_timing passed")
