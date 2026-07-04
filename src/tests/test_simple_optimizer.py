from src.strategies.strategy_loader import load_strategy
from src.plugins.binance_data import download_klines
from src.optimizers.optimizer_engine import OptimizerEngine


strategy = load_strategy("src/config/strategy.json")

df = download_klines(
    symbol="BTCUSDT",
    interval="1h",
    start_str="1 year ago UTC"
)

optimizer = OptimizerEngine(strategy)

results = optimizer.optimize(
    df=df,
    sl_values=[1, 1.5, 2, 2.5],
    tp_values=[2, 3, 4, 5]
)

print("\n===== OPTIMIZATION RESULTS =====")
print(results.to_string(index=False))

print("\n===== BEST RESULT =====")
print(results.iloc[0].to_string())