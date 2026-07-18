from src.strategies.strategy_loader import load_strategy


def main():
    strategy = load_strategy()

    print("Strategy loaded successfully")
    print(f"Strategy: {strategy.name} v{strategy.version}")
    print(f"Exchange: {strategy.exchange}")
    print(f"Market Type: {strategy.market_type}")
    print(f"Symbols: {', '.join(strategy.symbols)}")
    print(f"Timeframe: {strategy.timeframe}")
    print(f"Minimum Score: {strategy.signal_scoring['minimum_score']}")


if __name__ == "__main__":
    main()
