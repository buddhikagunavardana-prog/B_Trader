from dataclasses import dataclass, field

from src.research.monte_carlo.monte_carlo_input import MonteCarloInput
from src.research.monte_carlo.monte_carlo_scenario import MonteCarloScenario


@dataclass(frozen=True)
class MonteCarloSimulationResult:
    simulation_index: int
    seed: int
    final_balance: float
    roi_pct: float
    max_drawdown_pct: float
    trade_count: int
    positive_run: bool
    ruin: bool
    success: bool = True
    failure_reason: str = ""
    equity_curve: list[float] = field(default_factory=list)

    def to_report_row(self) -> dict:
        return {
            "Simulation Index": self.simulation_index,
            "Seed": self.seed,
            "Final Balance": round(self.final_balance, 2),
            "ROI %": round(self.roi_pct, 2),
            "Max Drawdown %": round(self.max_drawdown_pct, 2),
            "Trade Count": self.trade_count,
            "Positive Run": self.positive_run,
            "Ruin": self.ruin,
            "Failure Reason": self.failure_reason,
        }


def calculate_max_drawdown_pct(equity_curve: list[float]) -> float:
    if not equity_curve:
        return 0.0

    peak = equity_curve[0]
    max_drawdown = 0.0

    for balance in equity_curve:
        if balance > peak:
            peak = balance

        if peak > 0:
            drawdown = (balance - peak) / peak * 100
            if drawdown < max_drawdown:
                max_drawdown = drawdown

    return max_drawdown


def simulate_scenario(
    mc_input: MonteCarloInput,
    scenario: MonteCarloScenario,
    ruin_balance: float = 0.0,
) -> MonteCarloSimulationResult:
    balance = float(mc_input.initial_balance)
    equity_curve = [balance]
    executed_trades = 0
    trade_returns = list(mc_input.trade_returns)
    trade_pnls = list(mc_input.trade_pnls)
    fees = list(mc_input.fees)

    try:
        ordered_positions = [scenario.trade_order[index] for index in range(len(scenario.trade_order))]

        for position in ordered_positions:
            source_index = scenario.sample_indices[position]

            if scenario.missed_trade_mask[position]:
                continue

            return_pct = (
                trade_returns[source_index]
                if trade_returns
                else trade_pnls[source_index] / mc_input.initial_balance * 100
            )
            pnl_amount = (
                trade_pnls[source_index]
                if trade_pnls
                else balance * (return_pct / 100)
            )
            fee_amount = fees[source_index] if fees else 0.0

            adjusted_return_pct = (
                return_pct
                + scenario.slippage_adjustments[position]
                + scenario.return_noise[position]
            )

            if trade_pnls:
                adjusted_pnl = pnl_amount + (
                    mc_input.initial_balance * (
                        scenario.slippage_adjustments[position]
                        + scenario.return_noise[position]
                    )
                    / 100
                )
            else:
                adjusted_pnl = balance * (adjusted_return_pct / 100)

            adjusted_fee = fee_amount * (1 + scenario.fee_adjustments[position] / 100)
            balance += adjusted_pnl - adjusted_fee
            equity_curve.append(balance)
            executed_trades += 1

        roi_pct = (
            (balance - mc_input.initial_balance) / mc_input.initial_balance * 100
            if mc_input.initial_balance > 0
            else 0.0
        )
        max_drawdown_pct = calculate_max_drawdown_pct(equity_curve)

        return MonteCarloSimulationResult(
            simulation_index=scenario.simulation_index,
            seed=scenario.seed,
            final_balance=balance,
            roi_pct=roi_pct,
            max_drawdown_pct=max_drawdown_pct,
            trade_count=executed_trades,
            positive_run=roi_pct > 0,
            ruin=balance <= ruin_balance,
            equity_curve=equity_curve,
        )
    except Exception as error:
        return MonteCarloSimulationResult(
            simulation_index=scenario.simulation_index,
            seed=scenario.seed,
            final_balance=balance,
            roi_pct=0.0,
            max_drawdown_pct=0.0,
            trade_count=executed_trades,
            positive_run=False,
            ruin=True,
            success=False,
            failure_reason=str(error),
            equity_curve=equity_curve,
        )


def run_simulations(
    mc_input: MonteCarloInput,
    scenarios: list[MonteCarloScenario],
) -> list[MonteCarloSimulationResult]:
    return [simulate_scenario(mc_input, scenario) for scenario in scenarios]
