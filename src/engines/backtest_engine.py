import math

from src.models.backtest_result import BacktestResult


class BacktestEngine:
    def __init__(
        self,
        strategy,
        initial_balance=10000,
        stop_loss_pct=None,
        take_profit_pct=None,
        fee_pct=0.0,
        position_size_percent=100
    ):
        self.strategy = strategy
        self.initial_balance = float(initial_balance)
        self.balance = float(initial_balance)

        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
        self.fee_pct = float(fee_pct)
        self.position_size_percent = float(position_size_percent)

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

    def _get_exit_rules(self):
        if isinstance(self.strategy, dict):
            return self.strategy.get("exit_rules", {})
        return getattr(self.strategy, "exit_rules", {})

    def _get_exit_rule(self, key, default=None):
        rules = self._get_exit_rules()
        if isinstance(rules, dict):
            return rules.get(key, default)
        return getattr(rules, key, default)

    def _atr_exit_settings(self):
        if self._get_exit_rule("simulated_exit_mode") != "atr_full_position":
            return None
        settings = {
            "period": int(self._get_exit_rule("atr_period")),
            "stop_multiplier": float(
                self._get_exit_rule("atr_stop_multiplier")
            ),
            "target_multiplier": float(
                self._get_exit_rule("atr_target_multiplier")
            ),
            "min_stop_percent": self._get_exit_rule("min_stop_percent"),
            "max_stop_percent": self._get_exit_rule("max_stop_percent"),
        }
        if settings["period"] <= 0:
            raise ValueError("ATR period must be positive")
        if settings["stop_multiplier"] <= 0:
            raise ValueError("ATR stop multiplier must be positive")
        if settings["target_multiplier"] <= 0:
            raise ValueError("ATR target multiplier must be positive")
        for key in ("min_stop_percent", "max_stop_percent"):
            if settings[key] is not None:
                settings[key] = float(settings[key])
                if settings[key] <= 0:
                    raise ValueError(f"{key} must be positive")
        if (
            settings["min_stop_percent"] is not None
            and settings["max_stop_percent"] is not None
            and settings["min_stop_percent"] > settings["max_stop_percent"]
        ):
            raise ValueError(
                "min_stop_percent cannot exceed max_stop_percent"
            )
        return settings

    def _atr_exit_prices(self, entry_price, atr_value, settings):
        if not math.isfinite(atr_value) or atr_value <= 0:
            return None
        stop_distance = atr_value * settings["stop_multiplier"]
        minimum = settings["min_stop_percent"]
        maximum = settings["max_stop_percent"]
        if minimum is not None:
            stop_distance = max(stop_distance, entry_price * minimum / 100)
        if maximum is not None:
            stop_distance = min(stop_distance, entry_price * maximum / 100)
        # Apply the target to the effective (possibly clamped) ATR distance so
        # clamps cannot silently distort the predeclared reward-to-risk ratio.
        target_distance = (
            stop_distance
            / settings["stop_multiplier"]
            * settings["target_multiplier"]
        )
        if stop_distance <= 0 or target_distance <= 0:
            return None
        return {
            "stop_loss": entry_price - stop_distance,
            "take_profit": entry_price + target_distance,
            "atr_value": atr_value,
            "stop_distance": stop_distance,
            "target_distance": target_distance,
        }

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

    def _record_equity(self, time):
        self.equity_curve.append({
            "time": time,
            "balance": round(self.balance, 2)
        })

    def _calculate_max_drawdown_pct(self):
        if not self.equity_curve:
            return 0.0

        peak = self.equity_curve[0]["balance"]
        max_drawdown = 0.0

        for point in self.equity_curve:
            balance = point["balance"]

            if balance > peak:
                peak = balance

            if peak > 0:
                drawdown = ((balance - peak) / peak) * 100

                if drawdown < max_drawdown:
                    max_drawdown = drawdown

        return max_drawdown

    def run(self, df, signals):
        self.balance = self.initial_balance
        self.trades = []
        self.equity_curve = []

        position = None

        stop_loss_pct = self._resolve_stop_loss_pct() / 100
        take_profit_pct = self._resolve_take_profit_pct() / 100
        atr_settings = self._atr_exit_settings()

        # Read-only column/index views avoid constructing two pandas Series for
        # every candle.  The loop order and all trading calculations remain the
        # same; only the access path to the existing values changes.
        index = df.index
        close_values = df["close"].to_numpy(copy=False)
        low_values = df["low"].to_numpy(copy=False)
        high_values = df["high"].to_numpy(copy=False)
        signal_values = signals.to_numpy(copy=False)
        atr_values = None
        if atr_settings is not None:
            atr_column = f"ATR{atr_settings['period']}"
            if atr_column not in df.columns:
                raise ValueError(
                    f"ATR exit mode requires market data column {atr_column}"
                )
            atr_values = df[atr_column].to_numpy(copy=False)

        for i in range(len(df)):
            candle_time = index[i]
            signal = signal_values[i]
            current_price = float(close_values[i])

            self._record_equity(candle_time)

            if position is None and signal == "BUY":
                entry_price = current_price

                atr_prices = None
                if atr_settings is not None:
                    # Signals execute at the current close. The previous row is
                    # the latest fully completed candle available before entry.
                    if i == 0:
                        continue
                    atr_prices = self._atr_exit_prices(
                        entry_price,
                        float(atr_values[i - 1]),
                        atr_settings,
                    )
                    if atr_prices is None:
                        continue

                trade_capital = self.balance * (self.position_size_percent / 100)
                buy_fee = self._calculate_fee(trade_capital)

                position = {
                    "entry_index": i,
                    "entry_time": candle_time,
                    "entry_price": entry_price,
                    "stop_loss": entry_price * (1 - stop_loss_pct),
                    "take_profit": entry_price * (1 + take_profit_pct),
                    "balance_before": self.balance,
                    "trade_capital": trade_capital,
                    "buy_fee": buy_fee
                }
                if atr_prices is not None:
                    position.update(atr_prices)

            elif position is not None:
                low_price = float(low_values[i])
                high_price = float(high_values[i])

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
                    gross_pnl_amount = position["trade_capital"] * (gross_pnl_pct / 100)

                    exit_value = position["trade_capital"] + gross_pnl_amount
                    sell_fee = self._calculate_fee(exit_value)

                    total_trade_fee = position["buy_fee"] + sell_fee
                    net_pnl_amount = gross_pnl_amount - total_trade_fee

                    self.balance += net_pnl_amount

                    trade = {
                        "trade_id": len(self.trades) + 1,

                        "direction": "LONG",
                        "result": result,
                        "exit_reason": "STOP_LOSS" if result == "LOSS" else "TAKE_PROFIT",

                        "entry_index": position["entry_index"],
                        "exit_index": i,
                        "duration_candles": i - position["entry_index"],

                        "entry_time": position["entry_time"],
                        "exit_time": candle_time,

                        "entry_price": round(entry_price, 6),
                        "exit_price": round(exit_price, 6),
                        "stop_loss": round(position["stop_loss"], 6),
                        "take_profit": round(position["take_profit"], 6),

                        "position_size_percent": round(self.position_size_percent, 2),
                        "trade_capital": round(position["trade_capital"], 2),

                        "gross_pnl_pct": round(gross_pnl_pct, 2),
                        "pnl_pct": round(gross_pnl_pct, 2),

                        "gross_pnl_amount": round(gross_pnl_amount, 2),
                        "pnl_amount": round(net_pnl_amount, 2),

                        "buy_fee": round(position["buy_fee"], 2),
                        "sell_fee": round(sell_fee, 2),
                        "total_fee": round(total_trade_fee, 2),

                        "balance_before": round(position["balance_before"], 2),
                        "balance_after": round(self.balance, 2),
                    }
                    if atr_settings is not None:
                        trade.update({
                            "exit_mode": "atr_full_position",
                            "atr_value": round(position["atr_value"], 6),
                            "stop_distance": round(
                                position["stop_distance"], 6
                            ),
                            "target_distance": round(
                                position["target_distance"], 6
                            ),
                        })

                    self.trades.append(trade)
                    self._record_equity(candle_time)

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

        max_drawdown_pct = self._calculate_max_drawdown_pct()

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
            max_drawdown_pct=max_drawdown_pct,
            avg_win=avg_win,
            avg_loss=avg_loss,
            largest_win=largest_win,
            largest_loss=largest_loss,
            expectancy=expectancy,
            trades=self.trades,
            equity_curve=self.equity_curve
        )
