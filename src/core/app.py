from src.engines.indicator_engine import calculate_indicators
from src.engines.risk_engine import calculate_risk_levels
from src.plugins.binance_data import download_klines, get_live_price
from src.strategies.signal import generate_signal
from src.utils.banner import show_banner
from src.utils.system import show_system_info

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
    print("Calculating Indicators...")

    df = calculate_indicators(df)

    print("EMA20      :", round(df["EMA20"].iloc[-1], 2))
    print("EMA50      :", round(df["EMA50"].iloc[-1], 2))
    print("EMA200     :", round(df["EMA200"].iloc[-1], 2))
    print("RSI14      :", round(df["RSI14"].iloc[-1], 2))
    print("MACD       :", round(df["MACD"].iloc[-1], 2))
    print("MACD Signal:", round(df["MACD_SIGNAL"].iloc[-1], 2))
    print("Histogram  :", round(df["MACD_HIST"].iloc[-1], 2))
    print("BB Upper   :", round(df["BB_UPPER"].iloc[-1], 2))
    print("BB Middle  :", round(df["BB_MIDDLE"].iloc[-1], 2))
    print("BB Lower   :", round(df["BB_LOWER"].iloc[-1], 2))
    print("ATR14      :", round(df["ATR14"].iloc[-1], 2))
    print("ADX14      :", round(df["ADX14"].iloc[-1], 2))
    print("Volume     :", round(df["volume"].iloc[-1], 2))
    print("Vol SMA20  :", round(df["VOL_SMA20"].iloc[-1], 2))
    print("Support    :", round(df["SUPPORT"].iloc[-1], 2))
    print("Resistance :", round(df["RESISTANCE"].iloc[-1], 2))
    print("Candle     :", df["CANDLE_PATTERN"].iloc[-1])

    signal = generate_signal(
        df["EMA20"].iloc[-1],
        df["EMA50"].iloc[-1],
        df["RSI14"].iloc[-1],
        df["MACD"].iloc[-1],
        df["MACD_SIGNAL"].iloc[-1]
    )

    if df["volume"].iloc[-1] > df["VOL_SMA20"].iloc[-1]:
        print("Volume Confirmation : YES")
    else:
        print("Volume Confirmation : NO")

    print()
    print("Signal Analysis")
    print("----------------")
    print("Signal :", signal)

    entry_price = df["close"].iloc[-1]
    atr = df["ATR14"].iloc[-1]

    stop_loss, take_profit = calculate_risk_levels(entry_price, atr, signal)

    print()
    print("Risk Levels")
    print("-----------")
    print("Entry Price :", round(entry_price, 2))

    print()

    if df["ADX14"].iloc[-1] > 25:
        print("Trend Strength : STRONG")
    else:
        print("Trend Strength : WEAK")

    if signal != "HOLD":
        print("Stop Loss   :", round(stop_loss, 2))
        print("Take Profit :", round(take_profit, 2))
        print("Risk Reward : 1:2")
    else:
        print("No trade setup. Waiting for BUY or SELL signal.")
