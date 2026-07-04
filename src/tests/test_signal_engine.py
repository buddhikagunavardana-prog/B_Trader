from plugins.binance_data import download_klines
from strategies.strategy_loader import load_strategy
from engines.indicator_engine import calculate_indicators
from engines.signal_engine import generate_signals


strategy = load_strategy()

df = download_klines(
    symbol="BTCUSDT",
    interval=strategy.timeframe,
    start_str="1 year ago UTC"
)

df = calculate_indicators(df, strategy)
df = generate_signals(df, strategy)

print(df[[
    "open_time",
    "close",
    "EMA20",
    "EMA50",
    "EMA200",
    "RSI14",
    "MACD",
    "MACD_SIGNAL",
    "SIGNAL"
]].tail(20))

print()
print(df["SIGNAL"].value_counts())