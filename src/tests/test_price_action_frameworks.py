from src.tests.framework_expansion_test_data import data
from src.trading_frameworks.loader import load_trading_framework
from src.trading_frameworks.models import FrameworkContext
def test_price_action_uses_completed_inputs():
 for name in ("inside_bar_breakout","support_resistance_bounce"):
  assert load_trading_framework(name).execute(FrameworkContext(data(name))).timestamp==data(name)["execution"].index[-1]
if __name__=="__main__":test_price_action_uses_completed_inputs();print("test_price_action_frameworks passed")
