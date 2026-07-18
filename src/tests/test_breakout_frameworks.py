from src.tests.framework_expansion_test_data import data
from src.trading_frameworks.loader import load_trading_framework
from src.trading_frameworks.models import FrameworkContext

def test_breakout_frameworks_are_event_based_and_finite():
 for name in ("bollinger_squeeze_breakout","keltner_channel_breakout","atr_volatility_breakout","opening_range_breakout"):
  decision=load_trading_framework(name).execute(FrameworkContext(data(name))); assert 0<=decision.confidence<=1 and decision.diagnostics.get("event_based",True)
if __name__=="__main__":test_breakout_frameworks_are_event_based_and_finite();print("test_breakout_frameworks passed")
