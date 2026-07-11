import random

from src.research.monte_carlo.monte_carlo_context import MonteCarloContext
from src.research.monte_carlo.monte_carlo_input import MonteCarloInput
from src.research.monte_carlo.monte_carlo_scenario import MonteCarloScenario


def _validate_probability(value: float, field_name: str) -> None:
    if value < 0 or value > 1:
        raise ValueError(f"{field_name} must be between 0 and 1")


def _validate_range(values: list[float], field_name: str) -> None:
    if len(values) != 2:
        raise ValueError(f"{field_name} must contain exactly two values")

    if values[0] > values[1]:
        raise ValueError(f"{field_name} minimum cannot exceed maximum")


def validate_sampler_config(context: MonteCarloContext) -> None:
    if context.simulation_count <= 0:
        raise ValueError("simulation_count must be positive")

    _validate_probability(
        context.missed_trade_probability,
        "missed_trade_probability",
    )
    _validate_range(context.slippage_range_pct, "slippage_range_pct")
    _validate_range(context.fee_range_pct, "fee_range_pct")

    if context.return_noise_std_pct < 0:
        raise ValueError("return_noise_std_pct cannot be negative")


class MonteCarloSampler:
    def __init__(self, context: MonteCarloContext):
        validate_sampler_config(context)
        self.context = context

    def _child_seed(self, simulation_index: int) -> int:
        return self.context.random_seed + simulation_index

    def create_scenario(
        self,
        mc_input: MonteCarloInput,
        simulation_index: int,
    ) -> MonteCarloScenario:
        trade_count = mc_input.trade_count()
        child_seed = self._child_seed(simulation_index)
        rng = random.Random(child_seed)
        base_indices = list(range(trade_count))

        if self.context.sample_with_replacement:
            sample_indices = [rng.randrange(trade_count) for _ in base_indices]
        else:
            sample_indices = list(base_indices)

        trade_order = list(range(len(sample_indices)))
        if self.context.shuffle_trade_order:
            rng.shuffle(trade_order)

        if self.context.slippage_enabled:
            slippage_adjustments = [
                rng.uniform(
                    self.context.slippage_range_pct[0],
                    self.context.slippage_range_pct[1],
                )
                for _ in sample_indices
            ]
        else:
            slippage_adjustments = [0.0 for _ in sample_indices]

        if self.context.fee_perturbation_enabled:
            fee_adjustments = [
                rng.uniform(self.context.fee_range_pct[0], self.context.fee_range_pct[1])
                for _ in sample_indices
            ]
        else:
            fee_adjustments = [0.0 for _ in sample_indices]

        if self.context.missed_trade_enabled:
            missed_trade_mask = [
                rng.random() < self.context.missed_trade_probability
                for _ in sample_indices
            ]
        else:
            missed_trade_mask = [False for _ in sample_indices]

        if self.context.return_noise_enabled:
            return_noise = [
                rng.gauss(0.0, self.context.return_noise_std_pct)
                for _ in sample_indices
            ]
        else:
            return_noise = [0.0 for _ in sample_indices]

        return MonteCarloScenario(
            simulation_index=simulation_index,
            seed=child_seed,
            trade_order=trade_order,
            sample_indices=sample_indices,
            slippage_adjustments=slippage_adjustments,
            fee_adjustments=fee_adjustments,
            missed_trade_mask=missed_trade_mask,
            return_noise=return_noise,
        )

    def generate_scenarios(self, mc_input: MonteCarloInput) -> list[MonteCarloScenario]:
        return [
            self.create_scenario(mc_input, simulation_index)
            for simulation_index in range(self.context.simulation_count)
        ]
