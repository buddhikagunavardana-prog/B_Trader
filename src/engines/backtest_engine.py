from src.models.backtest_result import BacktestResult


class BacktestEngine:
    def __init__(
        self,
        strategy,
        initial_balance=10000,
        stop_loss_pct=None,
        take_profit_pct=None,
        fee_pct=0.0
    ):
        self.strategy = strategy
        self.initial_balance = float(initial_balance)
        self.balance = float(initial_balance)

        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
        self.fee_pct = float(fee_pct)

        self.trades = []
        self.equity_curve = []

    def _get_strategy_exit_value(self, value_type):
        possible_keys_map = {
            "stop_loss": [
                "stop_loss_pct",
                "stop_loss_percent",
                "stop_loss",
                "sl_pct",
                "sl_percent",
                "sl"
            ],
            "take_profit": [
                "take_profit_pct",
                "take_profit_percent",
                "take_profit",
                "tp_pct",
                "tp_percent",
                "tp"
            ]
        }

        possible_keys = possible_keys_map[value_type]

        if isinstance(self.strategy, dict):
            exit_rules = self.strategy.get("exit_rules", {})
        else:
            exit_rules = getattr(self.strategy, "exit_rules", {})

        if isinstance(exit_rules, dict):
            for key in possible_keys:
                if key in exit_rules:
                    return float(exit_rules[key])
        else:
            for key in possible_keys:
                if hasattr(exit_rules, key):
                    return float(getattr(exit_rules, key))

        return None

    def _resolve_stop_loss_pct(self):
        if self.stop_loss_pct is not None:
            return float(self.stop_loss_pct)

        value = self._get_strategy_exit_value("stop_loss")
        if value is not None:
            return value

        return 2.0

    def _resolve_take_profit_pct(self):
        if self.take_profit_pct is not None:
            return float(self.take_profit_pct)

        value = self._get_strategy_exit_value("take_profit")
        if value is not None:
            return value

        return 4.0

    def _calculate_fee(self, amount):
        return amount * (self.fee_pct / 100)

    def run(self, df, signals):
        self.balance = self.initial_balance
        self.trades = []
        self.equity_curve = []

        position = None

        stop_loss_pct = self._resolve_stop_loss_pct() / 100
        take_profit_pct = self._resolve_take_profit_pct() / 100

        for i in range(len(df)):
            candle = df.iloc[i]
            signal = signals.iloc[i]
            current_price = float(candle["close"])

            self.equity_curve.append({
                "time": candle.name,
                "balance": round(self.balance, 2)
            })

            if position is None and signal == "BUY":
                entry_price = current_price
                buy_fee = self._calculate_fee(self.balance)

                self.balance -= buy_fee

                position = {
                    "entry_index": i,
                    "entry_time": candle.name,
                    "entry_price": entry_price,
                    "stop_loss": entry_price * (1 - stop_loss_pct),
                    "take_profit": entry_price * (1 + take_profit_pct),
                    "balance_before": self.balance + buy_fee,
                    "buy_fee": buy_fee
                }

            elif position is not None:
                low_price = float(candle["low"])
                high_price = float(candle["high"])

                exit_price = None
                result = None

                if low_price <= position["stop_loss"]:
                    exit_price = position["stop_loss"]
                    result = "LOSS"

                elif high_price >= position["take_profit"]:
                    exit_price = position["take_profit"]
                    result = "WIN"

                if exit_price is not None:
                    entry_price = position["entry_price"]

                    gross_pnl_pct = ((exit_price - entry_price) / entry_price) * 100
                    gross_pnl_amount = self.balance * (gross_pnl_pct / 100)

                    balance_after_gross_pnl = self.balance + gross_pnl_amount
                    sell_fee = self._calculate_fee(balance_after_gross_pnl)

                    net_pnl_amount = gross_pnl_amount - sell_fee
                    self.balance = balance_after_gross_pnl - sell_fee

                    total_trade_fee = position["buy_fee"] + sell_fee

                    trade = {
                        "entry_time": position["entry_time"],
                        "exit_time": candle.name,
                        "entry_price": round(entry_price, 6),
                        "exit_price": round(exit_price, 6),
                        "result": result,
                        "gross_pnl_pct": round(gross_pnl_pct, 2),
                        "pnl_pct": round(gross_pnl_pct, 2),
                        "gross_pnl_amount": round(gross_pnl_amount, 2),
                        "pnl_amount": round(net_pnl_amount, 2),
                        "buy_fee": round(position["buy_fee"], 2),
                        "sell_fee": round(sell_fee, 2),
                        "total_fee": round(total_trade_fee, 2),
                        "balance_before": round(position["balance_before"], 2),
                        "balance_after": round(self.balance, 2)
                    }

                    self.trades.append(trade)
                    position = None

        return self.get_results()

    def get_results(self):
        total_trades = len(self.trades)
        wins = len([t for t in self.trades if t["result"] == "WIN"])
        losses = len([t for t in self.trades if t["result"] == "LOSS"])

        win_rate = (wins / total_trades) * 100 if total_trades > 0 else 0

        gross_profit = sum(t["pnl_amount"] for t in self.trades if t["pnl_amount"] > 0)
        gross_loss = abs(sum(t["pnl_amount"] for t in self.trades if t["pnl_amount"] < 0))

        net_profit = self.balance - self.initial_balance
        roi_pct = (net_profit / self.initial_balance) * 100

        total_pnl_pct = sum(t["pnl_pct"] for t in self.trades)
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0

        total_fees = sum(t["total_fee"] for t in self.trades)

        win_amounts = [t["pnl_amount"] for t in self.trades if t["pnl_amount"] > 0]
        loss_amounts = [t["pnl_amount"] for t in self.trades if t["pnl_amount"] < 0]

        avg_win = sum(win_amounts) / len(win_amounts) if len(win_amounts) > 0 else 0
        avg_loss = sum(loss_amounts) / len(loss_amounts) if len(loss_amounts) > 0 else 0

        largest_win = max(win_amounts) if len(win_amounts) > 0 else 0
        largest_loss = min(loss_amounts) if len(loss_amounts) > 0 else 0

        expectancy = (
            (win_rate / 100) * avg_win
            +
            ((100 - win_rate) / 100) * avg_loss
        ) if total_trades > 0 else 0

        return BacktestResult(
            initial_balance=self.initial_balance,
            final_balance=self.balance,
            gross_profit=gross_profit,
            gross_loss=gross_loss,
            net_profit=net_profit,
            roi_pct=roi_pct,
            total_trades=total_trades,
            wins=wins,
            losses=losses,
            win_rate=win_rate,
            total_pnl_pct=total_pnl_pct,
            profit_factor=profit_factor,
            total_fees=total_fees,
            avg_win=avg_win,
            avg_loss=avg_loss,
            largest_win=largest_win,
            largest_loss=largest_loss,
            expectancy=expectancy,
            trades=self.trades,
            equity_curve=self.equity_curve
        )