from src.research.frameworks.models import PreparationMode
from src.research.frameworks.preparation import IndicatorRequest,compute_indicator_requests,prepare_timeframe_data
from src.tests.framework_research_test_data import raw_data,research_configuration
from src.trading_frameworks.loader import load_trading_framework
def test_ema_ribbon_compute_missing_and_alias_collision():
 c=research_configuration("ema_ribbon_trend",PreparationMode.COMPUTE_MISSING);p=prepare_timeframe_data(c,load_trading_framework(c.framework),raw_data(c.framework));assert {"EMA_8","EMA_13","EMA_21","EMA_34","EMA_55"}.issubset(p["execution"].frame.columns)
 frame=raw_data("ema_ribbon_trend")["execution"].copy()
 try:compute_indicator_requests(frame,(IndicatorRequest("ema",{"period":8},"X"),IndicatorRequest("ema",{"period":13},"X")))
 except ValueError:pass
 else:raise AssertionError("duplicate alias accepted")
if __name__=="__main__":test_ema_ribbon_compute_missing_and_alias_collision();print("test_framework_multi_period_preparation passed")
