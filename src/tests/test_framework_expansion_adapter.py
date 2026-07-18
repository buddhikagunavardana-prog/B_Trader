from src.research.frameworks.adapter import run_framework_decision_series
from src.tests.framework_expansion_test_data import config,data
from src.trading_frameworks.registry import trading_framework_registry
def test_all_twenty_adapter_outputs():
 for name in trading_framework_registry.list_names():
  result=run_framework_decision_series(config(name),data(name)); assert result.validation.valid and len(result.decisions)==120
if __name__=="__main__":test_all_twenty_adapter_outputs();print("test_framework_expansion_adapter passed")
