import pandas as pd

from src.engines.backtest_engine import BacktestEngine
from src.strategies.strategy_loader import load_strategy


strategy = load_strategy()

data = {
    "close": [100, 101, 102, 103, 104, 105],
    "high":  [101, 102, 103, 104, 105, 106],
    "low":   [99, 100, 101, 102, 103, 104]
}

df = pd.DataFrame(data)

signals = pd.Series(["BUY", "HOLD", "HOLD", "HOLD", "HOLD", "HOLD"])

engine = BacktestEngine(strategy)

result = engine.run(df, signals)

print(result)
