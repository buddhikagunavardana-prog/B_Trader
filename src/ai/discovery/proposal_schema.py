import math
import re


class ProposalValidationError(ValueError):
    pass


PROPOSAL_FIELDS = {
    "proposal_version", "proposal_id", "title", "hypothesis",
    "strategy_family", "market_scope", "entry_timeframe",
    "confirmation_timeframes", "entry_conditions",
    "confirmation_conditions", "exit_mode", "risk_mode",
    "parameter_ranges", "expected_market_regimes", "expected_benefit",
    "known_risks", "overfitting_risk", "validation_plan", "do_not_change",
}
CONDITION_FIELDS = {"indicator", "parameters", "operator"}
OPERATORS = {
    "EMA": {"cross_above"},
    "RSI": {"above"},
    "MACD": {"above_signal"},
    "VOLUME": {"above_multiplier"},
    "BOLLINGER": {"close_above_lower"},
    "SUPERTREND": {"buy"},
    "CANDLESTICK": {"bullish_pattern"},
}
PARAMETER_LIMITS = {
    "EMA": {"fast": (2, 300), "slow": (3, 400)},
    "RSI": {"period": (2, 100), "buy": (1, 99)},
    "MACD": {"fast": (2, 100), "slow": (3, 200), "signal": (2, 100)},
    "VOLUME": {"period": (20, 20), "multiplier": (0.5, 5)},
    "BOLLINGER": {"period": (2, 200), "std_dev": (0.5, 5)},
    "SUPERTREND": {"period": (2, 100), "multiplier": (0.5, 10)},
    "CANDLESTICK": {},
}
RANGE_KEYS = {
    "ema.fast", "ema.slow", "rsi.period", "rsi.buy", "macd.fast",
    "macd.slow", "macd.signal", "volume.multiplier", "bollinger.period",
    "bollinger.std_dev", "supertrend.period", "supertrend.multiplier",
    "stop_loss_pct", "take_profit_pct", "atr_period",
    "atr_stop_multiplier", "atr_target_multiplier",
}
RANGE_LIMITS = {
    "ema.fast": (2, 300), "ema.slow": (3, 400),
    "rsi.period": (2, 100), "rsi.buy": (1, 99),
    "macd.fast": (2, 100), "macd.slow": (3, 200),
    "macd.signal": (2, 100), "volume.multiplier": (0.5, 5),
    "bollinger.period": (2, 200), "bollinger.std_dev": (0.5, 5),
    "supertrend.period": (2, 100), "supertrend.multiplier": (0.5, 10),
    "stop_loss_pct": (0.1, 10), "take_profit_pct": (0.1, 20),
    "atr_period": (2, 100), "atr_stop_multiplier": (0.1, 10),
    "atr_target_multiplier": (0.1, 20),
}
INTEGER_RANGES = {
    "ema.fast", "ema.slow", "rsi.period", "macd.fast", "macd.slow",
    "macd.signal", "bollinger.period", "supertrend.period", "atr_period",
}
FORBIDDEN_TEXT = {
    "future data", "next candle", "look ahead", "look-ahead",
    "final validation result", "holdout result", "relax threshold",
    "lower threshold", "execute trade", "place order", "production activation",
}


def _exact_fields(payload: dict, fields: set[str], label: str) -> None:
    if not isinstance(payload, dict):
        raise ProposalValidationError(f"{label} must be an object")
    missing = fields.difference(payload)
    extra = set(payload).difference(fields)
    if missing or extra:
        raise ProposalValidationError(
            f"{label} fields invalid; missing={sorted(missing)}, extra={sorted(extra)}"
        )


def _string_list(value, label: str) -> None:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise ProposalValidationError(f"{label} must be a list of strings")


def _validate_text(values: list[str]) -> None:
    combined = " ".join(values).lower()
    if any(term in combined for term in FORBIDDEN_TEXT):
        raise ProposalValidationError("Proposal contains forbidden data or authority")
    if any(re.search(r"(?<![A-Za-z])[-+]?\d+(?:\.\d+)?%", value) for value in values):
        raise ProposalValidationError("Proposal contains unsupported numerical claims")


def _validate_condition(condition: dict, allowed_indicators: set[str]) -> None:
    _exact_fields(condition, CONDITION_FIELDS, "condition")
    indicator = str(condition["indicator"]).upper()
    if indicator not in allowed_indicators or indicator not in OPERATORS:
        raise ProposalValidationError(f"Unsupported indicator: {indicator}")
    if condition["operator"] not in OPERATORS[indicator]:
        raise ProposalValidationError(
            f"Unsupported operator for {indicator}: {condition['operator']}"
        )
    parameters = condition["parameters"]
    if not isinstance(parameters, dict):
        raise ProposalValidationError("Condition parameters must be an object")
    limits = PARAMETER_LIMITS[indicator]
    if set(parameters) != set(limits):
        raise ProposalValidationError(
            f"Invalid {indicator} parameter fields: {sorted(parameters)}"
        )
    for key, value in parameters.items():
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ProposalValidationError(f"{indicator}.{key} must be numeric")
        minimum, maximum = limits[key]
        if not math.isfinite(float(value)) or not minimum <= float(value) <= maximum:
            raise ProposalValidationError(f"{indicator}.{key} is out of range")
    if indicator in {"EMA", "MACD"} and parameters["fast"] >= parameters["slow"]:
        raise ProposalValidationError(f"{indicator} fast must be below slow")


