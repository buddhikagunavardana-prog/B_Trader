from __future__ import annotations

from datetime import time
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import pandas as pd

from src.trading_frameworks.base import BaseTradingFramework
from src.trading_frameworks.exceptions import FrameworkConfigurationError
from src.trading_frameworks.models import FrameworkContext, FrameworkDecision, FrameworkDirection, FrameworkMetadata, FrameworkSignal, FrameworkStability, ParameterDefinition, ParameterType
from src.trading_frameworks.schema import FrameworkSchema
from src.trading_frameworks.smc.models import SMCDirection, SMCLifecycle, SMCFrameworkState, SMCZone
from src.trading_frameworks.smc.primitives import average_true_range, confirmed_swings, dealing_range, displacement_event, equal_liquidity, imbalance_zones, structural_bias, structure_event, zone_status


OHLCV = ("open", "high", "low", "close", "volume")
SMC_NAMES = (
    "order_block", "fair_value_gap", "break_of_structure", "change_of_character",
    "liquidity_sweep", "equal_high_low_liquidity", "breaker_block", "mitigation_block",
    "premium_discount_zone", "market_structure_shift", "balanced_price_range",
    "displacement", "judas_swing", "kill_zone_setup", "power_of_three",
)
DISPLAY = {
    "order_block": "Order Block", "fair_value_gap": "Fair Value Gap", "break_of_structure": "Break of Structure",
    "change_of_character": "Change of Character", "liquidity_sweep": "Liquidity Sweep",
    "equal_high_low_liquidity": "Equal High / Equal Low Liquidity", "breaker_block": "Breaker Block",
    "mitigation_block": "Mitigation Block", "premium_discount_zone": "Premium / Discount Zone",
    "market_structure_shift": "Market Structure Shift", "balanced_price_range": "Balanced Price Range",
    "displacement": "Displacement", "judas_swing": "Judas Swing", "kill_zone_setup": "Kill Zone Setup",
    "power_of_three": "Power of Three",
}


def _period(name: str, default: int, minimum: int = 1, maximum: int = 200) -> ParameterDefinition:
    return ParameterDefinition(name, ParameterType.PERIOD, default, name.replace("_", " "), minimum, maximum, optimization_allowed=False)


def _number(name: str, default: float, minimum: float, maximum: float) -> ParameterDefinition:
    return ParameterDefinition(name, ParameterType.FLOAT, default, name.replace("_", " "), minimum, maximum, optimization_allowed=False)


def _choice(name: str, default: str, values: tuple[str, ...]) -> ParameterDefinition:
    return ParameterDefinition(name, ParameterType.ENUM, default, name.replace("_", " "), allowed_values=values, optimization_allowed=False)


COMMON = (
    _period("swing_period", 2, 1, 10),
    _choice("confirmation_mode", "close", ("close", "wick")),
    _period("maximum_age_bars", 40, 2, 500),
    _number("minimum_gap", 0.01, 0.0, 1000000.0),
    _period("atr_period", 14, 2, 100),
    _number("body_ratio", .65, .1, 1.0),
    _number("atr_multiple", .8, 0.0, 10.0),
    _number("liquidity_tolerance", .15, 0.0, 1000000.0),
    _choice("liquidity_tolerance_mode", "absolute", ("absolute", "percentage", "atr")),
    _number("liquidity_tolerance_percentage", .001, 0.0, .1),
    _number("liquidity_tolerance_atr", .1, 0.0, 10.0),
    _period("minimum_touches", 2, 2, 10),
    _period("reclaim_window", 3, 1, 20),
    _choice("zone_mode", "wick", ("wick", "body")),
    _choice("mitigation_rule", "touch", ("touch", "midpoint", "full")),
    _choice("invalidation_rule", "close", ("close", "wick")),
    ParameterDefinition("require_displacement", ParameterType.BOOLEAN, True, "require displacement confirmation", optimization_allowed=False),
    _choice("session_name", "custom", ("asia", "london", "new_york_am", "new_york_pm", "custom")),
    ParameterDefinition("session_timezone", ParameterType.STRING, "UTC", "IANA session timezone", optimization_allowed=False),
    ParameterDefinition("session_start", ParameterType.STRING, "08:00", "session start HH:MM", optimization_allowed=False),
    ParameterDefinition("session_end", ParameterType.STRING, "12:00", "session end HH:MM", optimization_allowed=False),
    _period("reference_bars", 8, 2, 60),
)


