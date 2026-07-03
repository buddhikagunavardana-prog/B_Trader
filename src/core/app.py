from utils.banner import show_banner
from utils.system import show_system_info
from plugins.binance_data import get_live_price, download_klines
from indicators.ema import calculate_ema
from indicators.rsi import calculate_rsi
from indicators.macd import calculate_macd
from strategies.signal import generate_signal
import os



def start():
    show_banner()

    print("Status : System Ready")
    print("Mode   : Development")
    print()
    show_system_info()

    print()
    print("Connecting to Binance...")

    btc_price = get_live_price("BTCUSDT")
    eth_price = get_live_price("ETHUSDT")

    print(f"BTCUSDT : {btc_price}")
    print(f"ETHUSDT : {eth_price}")
    print("Binance Connection Successful")

    print()
    print("Downloading BTCUSDT 1H candles for 1 year...")

    df = download_klines("BTCUSDT", "1h", "1 year ago UTC")

    os.makedirs("data/BTCUSDT", exist_ok=True)
    df.to_csv("data/BTCUSDT/1h.csv", index=False)

    print(f"Saved candles: {len(df)}")
    print("File saved: data/BTCUSDT/1h.csv")

    print()
    print("Calculating EMA...")

    df["EMA20"] = calculate_ema(df, 20)
    df["EMA50"] = calculate_ema(df, 50)
    df["EMA200"] = calculate_ema(df, 200)

    print("EMA20 :", round(df["EMA20"].iloc[-1], 2))
    print("EMA50 :", round(df["EMA50"].iloc[-1], 2))
    print("EMA200:", round(df["EMA200"].iloc[-1], 2))

    print()
    print("Calculating RSI...")

    df["RSI14"] = calculate_rsi(df, 14)

    print("RSI14 :", round(df["RSI14"].iloc[-1], 2))

    print()
    print("Calculating MACD...")

    df["MACD"], df["MACD_SIGNAL"], df["MACD_HIST"] = calculate_macd(df)

    print("MACD       :", round(df["MACD"].iloc[-1], 2))
    print("Signal     :", round(df["MACD_SIGNAL"].iloc[-1], 2))
    print("Histogram  :", round(df["MACD_HIST"].iloc[-1], 2))

    print("Signal Analysis...")

    signal = generate_signal(
    df["EMA20"].iloc[-1],
    df["EMA50"].iloc[-1],
    df["RSI14"].iloc[-1],
    df["MACD"].iloc[-1],
    df["MACD_SIGNAL"].iloc[-1]
)

    print()
    print("Signal Analysis")
    print("----------------")
    print("Signal :", signal)