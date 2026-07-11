from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class MonteCarloScenario:
    simulation_index: int
    seed: int
    trade_order: list[int]
    sample_indices: list[int]
    slippage_adjustments: list[float]
    fee_adjustments: list[float]
    missed_trade_mask: list[bool]
    return_noise: list[float]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "simulation_index": self.simulation_index,
            "seed": self.seed,
            "trade_order": list(self.trade_order),
            "sample_indices": list(self.sample_indices),
            "slippage_adjustments": list(self.slippage_adjustments),
            "fee_adjustments": list(self.fee_adjustments),
            "missed_trade_mask": list(self.missed_trade_mask),
            "return_noise": list(self.return_noise),
            "metadata": dict(self.metadata),
        }
