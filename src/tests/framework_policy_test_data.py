import pandas as pd

from src.research.frameworks.state import ResearchStateController
from src.research.frameworks.state.policies import PolicyConfiguration
from src.trading_frameworks.models import FrameworkDecision, FrameworkDirection, FrameworkSignal, RiskProposal


T0 = pd.Timestamp("2026-01-01T00:00:00Z")


def decision(signal: FrameworkSignal, framework: str = "inside_bar_breakout", maximum_holding_period=None):
    direction = FrameworkDirection.LONG if signal is FrameworkSignal.BUY else FrameworkDirection.SHORT if signal is FrameworkSignal.SELL else FrameworkDirection.FLAT
    return FrameworkDecision(framework, T0, signal, direction, .8, "test proposal", RiskProposal(maximum_holding_period=maximum_holding_period))


def controller(framework="inside_bar_breakout", **policy):
    return ResearchStateController(framework, policy_configuration=PolicyConfiguration.from_mapping(policy))
