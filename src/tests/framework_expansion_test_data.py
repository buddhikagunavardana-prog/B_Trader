from src.research.frameworks.models import FrameworkResearchConfiguration
from src.trading_frameworks.registry import trading_framework_registry
from src.utils.trading_framework_performance import _context

NEW_NAMES={"supertrend_trend_following","ema_ribbon_trend","dual_moving_average_crossover","adx_trend_following","parabolic_sar_trend","bollinger_squeeze_breakout","keltner_channel_breakout","atr_volatility_breakout","opening_range_breakout","rsi_pullback_trend","macd_momentum","vwap_mean_reversion","zscore_mean_reversion","inside_bar_breakout","support_resistance_bounce"}
def config(name,end=None):
 c=trading_framework_registry.resolve(name); return FrameworkResearchConfiguration(name,"1.0.0",{},"SYNTHETIC-USD","crypto_spot",c.schema.metadata.default_timeframes,c.execution_role,end_timestamp=end)
def data(name,rows=120): return _context(name,rows).frames