def estimate_search_space(parameter_ranges: dict) -> int:
    count = 1
    for values in parameter_ranges.values():
        count *= len(values)
    return count


def validate_strategy_proposal(proposal: dict, config: dict) -> dict:
    _exact_fields(proposal, PROPOSAL_FIELDS, "proposal")
    if proposal["proposal_version"] != "1.0":
        raise ProposalValidationError("proposal_version must be 1.0")
    for field in ["proposal_id", "title", "hypothesis", "strategy_family",
                  "expected_benefit", "overfitting_risk"]:
        if not isinstance(proposal[field], str) or not proposal[field]:
            raise ProposalValidationError(f"{field} must be a non-empty string")
    if not re.fullmatch(r"[A-Z0-9_]{8,80}", proposal["proposal_id"]):
        raise ProposalValidationError("proposal_id must be a stable uppercase identifier")
    for field in ["market_scope", "confirmation_timeframes",
                  "expected_market_regimes", "known_risks",
                  "validation_plan", "do_not_change"]:
        _string_list(proposal[field], field)
    markets = set(config["allowed_market_scope"])
    if not proposal["market_scope"] or not set(proposal["market_scope"]).issubset(markets):
        raise ProposalValidationError("Proposal market scope is unsupported")
    timeframes = set(config["allowed_timeframes"])
    if proposal["entry_timeframe"] not in timeframes:
        raise ProposalValidationError("Entry timeframe is unsupported")
    if not set(proposal["confirmation_timeframes"]).issubset(timeframes):
        raise ProposalValidationError("Confirmation timeframe is unsupported")
    if proposal["confirmation_timeframes"] and not config["allow_multi_timeframe_confirmation"]:
        raise ProposalValidationError("Multi-timeframe confirmation is disabled")
    if not isinstance(proposal["entry_conditions"], list) or not isinstance(
        proposal["confirmation_conditions"], list
    ):
        raise ProposalValidationError("Strategy conditions must be lists")
    conditions = proposal["entry_conditions"] + proposal["confirmation_conditions"]
    if not proposal["entry_conditions"] or not all(isinstance(item, dict) for item in conditions):
        raise ProposalValidationError("Proposal requires valid entry conditions")
    unique_indicators = {str(item.get("indicator", "")).upper() for item in conditions}
    if len(unique_indicators) > int(config["max_indicators_per_strategy"]):
        raise ProposalValidationError("Proposal exceeds indicator complexity limit")
    allowed = {item.upper() for item in config["allowed_indicators"]}
    for condition in conditions:
        _validate_condition(condition, allowed)
    if proposal["exit_mode"] not in {"fixed", "atr"}:
        raise ProposalValidationError("Unsupported exit_mode")
    if proposal["risk_mode"] not in {"full_allocation", "risk_normalized"}:
        raise ProposalValidationError("Unsupported risk_mode")
    ranges = proposal["parameter_ranges"]
    if not isinstance(ranges, dict) or not ranges:
        raise ProposalValidationError("parameter_ranges must be a non-empty object")
    if not set(ranges).issubset(RANGE_KEYS):
        raise ProposalValidationError("Proposal contains unsupported parameter range")
    for key, values in ranges.items():
        if not isinstance(values, list) or not values or len(values) != len(set(values)):
            raise ProposalValidationError(f"Invalid parameter range: {key}")
        if any(isinstance(value, bool) or not isinstance(value, (int, float))
               or not math.isfinite(float(value)) for value in values):
            raise ProposalValidationError(f"Non-numeric parameter range: {key}")
        minimum, maximum = RANGE_LIMITS[key]
        if any(not minimum <= float(value) <= maximum for value in values):
            raise ProposalValidationError(f"Parameter range is out of bounds: {key}")
        if key in INTEGER_RANGES and any(float(value) != int(value) for value in values):
            raise ProposalValidationError(f"Parameter range must use integers: {key}")
    if proposal["exit_mode"] == "fixed":
        required_exit = {"stop_loss_pct", "take_profit_pct"}
    else:
        required_exit = {
            "atr_period", "atr_stop_multiplier", "atr_target_multiplier"
        }
    if not required_exit.issubset(ranges):
        raise ProposalValidationError("Required exit parameter ranges are missing")
    for fast, slow in [("ema.fast", "ema.slow"), ("macd.fast", "macd.slow")]:
        if fast in ranges and slow in ranges and max(ranges[fast]) >= min(ranges[slow]):
            raise ProposalValidationError(f"Impossible parameter relationship: {fast} >= {slow}")
    search_space = estimate_search_space(ranges)
    if search_space > int(config["max_parameter_combinations_per_proposal"]):
        raise ProposalValidationError("Proposal search space exceeds configured limit")
    text = [proposal["title"], proposal["hypothesis"], proposal["expected_benefit"],
            proposal["overfitting_risk"], *proposal["known_risks"],
            *proposal["validation_plan"], *proposal["do_not_change"]]
    _validate_text(text)
    return dict(proposal)
