class RuleEngine:
    """
    B Trader Rule Engine v1

    Uses current strategy.json format:
    - indicators
    - entry_rules
    - exit_rules

    Expected data keys:
    close, EMA_FAST, EMA_SLOW, EMA_TREND, RSI, MACD, MACD_SIGNAL
    """

    def __init__(self, strategy):
        self.strategy = strategy

    def _get_config(self, key, default=None):
        if isinstance(self.strategy, dict):
            return self.strategy.get(key, default)

        return getattr(self.strategy, key, default)

    def _is_enabled(self, rule_name):
        entry_rules = self._get_config("entry_rules", {})
        return entry_rules.get(rule_name, False)

    def generate_signal(self, data):
        """
        Returns BUY or HOLD.
        SELL/exit will be handled by backtest exit rules.
        """

        if self._is_enabled("ema_cross"):
            if data.get("EMA_FAST") is None or data.get("EMA_SLOW") is None:
                return "HOLD"

            if data["EMA_FAST"] <= data["EMA_SLOW"]:
                return "HOLD"

        if self._is_enabled("ema200_filter"):
            if data.get("close") is None or data.get("EMA_TREND") is None:
                return "HOLD"

            if data["close"] <= data["EMA_TREND"]:
                return "HOLD"

        if self._is_enabled("rsi_filter"):
            indicators = self._get_config("indicators", {})
            rsi_config = indicators.get("rsi", {})
            buy_level = rsi_config.get("buy", 55)

            if data.get("RSI") is None:
                return "HOLD"

            if data["RSI"] < buy_level:
                return "HOLD"

        if self._is_enabled("macd_confirmation"):
            if data.get("MACD") is None or data.get("MACD_SIGNAL") is None:
                return "HOLD"

            if data["MACD"] <= data["MACD_SIGNAL"]:
                return "HOLD"

        return "BUY"

    def evaluate(self, data):
        return self.generate_signal(data)