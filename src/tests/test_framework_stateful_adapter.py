from src.research.frameworks.adapter import run_framework_decision_series
from src.research.frameworks.validator import STATE_COLUMNS
from src.tests.framework_expansion_test_data import config,data
def test_stateful_output_and_run_reset():
 c=config("inside_bar_breakout");a=run_framework_decision_series(c,data(c.framework));b=run_framework_decision_series(c,data(c.framework));assert set(STATE_COLUMNS).issubset(a.decisions.columns) and a.decisions.equals(b.decisions);assert a.decisions.iloc[0].research_position_state=="flat"
if __name__=="__main__":test_stateful_output_and_run_reset();print("test_framework_stateful_adapter passed")
