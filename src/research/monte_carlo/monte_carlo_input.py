import math
from dataclasses import dataclass, field
from typing import Any


def _validate_numeric_list(values: list[float] | None, field_name: str) -> list[float]:
    if values is None:
        return []

    converted = []
    for value in values:
        number = float(value)
        if not math.isfinite(number):
            raise ValueError(f"{field_name} contains non-finite value")
        converted.append(number)

    return converted


@dataclass(frozen=True)
class MonteCarloInput:
    strategy_id: str
    strategy_name: str
    pair: str
    template_type: str
    initial_balance: float
    trade_returns: list[float] = field(default_factory=list)
    trade_pnls: list[float] = field(default_factory=list)
    fees: list[float] = field(default_factory=list)
    original_metrics: dict[str, Any] = field(default_factory=dict)
    portfolio_weights: dict[str, float] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if float(self.initial_balance) < 0:
            raise ValueError("initial_balance must be non-negative")

        trade_returns = _validate_numeric_list(self.trade_returns, "trade_returns")
        trade_pnls = _validate_numeric_list(self.trade_pnls, "trade_pnls")
        fees = _validate_numeric_list(self.fees, "fees")

        if not trade_returns and not trade_pnls:
            raise ValueError("Monte Carlo input requires trade_returns or trade_pnls")

        reference_length = len(trade_returns) if trade_returns else len(trade_pnls)

        if trade_returns and trade_pnls and len(trade_returns) != len(trade_pnls):
            raise ValueError("trade_returns and trade_pnls lengths must match")

        if fees and len(fees) != reference_length:
            raise ValueError("fees length must match trade series length")

        object.__setattr__(self, "initial_balance", float(self.initial_balance))
        object.__setattr__(self, "trade_returns", trade_returns)
        object.__setattr__(self, "trade_pnls", trade_pnls)
        object.__setattr__(self, "fees", fees)

    @classmethod
    def from_backtest_result(
        cls,
        strategy_id: str,
        strategy_name: str,
        pair: str,
        template_type: str,
        result,
        metadata: dict | None = None,
    ):
        result_dict = result.to_dict() if hasattr(result, "to_dict") else dict(result)
        trades = result_dict.get("trades", [])
        return cls(
            strategy_id=strategy_id,
            strategy_name=strategy_name,
            pair=pair,
            template_type=template_type,
            initial_balance=result_dict["initial_balance"],
            trade_returns=[trade["pnl_pct"] for trade in trades],
            trade_pnls=[trade["pnl_amount"] for trade in trades],
            fees=[trade.get("total_fee", 0.0) for trade in trades],
            original_metrics={
                "final_balance": result_dict.get("final_balance"),
                "roi_pct": result_dict.get("roi_pct"),
                "max_drawdown_pct": result_dict.get("max_drawdown_pct"),
            },
            metadata=metadata or {},
        )

    def trade_count(self) -> int:
        return len(self.trade_pnls or self.trade_returns)

    def to_dict(self) -> dict:
        return {
            "strategy_id": self.strategy_id,
            "strategy_name": self.strategy_name,
            "pair": self.pair,
            "template_type": self.template_type,
            "initial_balance": self.initial_balance,
            "trade_returns": list(self.trade_returns),
            "trade_pnls": list(self.trade_pnls),
            "fees": list(self.fees),
            "original_metrics": dict(self.original_metrics),
            "portfolio_weights": dict(self.portfolio_weights),
            "metadata": dict(self.metadata),
        }
