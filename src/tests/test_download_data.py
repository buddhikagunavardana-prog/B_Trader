from plugins.binance_data import download_klines

df = download_klines(
    symbol="BTCUSDT",
    interval="1h",
    start_str="1 year ago UTC"
)

print("=" * 50)
print("First 5 Candles")
print("=" * 50)
print(df.head())

print()

print("=" * 50)
print("Last 5 Candles")
print("=" * 50)
print(df.tail())

print()

print("=" * 50)
print("Total Candles:", len(df))
print("=" * 50)