from src.research.frameworks.adapter import run_framework_decision_series
from src.tests.framework_expansion_test_data import config,data
def test_state_is_future_change_invariant():
 source=data("opening_range_breakout");cutoff=source["execution"].index[-20];before=run_framework_decision_series(config("opening_range_breakout",cutoff),source).decisions;changed={"execution":source["execution"].copy()};cols=list(changed["execution"].select_dtypes(include="number").columns);changed["execution"].loc[changed["execution"].index>cutoff,cols]+=9999;assert before.equals(run_framework_decision_series(config("opening_range_breakout",cutoff),changed).decisions)
if __name__=="__main__":test_state_is_future_change_invariant();print("test_framework_stateful_causality passed")
