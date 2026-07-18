from src.tests.framework_expansion_test_data import NEW_NAMES,data
from src.trading_frameworks.loader import load_trading_framework
from src.trading_frameworks.models import FrameworkContext,FrameworkDecision

def test_trend_framework_defaults_determinism_and_nonmutation():
 for name in sorted(n for n in NEW_NAMES if n in {"supertrend_trend_following","ema_ribbon_trend","dual_moving_average_crossover","adx_trend_following","parabolic_sar_trend"}):
  f=load_trading_framework(name); d=data(name); before=d["execution"].copy(deep=True); a=f.execute(FrameworkContext(d)); b=f.execute(FrameworkContext(d)); assert isinstance(a,FrameworkDecision) and a.to_dict()==b.to_dict(); assert d["execution"].equals(before)
if __name__=="__main__":test_trend_framework_defaults_determinism_and_nonmutation();print("test_trend_following_frameworks passed")
