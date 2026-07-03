from utils.banner import show_banner
from utils.system import show_system_info
from plugins.binance_data import get_live_price
from config.watchlist import TOP_15_USDT_PAIRS

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
    print("Top 15 Watchlist:")

    for pair in TOP_15_USDT_PAIRS:
        print(f"- {pair}")