def _schema(name: str) -> FrameworkSchema:
    roles = ("execution", "structure") if name == "premium_discount_zone" else ("execution",)
    timeframes = {"execution": "15m", **({"structure": "1h"} if len(roles) == 2 else {})}
    columns = {role: OHLCV for role in roles}
    return FrameworkSchema(
        FrameworkMetadata(
            name=name, display_name=DISPLAY[name], category="smc",
            description=f"Deterministic {DISPLAY[name]} structural research framework.",
            timeframe_roles=roles, default_timeframes=timeframes, required_indicators=(), required_data_columns=OHLCV,
            stability=FrameworkStability.STABLE, aliases=(), version="1.0.0",
            tags=("smc", "ict_style", "structural_research", "research_only"),
            compatible_market_regimes=("structural",),
            state_policy_requirements=("setup", "event_consumption", "serializable_state"),
            reference_notes="ICT-style terminology is encoded as explicit completed-bar structural rules for reproducible research.",
            causality_notes="Symmetric swings become visible only at the right-window confirmation close; events use confirmation time.",
            research_limitations="Structural research classification only; no trade advice or financial-performance inference.",
            execution_warning="Research classification only; execution is outside this framework.",
        ),
        COMMON, columns,
        entry_logic="Emit a normalized directional research event only after completed-bar structural confirmation.",
        exit_logic="Lifecycle invalidation is diagnostic; this framework does not manage positions.",
        risk_logic="The framework emits no risk or financial-execution proposal.",
        trade_management="None; research-only structural state.",
    )


