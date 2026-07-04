VALID_TIMEFRAMES = ["15m", "1h", "4h", "1d"]


def validate_strategy(data: dict) -> None:
    required_fields = [
        "name",
        "version",
        "exchange",
        "market_type",
        "quote_asset",
        "symbols",
        "timeframe",
        "indicators",
        "entry_rules",
        "exit_rules",
        "risk",
        "signal_scoring",
    ]

    for field in required_fields:
        if field not in data:
            raise ValueError(f"Missing required field: {field}")

    if data["timeframe"] not in VALID_TIMEFRAMES:
        raise ValueError(f"Invalid timeframe: {data['timeframe']}")

    if not isinstance(data["symbols"], list) or len(data["symbols"]) == 0:
        raise ValueError("symbols must be a non-empty list")

    risk_per_trade = data["risk"].get("risk_per_trade")
    if risk_per_trade <= 0 or risk_per_trade > 5:
        raise ValueError("risk_per_trade must be between 0 and 5")

    minimum_score = data["signal_scoring"].get("minimum_score")
    if minimum_score < 0 or minimum_score > 100:
        raise ValueError("minimum_score must be between 0 and 100")