import json
import pandas as pd

from src.strategies.strategy_loader import load_strategy
from src.strategies.strategy_validator import validate_strategy
from src.engines.indicator_engine import calculate_indicators
from src.engines.signal_engine import generate_signals
from src.engines.backtest_engine import BacktestEngine
from src.optimizers.optimizer_engine import OptimizerEngine


def test_system():
    print("\n========================================")
    print("B TRADER SYSTEM TEST")
    print("========================================")

    with open("src/config/strategy.json", "r") as file:
        raw_strategy = json.load(file)

    validate_strategy(raw_strategy)
    print("✅ Strategy JSON validated")

    strategy = load_strategy("src/config/strategy.json")
    print("✅ Strategy loaded")

    df = pd.DataFrame({
        "open": [100, 101, 102, 103, 104, 105, 106, 107, 108, 109],
        "high": [102, 103, 104, 105, 106, 107, 108, 109, 110, 111],
        "low": [99, 100, 101, 102, 103, 104, 105, 106, 107, 108],
        "close": [101, 102, 103, 104, 105, 106, 107, 108, 109, 110],
        "volume": [1000, 1100, 1200, 1300, 1400, 1500, 1600, 1700, 1800, 1900],
    })

    df = calculate_indicators(df, strategy)
    print("✅ Indicators calculated")

    df = generate_signals(df, strategy)
    print("✅ Signals generated")

    backtest = BacktestEngine(
        strategy=strategy,
        initial_balance=10000,
        stop_loss_pct=1,
        take_profit_pct=2
    )

    result = backtest.run(df, df["SIGNAL"])
    result_dict = result.to_dict()
    print("✅ Backtest completed")

    optimizer = OptimizerEngine(strategy)
    optimizer_results = optimizer.optimize(
        df=df,
        sl_values=[1],
        tp_values=[2]
    )
    print("✅ Optimizer completed")

    print("\n----------------------------------------")
    print("SYSTEM RESULT")
    print("----------------------------------------")
    print(f"Initial Balance : {result_dict['initial_balance']}")
    print(f"Final Balance   : {result_dict['final_balance']}")
    print(f"Net Profit      : {result_dict['net_profit']}")
    print(f"ROI %           : {result_dict['roi_pct']}")
    print(f"Trades          : {result_dict['total_trades']}")
    print(f"Optimizer Rows  : {len(optimizer_results)}")

    print("\n✅ ALL SYSTEM TESTS PASSED")


if __name__ == "__main__":
    test_system()