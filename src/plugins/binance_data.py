from binance.client import Client


def get_live_price(symbol: str) -> float:
    client = Client()
    ticker = client.get_symbol_ticker(symbol=symbol)
    return float(ticker["price"])