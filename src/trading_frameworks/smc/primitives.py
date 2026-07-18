from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Iterable

import numpy as np
import pandas as pd

from src.trading_frameworks.smc.models import SMCDirection, SMCLifecycle, SMCZone


@dataclass(frozen=True)
class ConfirmedSwing:
    kind: str
    price: float
    pivot_timestamp: pd.Timestamp
    confirmation_timestamp: pd.Timestamp
    pivot_position: int


def confirmed_swings(frame: pd.DataFrame, left: int = 2, right: int = 2) -> tuple[ConfirmedSwing, ...]:
    """Return pivots only when all required right-side completed bars exist."""
    if left < 1 or right < 1:
        raise ValueError("swing windows must be positive")
    highs = frame["high"].to_numpy(dtype=float)
    lows = frame["low"].to_numpy(dtype=float)
    result: list[ConfirmedSwing] = []
    for position in range(left, len(frame) - right):
        high_window = highs[position - left:position + right + 1]
        low_window = lows[position - left:position + right + 1]
        confirmation = frame.index[position + right]
        if highs[position] == np.max(high_window) and np.count_nonzero(high_window == highs[position]) == 1:
            result.append(ConfirmedSwing("high", highs[position], frame.index[position], confirmation, position))
        if lows[position] == np.min(low_window) and np.count_nonzero(low_window == lows[position]) == 1:
            result.append(ConfirmedSwing("low", lows[position], frame.index[position], confirmation, position))
    return tuple(sorted(result, key=lambda item: (item.confirmation_timestamp, item.pivot_position, item.kind)))


def average_true_range(frame: pd.DataFrame, period: int = 14) -> pd.Series:
    previous = frame["close"].shift(1)
    true_range = pd.concat(((frame["high"] - frame["low"]), (frame["high"] - previous).abs(), (frame["low"] - previous).abs()), axis=1).max(axis=1)
    return true_range.rolling(period, min_periods=1).mean()


def displacement_event(frame: pd.DataFrame, atr_period: int, body_ratio: float, atr_multiple: float) -> dict | None:
    if len(frame) < 2:
        return None
    row = frame.iloc[-1]
    candle_range = float(row.high - row.low)
    body = abs(float(row.close - row.open))
    atr = float(average_true_range(frame, atr_period).iloc[-1])
    if candle_range <= 0 or body / candle_range < body_ratio or body < atr * atr_multiple:
        return None
    direction = SMCDirection.BULLISH if row.close > row.open else SMCDirection.BEARISH
    close_location = (float(row.close) - float(row.low)) / candle_range
    if (direction is SMCDirection.BULLISH and close_location < .65) or (direction is SMCDirection.BEARISH and close_location > .35):
        return None
    return {"direction": direction, "body": body, "atr": atr, "timestamp": frame.index[-1]}


def imbalance_zones(frame: pd.DataFrame, minimum_gap: float = 0.0) -> tuple[SMCZone, ...]:
    zones: list[SMCZone] = []
    for position in range(2, len(frame)):
        first, third = frame.iloc[position - 2], frame.iloc[position]
        detected = frame.index[position]
        if float(third.low) - float(first.high) >= minimum_gap and third.low > first.high:
            lower, upper, direction = float(first.high), float(third.low), SMCDirection.BULLISH
        elif float(first.low) - float(third.high) >= minimum_gap and third.high < first.low:
            lower, upper, direction = float(third.high), float(first.low), SMCDirection.BEARISH
        else:
            continue
        digest = sha256(f"{direction.value}|{detected.isoformat()}|{lower:.12g}|{upper:.12g}".encode()).hexdigest()[:16]
        zones.append(SMCZone(f"fvg-{digest}", direction, lower, upper, detected.isoformat()))
    return tuple(zones)


