from src.indicators.trend.ema import calculate_ema
from src.indicators.trend.supertrend import calculate_supertrend
from src.indicators.trend.sma import calculate_sma
from src.indicators.trend.wma import calculate_wma
from src.indicators.trend.dema import calculate_dema
from src.indicators.trend.tema import calculate_tema
from src.indicators.trend.vwma import calculate_vwma

from src.indicators.momentum.rsi import calculate_rsi
from src.indicators.momentum.macd import calculate_macd
from src.indicators.momentum.stochastic import calculate_stochastic
from src.indicators.momentum.stochastic_rsi import calculate_stochastic_rsi
from src.indicators.momentum.cci import calculate_cci
from src.indicators.momentum.williams_r import calculate_williams_r
from src.indicators.momentum.roc import calculate_roc
from src.indicators.momentum.momentum import calculate_momentum

from src.indicators.volatility.atr import calculate_atr
from src.indicators.volatility.bollinger import calculate_bollinger_bands
from src.indicators.volatility.keltner import calculate_keltner_channel
from src.indicators.volatility.donchian import calculate_donchian_channel
from src.indicators.volatility.chaikin import calculate_chaikin_volatility

from src.indicators.volume.volume import calculate_volume_indicators

from src.indicators.structure.support_resistance import calculate_support_resistance

from src.indicators.candlestick.candlestick import calculate_candlestick_patterns

from src.indicators.market_strength.adx import calculate_adx


INDICATOR_REGISTRY = {
    # Trend
    "ema": calculate_ema,
    "sma": calculate_sma,
    "wma": calculate_wma,
    "hma": calculate_hma,
    "dema": calculate_dema,
    "tema": calculate_tema,
    "vwma": calculate_vwma,
    "supertrend": calculate_supertrend,
    

    # Momentum
    "rsi": calculate_rsi,
    "macd": calculate_macd,# Momentum
    "stochastic": calculate_stochastic,
    "stochastic_rsi": calculate_stochastic_rsi,
    "cci": calculate_cci,
    "williams_r": calculate_williams_r,
    "roc": calculate_roc,
    "momentum": calculate_momentum,

    # Volatility
    "atr": calculate_atr,
    "bollinger": calculate_bollinger_bands,
    "keltner": calculate_keltner_channel,
    "donchian": calculate_donchian_channel,
    "chaikin_volatility": calculate_chaikin_volatility,

    # Volume
    "volume": calculate_volume_indicators,

    # Structure
    "support_resistance": calculate_support_resistance,

    # Candlestick
    "candlestick": calculate_candlestick_patterns,


    # Market Strength
    "adx": calculate_adx,
}


def get_indicator(name):
    if name not in INDICATOR_REGISTRY:
        raise ValueError(f"Indicator not found in registry: {name}")

    return INDICATOR_REGISTRY[name]


def list_indicators():
    return list(INDICATOR_REGISTRY.keys())