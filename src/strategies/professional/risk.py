def calculate_position_notional(
    equity: float,
    risk_per_trade_pct: float,
    entry_price: float,
    stop_price: float,
    maximum_notional_fraction: float = 1.0,
) -> float:
    values = [equity, risk_per_trade_pct, entry_price, maximum_notional_fraction]
    if any(value <= 0 for value in values) or stop_price >= entry_price or stop_price < 0:
        raise ValueError("invalid long-only position sizing inputs")
    risk_amount = equity * risk_per_trade_pct / 100.0
    stop_fraction = (entry_price - stop_price) / entry_price
    raw_notional = risk_amount / stop_fraction
    return min(raw_notional, equity * maximum_notional_fraction)


def cooldown_allows_entry(
    current_bar: int,
    last_exit_bar: int | None,
    cooldown_bars: int,
) -> bool:
    if cooldown_bars < 0 or current_bar < 0:
        raise ValueError("bar indexes and cooldown must be non-negative")
    return last_exit_bar is None or current_bar - last_exit_bar >= cooldown_bars


def drawdown_risk_multiplier(drawdown_pct: float) -> float:
    drawdown = abs(float(drawdown_pct))
    if drawdown >= 10.0:
        return 0.0
    if drawdown >= 6.0:
        return 0.5
    return 1.0
