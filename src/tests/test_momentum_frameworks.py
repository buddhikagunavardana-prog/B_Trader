from src.tests.framework_expansion_test_data import data
from src.trading_frameworks.loader import load_trading_framework
from src.trading_frameworks.models import FrameworkContext
def test_momentum_event_frameworks():
 for name in ("rsi_pullback_trend","macd_momentum"):
  f=load_trading_framework(name); d=data(name); assert f.execute(FrameworkContext(d)).to_dict()==f.execute(FrameworkContext(d)).to_dict()
if __name__=="__main__":test_momentum_event_frameworks();print("test_momentum_frameworks passed")
