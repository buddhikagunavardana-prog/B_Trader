import pandas as pd
from src.research.frameworks.state.policies import validate_policy_rows


def test_missing_reason_code_is_rejected():
    frame = pd.DataFrame([{"policy_allowed": True, "policy_reason_code": "", "research_position_state": "flat", "position_transition": "none", "opposite_signal_action": "none"}])
    assert validate_policy_rows(frame)[0].code == "MISSING_REASON_CODE"


if __name__ == "__main__":
    test_missing_reason_code_is_rejected(); print("test_framework_policy_validation passed")
