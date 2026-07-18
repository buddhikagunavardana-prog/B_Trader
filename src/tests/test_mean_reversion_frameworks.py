from src.tests.framework_expansion_test_data import data
from src.trading_frameworks.loader import load_trading_framework
from src.trading_frameworks.models import FrameworkContext
def test_vwap_and_zscore_defaults_and_risk():
 for name in ("vwap_mean_reversion","zscore_mean_reversion"):
  d=load_trading_framework(name).execute(FrameworkContext(data(name))); assert d.framework==name and d.risk.position_sizing_hint=="fractional_risk"
if __name__=="__main__":test_vwap_and_zscore_defaults_and_risk();print("test_mean_reversion_frameworks passed")
