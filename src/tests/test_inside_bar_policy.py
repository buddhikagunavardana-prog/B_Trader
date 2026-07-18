from src.research.frameworks.state.policies import NestedInsideBarPolicy, PolicyConfiguration
from src.research.frameworks.state.policies.framework_policies import inside_bar_transition


def test_nested_inside_bar_policy_is_typed():
    assert PolicyConfiguration().nested_inside_bar_policy is NestedInsideBarPolicy.KEEP_ORIGINAL_MOTHER_BAR
    assert PolicyConfiguration.from_mapping({"nested_inside_bar_policy": "narrow_range"}).nested_inside_bar_policy is NestedInsideBarPolicy.NARROW_RANGE
    assert inside_bar_transition("armed", age=3, expiry_bars=3, structural_violation=False, breakout_side=None, nested_policy="keep_original_mother_bar")[0] == "expired"
    assert inside_bar_transition("consumed", age=1, expiry_bars=3, structural_violation=False, breakout_side="long", nested_policy="keep_original_mother_bar")[1] == "SETUP_ALREADY_CONSUMED"


if __name__ == "__main__":
    test_nested_inside_bar_policy_is_typed(); print("test_inside_bar_policy passed")
