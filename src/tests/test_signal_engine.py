from src.engines.indicator_engine import calculate_indicators
from src.engines.signal_engine import generate_signals
from src.plugins.binance_data import download_klines
from src.strategies.strategy_loader import load_strategy


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
