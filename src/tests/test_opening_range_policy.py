from src.research.frameworks.state.policies import policy_registry
from src.research.frameworks.state.policies.framework_policies import opening_range_transition


def test_opening_range_is_session_bound_and_consumed():
    requirements = policy_registry.requirements("opening_range_breakout")
    assert requirements["setup"] and requirements["session"] and requirements["event_consumption"]
    assert opening_range_transition("forming", opening_complete=False, data_sufficient=True, entry_allowed=True, breakout_side="long", consumed=False)[0] == "forming"
    assert opening_range_transition("armed", opening_complete=True, data_sufficient=True, entry_allowed=False, breakout_side="long", consumed=False)[1] == "SESSION_ENTRY_CUTOFF_REACHED"
    assert opening_range_transition("consumed", opening_complete=True, data_sufficient=True, entry_allowed=True, breakout_side="long", consumed=True)[1] == "SETUP_ALREADY_CONSUMED"


if __name__ == "__main__":
    test_opening_range_is_session_bound_and_consumed(); print("test_opening_range_policy passed")
