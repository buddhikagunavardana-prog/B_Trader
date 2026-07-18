from src.engines.backtest_engine import BacktestEngine
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

engine = BacktestEngine(strategy)

result = engine.run(df, df["SIGNAL"])

print("\n===== BACKTEST RESULT =====")
print(f"Total Trades  : {result.total_trades}")
print(f"Wins          : {result.wins}")
print(f"Losses        : {result.losses}")
print(f"Win Rate      : {result.win_rate}%")
print(f"Total PnL     : {result.total_pnl_pct}%")
print(f"Avg Win       : {result.avg_win}")
print(f"Avg Loss      : {result.avg_loss}")
print(f"Profit Factor : {result.profit_factor}")
