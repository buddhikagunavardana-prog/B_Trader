from __future__ import annotations

from math import isfinite

from src.trading_frameworks.models import RiskProposal


def finite_number(value: object) -> bool:
    try:
        return isfinite(float(value))
    except (TypeError, ValueError):
        return False


def atr_risk(
    price: float,
    atr: object,
    direction: int,
    stop_multiple: float,
    reward_multiple: float,
    risk_fraction: float,
    trailing: bool = False,
    maximum_holding_period: int | None = None,
    scale_in_units: int = 0,
) -> RiskProposal:
    if not finite_number(atr) or float(atr) <= 0:
        return RiskProposal(risk_fraction=risk_fraction, notes=("ATR unavailable; no price levels proposed.",))
    distance = float(atr) * stop_multiple
    return RiskProposal(
        stop_loss=price - direction * distance,
        take_profit=price + direction * distance * reward_multiple,
        risk_fraction=risk_fraction,
        volatility_unit=float(atr),
        trailing_stop=trailing,
        stop_type="atr_multiple",
        stop_distance=distance,
        take_profit_type="reward_multiple",
        reward_to_risk=reward_multiple,
        trailing_stop_type="atr_multiple" if trailing else "none",
        maximum_holding_period=maximum_holding_period,
        scale_in_units=scale_in_units,
    )
