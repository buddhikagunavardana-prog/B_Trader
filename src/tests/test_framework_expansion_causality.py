from src.research.frameworks.adapter import run_framework_decision_series
from src.tests.framework_expansion_test_data import config,data
from src.trading_frameworks.registry import trading_framework_registry
def test_all_twenty_future_invariance():
 for name in trading_framework_registry.list_names():
  source=data(name); role=trading_framework_registry.resolve(name).execution_role; cutoff=source[role].index[-20]; before=run_framework_decision_series(config(name,cutoff),source).decisions; changed={r:f.copy(deep=True) for r,f in source.items()}
  for frame in changed.values():
   cols=list(frame.select_dtypes(include="number").columns); frame.loc[frame.index>cutoff,cols]+=999999
  assert before.equals(run_framework_decision_series(config(name,cutoff),changed).decisions),name
if __name__=="__main__":test_all_twenty_future_invariance();print("test_framework_expansion_causality passed")
