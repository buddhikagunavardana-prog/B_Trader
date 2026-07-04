from plugins.binance_data import download_klines
from strategies.strategy_loader import load_strategy
from engines.indicator_engine import calculate_indicators


strategy = load_strategy()

df = download_klines(
    symbol="BTCUSDT",
    interval=strategy.timeframe,
    start_str="1 year ago UTC"
)

df = calculate_indicators(df, strategy)

print(df[[
    "open_time",
    "close",
    "EMA_FAST",
    "EMA_SLOW",
    "EMA_TREND",
    "RSI14",
    "MACD",
    "MACD_SIGNAL",
    "ATR14"
]].tail())