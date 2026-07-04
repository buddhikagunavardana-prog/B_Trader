class BacktestEngine:
    def __init__(self, strategy, initial_balance=10000):
        self.strategy = strategy
        self.balance = initial_balance
        self.trades = []

    def run(self, df, signals):
        position = None

        for i in range(len(df)):
            candle = df.iloc[i]
            signal = signals.iloc[i]

            if position is None and signal == "BUY":
                entry_price = candle["close"]

                exit_rules = self.strategy.exit_rules
                sl_percent = exit_rules.get("stop_loss_percent", 2)
                tp_percent = exit_rules.get("take_profit_percent", 4)

                position = {
                    "entry_price": entry_price,
                    "stop_loss": entry_price * (1 - sl_percent / 100),
                    "take_profit": entry_price * (1 + tp_percent / 100),
                    "entry_index": i
                }

            elif position is not None:
                if candle["low"] <= position["stop_loss"]:
                    self.close_trade(position, position["stop_loss"], "LOSS")
                    position = None

                elif candle["high"] >= position["take_profit"]:
                    self.close_trade(position, position["take_profit"], "WIN")
                    position = None

        return self.summary()

    def close_trade(self, position, exit_price, result):
        entry_price = position["entry_price"]

        pnl_percent = ((exit_price - entry_price) / entry_price) * 100

        self.trades.append({
            "result": result,
            "entry": entry_price,
            "exit": exit_price,
            "pnl_percent": pnl_percent
        })

    def summary(self):
        total = len(self.trades)
        wins = [t for t in self.trades if t["result"] == "WIN"]
        losses = [t for t in self.trades if t["result"] == "LOSS"]

        total_pnl = sum(t["pnl_percent"] for t in self.trades)
        gross_profit = sum(t["pnl_percent"] for t in wins)
        gross_loss = abs(sum(t["pnl_percent"] for t in losses))

        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0

        return {
            "total_trades": total,
            "wins": len(wins),
            "losses": len(losses),
            "win_rate": round((len(wins) / total) * 100, 2) if total else 0,
            "total_pnl_percent": round(total_pnl, 2),
            "average_win_percent": round(gross_profit / len(wins), 2) if wins else 0,
            "average_loss_percent": round(gross_loss / len(losses), 2) if losses else 0,
            "profit_factor": round(profit_factor, 2),
            "trades": self.trades
        }