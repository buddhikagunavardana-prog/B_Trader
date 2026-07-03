from binance.client import Client
import pandas as pd


def get_live_price(symbol: str) -> float:
    client = Client()
    ticker = client.get_symbol_ticker(symbol=symbol)
    return float(ticker["price"])


def download_klines(symbol: str, interval: str, start_str: str):
    client = Client()
    klines = client.get_historical_klines(symbol, interval, start_str)

    columns = [
        "open_time", "open", "high", "low", "close", "volume",
        "close_time", "quote_asset_volume", "number_of_trades",
        "taker_buy_base_volume", "taker_buy_quote_volume", "ignore"
    ]

    df = pd.DataFrame(klines, columns=columns)

    df["open_time"] = pd.to_datetime(df["open_time"], unit="ms")
    df["close_time"] = pd.to_datetime(df["close_time"], unit="ms")

    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = df[col].astype(float)

    return df