from plugins.binance_data import download_klines
from strategies.strategy_loader import load_strategy
from engines.indicator_engine import calculate_indicators
from engines.signal_engine import generate_signals
from engines.backtest_engine import BacktestEngine


strategy = load_strategy()

df = download_klines(
    symbol="BTCUSDT",
    interval=strategy.timeframe,
    start_str="1 year ago UTC"
)

df = calculate_indicators(df, strategy)
df = generate_signals(df, strategy)

engine = BacktestEngine(strategy)

result = engine.run(df, df["SIGNAL"])

print("\n===== BACKTEST RESULT =====")
print(f"Total Trades  : {result['total_trades']}")
print(f"Wins          : {result['wins']}")
print(f"Losses        : {result['losses']}")
print(f"Win Rate      : {result['win_rate']}%")
print(f"Total PnL     : {result['total_pnl_percent']}%")
print(f"Avg Win       : {result['average_win_percent']}%")
print(f"Avg Loss      : {result['average_loss_percent']}%")
print(f"Profit Factor : {result['profit_factor']}")