def zone_status(zone: SMCZone, frame: pd.DataFrame, maximum_age: int = 40) -> SMCLifecycle:
    detected = pd.Timestamp(zone.detected_at)
    later = frame.loc[frame.index > detected]
    if len(later) > maximum_age:
        later = later.iloc[:maximum_age]
        expired = True
    else:
        expired = False
    if later.empty:
        return SMCLifecycle.ACTIVE
    if zone.direction is SMCDirection.BULLISH:
        full = later["low"] <= zone.lower
        partial = later["low"] < zone.upper
        invalid = later["close"] < zone.lower
    else:
        full = later["high"] >= zone.upper
        partial = later["high"] > zone.lower
        invalid = later["close"] > zone.upper
    if bool(invalid.any()):
        return SMCLifecycle.INVALIDATED
    if bool(full.any()):
        return SMCLifecycle.FILLED
    if bool(partial.any()):
        return SMCLifecycle.PARTIALLY_FILLED
    return SMCLifecycle.EXPIRED if expired else SMCLifecycle.ACTIVE


def structure_event(frame: pd.DataFrame, swings: Iterable[ConfirmedSwing], confirmation_mode: str = "close") -> dict | None:
    if len(frame) < 2:
        return None
    highs = [item for item in swings if item.kind == "high" and item.confirmation_timestamp < frame.index[-1]]
    lows = [item for item in swings if item.kind == "low" and item.confirmation_timestamp < frame.index[-1]]
    current, previous = frame.iloc[-1], frame.iloc[-2]
    up_value = float(current.close if confirmation_mode == "close" else current.high)
    prior_up = float(previous.close if confirmation_mode == "close" else previous.high)
    down_value = float(current.close if confirmation_mode == "close" else current.low)
    prior_down = float(previous.close if confirmation_mode == "close" else previous.low)
    if highs and prior_up <= highs[-1].price < up_value:
        return {"direction": SMCDirection.BULLISH, "swing": highs[-1], "timestamp": frame.index[-1]}
    if lows and prior_down >= lows[-1].price > down_value:
        return {"direction": SMCDirection.BEARISH, "swing": lows[-1], "timestamp": frame.index[-1]}
    return None


def structural_bias(swings: Iterable[ConfirmedSwing]) -> SMCDirection:
    values = tuple(swings)
    highs = [item.price for item in values if item.kind == "high"]
    lows = [item.price for item in values if item.kind == "low"]
    if len(highs) >= 2 and len(lows) >= 2:
        if highs[-1] > highs[-2] and lows[-1] > lows[-2]:
            return SMCDirection.BULLISH
        if highs[-1] < highs[-2] and lows[-1] < lows[-2]:
            return SMCDirection.BEARISH
    return SMCDirection.NEUTRAL


def equal_liquidity(swings: Iterable[ConfirmedSwing], tolerance: float, minimum_touches: int = 2) -> tuple[dict, ...]:
    pools: list[dict] = []
    for kind in ("high", "low"):
        candidates = [item for item in swings if item.kind == kind]
        consumed: set[int] = set()
        for index, swing in enumerate(candidates):
            if index in consumed:
                continue
            cluster = [item for item in candidates[index:] if abs(item.price - swing.price) <= tolerance]
            if len(cluster) >= minimum_touches:
                positions = tuple(item.pivot_position for item in cluster)
                consumed.update(candidates.index(item) for item in cluster)
                pools.append({"pool_id": f"equal-{kind}-{positions[0]}-{positions[-1]}", "kind": kind, "level": sum(item.price for item in cluster) / len(cluster), "touches": len(cluster), "confirmed_at": cluster[-1].confirmation_timestamp})
    return tuple(pools)


def dealing_range(swings: Iterable[ConfirmedSwing]) -> tuple[float, float] | None:
    values = tuple(swings)
    highs = [item for item in values if item.kind == "high"]
    lows = [item for item in values if item.kind == "low"]
    if not highs or not lows:
        return None
    low, high = lows[-1].price, highs[-1].price
    return (low, high) if low < high else None
