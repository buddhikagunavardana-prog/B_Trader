from dataclasses import dataclass, field


@dataclass(frozen=True)
class ConstraintResult:
    is_valid: bool
    reasons: list[str] = field(default_factory=list)


def _positive(parameters: dict, key: str, reasons: list[str]) -> None:
    if key in parameters and float(parameters[key]) <= 0:
        reasons.append(f"{key} must be greater than 0")


def validate_optimizer_parameters(parameters: dict) -> ConstraintResult:
    reasons = []

    fast_ema = parameters.get("fast_ema")
    slow_ema = parameters.get("slow_ema")
    trend_ema = parameters.get("trend_ema")
    if fast_ema is not None and slow_ema is not None:
        if int(fast_ema) >= int(slow_ema):
            reasons.append("EMA fast must be lower than slow")

    if slow_ema is not None and trend_ema is not None:
        if int(slow_ema) >= int(trend_ema):
            reasons.append("EMA slow must be lower than trend")

    rsi_buy = parameters.get("rsi_buy")
    rsi_sell = parameters.get("rsi_sell")
    if rsi_buy is not None and rsi_sell is not None:
        if float(rsi_buy) <= float(rsi_sell):
            reasons.append("RSI buy must be greater than sell")

    macd_fast = parameters.get("macd_fast")
    macd_slow = parameters.get("macd_slow")
    if macd_fast is not None and macd_slow is not None:
        if int(macd_fast) >= int(macd_slow):
            reasons.append("MACD fast must be lower than slow")

    for key in [
        "atr_multiplier",
        "supertrend_multiplier",
        "volume_multiplier",
        "bollinger_std",
        "stop_loss_pct",
        "take_profit_pct",
    ]:
        _positive(parameters, key, reasons)

    for key, value in parameters.items():
        if key.endswith("_period") and int(value) <= 0:
            reasons.append(f"{key} must be greater than 0")

    return ConstraintResult(is_valid=not reasons, reasons=reasons)
