import json
from src.research.frameworks.state import PositionState,SetupState
def test_state_models_are_execution_free_and_serializable():
 for state in (PositionState(),SetupState()):
  payload=state.to_dict();json.dumps(payload);assert not {"quantity","balance","pnl","fill_price"}.intersection(payload)
if __name__=="__main__":test_state_models_are_execution_free_and_serializable();print("test_framework_state_models passed")