class SMCFramework(BaseTradingFramework):
    kind = ""
    minimum_history = {"execution": 18}

    def __init__(self, parameters=None) -> None:
        super().__init__(parameters)
        try:
            ZoneInfo(self.parameters["session_timezone"])
            start = time.fromisoformat(self.parameters["session_start"])
            end = time.fromisoformat(self.parameters["session_end"])
        except (ValueError, ZoneInfoNotFoundError) as error:
            raise FrameworkConfigurationError("session timezone and HH:MM bounds must be valid") from error
        if start == end:
            raise FrameworkConfigurationError("session start and end must differ")
        if self.parameters["require_displacement"] and self.parameters["atr_multiple"] <= 0:
            raise FrameworkConfigurationError("displacement requirement needs a positive ATR multiple")

    def _decision(self, timestamp, direction=SMCDirection.NEUTRAL, lifecycle=SMCLifecycle.UNDEFINED, reason="NO_ACTION", **attributes):
        state = SMCFrameworkState(self.kind, lifecycle, direction, reason, timestamp.isoformat(), attributes=attributes)
        signal = FrameworkSignal.NO_TRADE
        framework_direction = FrameworkDirection.FLAT
        if reason.endswith("CONFIRMED") or reason.endswith("DETECTED") or reason in {"LIQUIDITY_RECLAIMED", "DISTRIBUTION_CONFIRMED"}:
            if direction is SMCDirection.BULLISH:
                signal, framework_direction = FrameworkSignal.BUY, FrameworkDirection.LONG
            elif direction is SMCDirection.BEARISH:
                signal, framework_direction = FrameworkSignal.SELL, FrameworkDirection.SHORT
        return FrameworkDecision(self.kind, timestamp, signal, framework_direction, .75 if signal is not FrameworkSignal.NO_TRADE else 0.0, reason.replace("_", " ").title(), diagnostics={"smc_state": state.to_dict(), "reason_code": reason, "lifecycle_state": lifecycle.value, **attributes})

    def generate_decision(self, context: FrameworkContext, timestamp: pd.Timestamp | None) -> FrameworkDecision:
        frame = context.frames["execution"]
        p = self.parameters
        swings = confirmed_swings(frame, p["swing_period"], p["swing_period"])
        event = structure_event(frame, swings, p["confirmation_mode"])
        bias = structural_bias(swings)
        displacement = displacement_event(frame, p["atr_period"], p["body_ratio"], p["atr_multiple"])
        fvgs = imbalance_zones(frame, p["minimum_gap"])
        latest_fvg = fvgs[-1] if fvgs else None

        if self.kind == "break_of_structure":
            return self._decision(timestamp, event["direction"], SMCLifecycle.CONFIRMED, "BOS_CONFIRMED", structure_level=event["swing"].price, confirmation_timestamp=timestamp.isoformat()) if event else self._decision(timestamp, reason="NO_STRUCTURE_BREAK")
        if self.kind == "change_of_character":
            if event and bias is not SMCDirection.NEUTRAL and event["direction"] is not bias:
                return self._decision(timestamp, event["direction"], SMCLifecycle.CONFIRMED, "CHOCH_CONFIRMED", prior_bias=bias.value)
            return self._decision(timestamp, reason="PRIOR_STRUCTURE_NOT_REVERSED")
        if self.kind == "market_structure_shift":
            if event and bias is not SMCDirection.NEUTRAL and event["direction"] is not bias and displacement and displacement["direction"] is event["direction"]:
                return self._decision(timestamp, event["direction"], SMCLifecycle.CONFIRMED, "MSS_CONFIRMED", prior_bias=bias.value, displacement=True)
            return self._decision(timestamp, reason="MSS_SEQUENCE_INCOMPLETE")
        if self.kind == "displacement":
            return self._decision(timestamp, displacement["direction"], SMCLifecycle.DETECTED, "DISPLACEMENT_DETECTED", body=displacement["body"], atr=displacement["atr"]) if displacement else self._decision(timestamp, reason="DISPLACEMENT_THRESHOLD_NOT_MET")
        if self.kind == "fair_value_gap":
            if latest_fvg and pd.Timestamp(latest_fvg.detected_at) == timestamp:
                if p["require_displacement"] and (not displacement or displacement["direction"] is not latest_fvg.direction):
                    return self._decision(timestamp, latest_fvg.direction, SMCLifecycle.CANDIDATE, "FVG_DISPLACEMENT_MISSING", zone=latest_fvg.to_dict())
                return self._decision(timestamp, latest_fvg.direction, SMCLifecycle.DETECTED, "FVG_DETECTED", zone=latest_fvg.to_dict())
            if latest_fvg:
                status = zone_status(latest_fvg, frame, p["maximum_age_bars"])
                return self._decision(timestamp, latest_fvg.direction, status, f"FVG_{status.value.upper()}", zone=latest_fvg.to_dict())
            return self._decision(timestamp, reason="NO_IMBALANCE")
        if self.kind == "balanced_price_range":
            bullish = [zone for zone in fvgs if zone.direction is SMCDirection.BULLISH]
            bearish = [zone for zone in fvgs if zone.direction is SMCDirection.BEARISH]
            if bullish and bearish:
                lower, upper = max(bullish[-1].lower, bearish[-1].lower), min(bullish[-1].upper, bearish[-1].upper)
                if lower < upper:
                    return self._decision(timestamp, lifecycle=SMCLifecycle.DETECTED, reason="BPR_DETECTED", lower=lower, upper=upper, lineage=[bullish[-1].zone_id, bearish[-1].zone_id])
            return self._decision(timestamp, reason="NO_OPPOSING_IMBALANCE_OVERLAP")
        if self.kind == "equal_high_low_liquidity":
            tolerance = p["liquidity_tolerance"]
            if p["liquidity_tolerance_mode"] == "percentage":
                tolerance = abs(float(frame.iloc[-1].close)) * p["liquidity_tolerance_percentage"]
            elif p["liquidity_tolerance_mode"] == "atr":
                tolerance = float(average_true_range(frame, p["atr_period"]).iloc[-1]) * p["liquidity_tolerance_atr"]
            pools = equal_liquidity(swings, tolerance, p["minimum_touches"])
            if pools:
                pool = pools[-1]; direction = SMCDirection.BEARISH if pool["kind"] == "high" else SMCDirection.BULLISH
                return self._decision(timestamp, direction, SMCLifecycle.ACTIVE, "LIQUIDITY_POOL_ACTIVE", pool_id=pool["pool_id"], level=pool["level"], touches=pool["touches"])
            return self._decision(timestamp, reason="NO_EQUAL_LIQUIDITY_CLUSTER")
        if self.kind == "liquidity_sweep":
            if swings and len(frame) >= 2:
                prior = frame.iloc[-2]; current = frame.iloc[-1]
                highs = [s for s in swings if s.kind == "high" and s.confirmation_timestamp < timestamp]
                lows = [s for s in swings if s.kind == "low" and s.confirmation_timestamp < timestamp]
                if highs and current.high >= highs[-1].price + p["liquidity_tolerance"] and current.close < highs[-1].price and prior.close <= highs[-1].price:
                    return self._decision(timestamp, SMCDirection.BEARISH, SMCLifecycle.CONFIRMED, "LIQUIDITY_RECLAIMED", level=highs[-1].price)
                if lows and current.low <= lows[-1].price - p["liquidity_tolerance"] and current.close > lows[-1].price and prior.close >= lows[-1].price:
                    return self._decision(timestamp, SMCDirection.BULLISH, SMCLifecycle.CONFIRMED, "LIQUIDITY_RECLAIMED", level=lows[-1].price)
            return self._decision(timestamp, reason="NO_SWEEP_RECLAIM")
        if self.kind in {"order_block", "breaker_block", "mitigation_block"}:
            return self._zone_family(frame, timestamp, event, displacement)
        if self.kind == "premium_discount_zone":
            structure = context.frames["structure"]
            structure_swings = confirmed_swings(structure, p["swing_period"], p["swing_period"])
            bounds = dealing_range(structure_swings)
            if not bounds:
                return self._decision(timestamp, reason="DEALING_RANGE_UNDEFINED")
            low, high = bounds; price = float(frame.iloc[-1].close); ratio = (price - low) / (high - low)
            state = "discount" if ratio < .45 else "premium" if ratio > .55 else "equilibrium"
            return self._decision(timestamp, lifecycle=SMCLifecycle.ACTIVE, reason=f"{state.upper()}_CLASSIFIED", classification=state, range_low=low, range_high=high)
        if self.kind in {"judas_swing", "kill_zone_setup", "power_of_three"}:
            return self._session_family(frame, timestamp)
        return self._decision(timestamp, reason="NO_ACTION")

    def _zone_family(self, frame, timestamp, event, displacement):
        p = self.parameters
        if not event or (p["require_displacement"] and (not displacement or displacement["direction"] is not event["direction"])):
            return self._decision(timestamp, reason="STRUCTURAL_PRECONDITION_MISSING")
        opposite = frame.iloc[-2]
        lower = float(min(opposite.open, opposite.close) if p["zone_mode"] == "body" else opposite.low)
        upper = float(max(opposite.open, opposite.close) if p["zone_mode"] == "body" else opposite.high)
        lineage = f"{event['swing'].kind}-{event['swing'].pivot_timestamp.isoformat()}"
        if self.kind == "order_block":
            reason, lifecycle = "ORDER_BLOCK_CONFIRMED", SMCLifecycle.CONFIRMED
        elif self.kind == "breaker_block":
            if structural_bias(confirmed_swings(frame.iloc[:-1], p["swing_period"], p["swing_period"])) is event["direction"]:
                return self._decision(timestamp, reason="FAILED_BLOCK_LINEAGE_MISSING")
            reason, lifecycle = "BREAKER_BLOCK_CONFIRMED", SMCLifecycle.CONFIRMED
        else:
            if not (opposite.low <= event["swing"].price <= opposite.high):
                return self._decision(timestamp, reason="RETRACEMENT_REQUIREMENT_MISSING")
            reason, lifecycle = "MITIGATION_BLOCK_CONFIRMED", SMCLifecycle.CONFIRMED
        return self._decision(timestamp, event["direction"], lifecycle, reason, lower=lower, upper=upper, lineage=[lineage])

    def _session_family(self, frame, timestamp):
        from src.research.frameworks.state.models import SessionType
        from src.research.frameworks.state.session_state import SessionConfiguration, session_snapshot

        p = self.parameters
        named_windows = {"asia": ("00:00", "04:00"), "london": ("07:00", "10:00"), "new_york_am": ("08:30", "12:00"), "new_york_pm": ("13:00", "16:00")}
        session_start, session_end = named_windows.get(p["session_name"], (p["session_start"], p["session_end"]))
        session_type = SessionType.OVERNIGHT_SESSION if time.fromisoformat(session_end) < time.fromisoformat(session_start) else SessionType.DAILY_SESSION
        configuration = SessionConfiguration(session_type=session_type, timezone=p["session_timezone"], start=session_start, end=session_end, entry_cutoff=session_end)
        snapshot = session_snapshot(timestamp, configuration)
        if snapshot["session_state"] != "active":
            return self._decision(timestamp, lifecycle=SMCLifecycle.EXPIRED, reason="SESSION_CLOSED", session=snapshot)
        reference = frame.iloc[-min(len(frame), p["reference_bars"] + 1):-1]
        if reference.empty:
            return self._decision(timestamp, reason="REFERENCE_RANGE_INCOMPLETE", session=snapshot)
        row = frame.iloc[-1]; high, low = float(reference.high.max()), float(reference.low.min())
        raid_up = row.high > high and row.close < high
        raid_down = row.low < low and row.close > low
        direction = SMCDirection.BEARISH if raid_up else SMCDirection.BULLISH if raid_down else SMCDirection.NEUTRAL
        if self.kind == "judas_swing":
            history = frame.iloc[-min(len(frame), p["reference_bars"] + p["reclaim_window"]):-p["reclaim_window"]]
            recent = frame.iloc[-p["reclaim_window"]:]
            if len(history):
                high, low = float(history.high.max()), float(history.low.min())
                raid_up = bool((recent.high > high).any()) and row.close < high
                raid_down = bool((recent.low < low).any()) and row.close > low
                direction = SMCDirection.BEARISH if raid_up else SMCDirection.BULLISH if raid_down else SMCDirection.NEUTRAL
            return self._decision(timestamp, direction, SMCLifecycle.CONFIRMED, "JUDAS_SWING_CONFIRMED", session=snapshot, range_high=high, range_low=low) if direction is not SMCDirection.NEUTRAL else self._decision(timestamp, lifecycle=SMCLifecycle.ACTIVE, reason="AWAITING_LIQUIDITY_RAID", session=snapshot)
        if self.kind == "kill_zone_setup":
            event = displacement_event(frame, p["atr_period"], p["body_ratio"], p["atr_multiple"])
            return self._decision(timestamp, event["direction"], SMCLifecycle.CONFIRMED, "KILL_ZONE_SETUP_CONFIRMED", session=snapshot) if event else self._decision(timestamp, lifecycle=SMCLifecycle.ACTIVE, reason="KILL_ZONE_ACTIVE_NO_STRUCTURE", session=snapshot)
        session_frame = frame.loc[frame.index >= pd.Timestamp(snapshot["session_open"])]
        if len(session_frame) < p["reference_bars"]:
            return self._decision(timestamp, reason="PO3_STAGE_UNDEFINED", session=snapshot)
        accumulation = session_frame.iloc[:p["reference_bars"]]
        range_high, range_low = float(accumulation.high.max()), float(accumulation.low.min())
        compact = (range_high - range_low) / max(abs(float(accumulation.close.mean())), 1e-12) < .03
        if not compact:
            return self._decision(timestamp, lifecycle=SMCLifecycle.INVALIDATED, reason="ACCUMULATION_INVALIDATED", session=snapshot)
        after = session_frame.iloc[p["reference_bars"]:]
        raid_position = None; po3_direction = SMCDirection.NEUTRAL
        for position, (_, candidate) in enumerate(after.iterrows()):
            if candidate.high > range_high and candidate.close < range_high:
                raid_position, po3_direction = position, SMCDirection.BEARISH; break
            if candidate.low < range_low and candidate.close > range_low:
                raid_position, po3_direction = position, SMCDirection.BULLISH; break
        if raid_position is None:
            return self._decision(timestamp, lifecycle=SMCLifecycle.ACCUMULATION, reason="ACCUMULATION_CONFIRMED", session=snapshot)
        distribution_position = None
        for position in range(raid_position + 1, len(after)):
            observed = displacement_event(pd.concat((accumulation, after.iloc[:position + 1])), p["atr_period"], p["body_ratio"], p["atr_multiple"])
            if observed and observed["direction"] is po3_direction:
                distribution_position = position; break
        if distribution_position is None:
            return self._decision(timestamp, po3_direction, SMCLifecycle.MANIPULATION, "MANIPULATION_CONFIRMED", session=snapshot)
        later = after.iloc[distribution_position + 1:]
        completed = bool((later.close > range_high).any()) if po3_direction is SMCDirection.BULLISH else bool((later.close < range_low).any())
        lifecycle = SMCLifecycle.COMPLETED if completed else SMCLifecycle.DISTRIBUTION
        reason = "PO3_COMPLETED" if completed else "DISTRIBUTION_CONFIRMED"
        return self._decision(timestamp, po3_direction, lifecycle, reason, session=snapshot)


def _build(name: str):
    return type("".join(part.title() for part in name.split("_")) + "Framework", (SMCFramework,), {"__module__": __name__, "kind": name, "schema": _schema(name)})


for _name in SMC_NAMES:
    globals()["".join(part.title() for part in _name.split("_")) + "Framework"] = _build(_name)

__all__ = ["SMC_NAMES", "SMCFramework"] + ["".join(part.title() for part in name.split("_")) + "Framework" for name in SMC_NAMES]
