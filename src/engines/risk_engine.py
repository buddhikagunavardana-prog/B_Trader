def calculate_risk_levels(entry_price, atr, signal):
    if signal == "BUY":
        stop_loss = entry_price - (atr * 2)
        take_profit = entry_price + (atr * 4)

    elif signal == "SELL":
        stop_loss = entry_price + (atr * 2)
        take_profit = entry_price - (atr * 4)

    else:
        stop_loss = None
        take_profit = None

    return stop_loss, take_profit