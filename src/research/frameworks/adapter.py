from __future__ import annotations

import json
from time import perf_counter
from typing import Mapping

import pandas as pd

from src.research.frameworks.alignment import alignment_diagnostics, build_causal_alignment
from src.research.frameworks.configuration import validate_research_configuration
from src.research.frameworks.models import DecisionSeriesResult, DecisionSeriesRow, FrameworkResearchConfiguration
from src.research.frameworks.preparation import prepare_timeframe_data
from src.research.frameworks.validator import DECISION_COLUMNS, STATE_COLUMNS, validate_decision_series
from src.research.frameworks.state import ResearchStateController
from src.trading_frameworks.models import FrameworkDirection
from src.research.run_management.run_identity import stable_identity_hash
from src.trading_frameworks.loader import load_trading_framework
from src.trading_frameworks.models import FrameworkContext


def _skipped_row(timestamp, framework, diagnostics, rows_available, reason):
    return DecisionSeriesRow(
        timestamp, framework.metadata.name, framework.metadata.version, "no_trade", "flat",
        False, False, 0.0, "", "", "none", None, None, "none", None, None, "none",
        None, None, diagnostics, (), rows_available,
        {role: value > 0 for role, value in rows_available.items()}, False, False, reason,
    ).to_record()


def _decision_row(decision, diagnostics, rows_available, include_diagnostics, include_warnings):
    risk = decision.risk
    combined = dict(decision.diagnostics)
    if include_diagnostics:
        combined["alignment"] = diagnostics
    return DecisionSeriesRow(
        decision.timestamp, decision.framework, decision.framework_version,
        decision.signal.value, decision.direction.value, bool(decision.entry_allowed),
        bool(decision.exit_requested), float(decision.confidence), decision.entry_reason,
        decision.exit_reason, risk.stop_type, risk.stop_loss, risk.stop_distance,
        risk.take_profit_type, risk.take_profit, risk.reward_to_risk, risk.trailing_stop_type,
        risk.risk_fraction, risk.maximum_holding_period,
        combined if include_diagnostics else {}, tuple(decision.warnings) if include_warnings else (),
        rows_available, {role: value > 0 for role, value in rows_available.items()}, True, True, "",
    ).to_record()


def summarize_decisions(frame: pd.DataFrame, stale_ages: Mapping[str, list[float]], duration: float) -> dict:
    evaluated = frame[frame["decision_valid"]]
    counts = evaluated["signal"].value_counts()
    directions = evaluated["direction"].value_counts()
    return {
        "total_timeline_rows": len(frame), "evaluated_rows": len(evaluated),
        "skipped_rows": int((~frame["decision_valid"]).sum()),
        "warmup_rows": int((~frame["warmup_complete"]).sum()),
        "buy_count": int(counts.get("buy", 0)), "sell_count": int(counts.get("sell", 0)),
        "exit_long_count": int(counts.get("exit_long", 0)), "exit_short_count": int(counts.get("exit_short", 0)),
        "hold_count": int(counts.get("hold", 0)), "no_trade_count": int(counts.get("no_trade", 0)),
        "entry_allowed_count": int(evaluated["entry_allowed"].sum()),
        "exit_requested_count": int(evaluated["exit_requested"].sum()),
        "mean_confidence": float(evaluated["confidence"].mean()) if len(evaluated) else 0.0,
        "median_confidence": float(evaluated["confidence"].median()) if len(evaluated) else 0.0,
        "warning_count": int(sum(len(json.loads(value)) for value in frame["warnings"])),
        "decisions_by_direction": {key: int(value) for key, value in directions.items()},
        "average_stale_age_seconds_by_role": {
            role: (sum(values) / len(values) if values else None) for role, values in stale_ages.items()
        },
        "execution_duration_seconds": duration,
    }


class FrameworkResearchAdapter:
    def __init__(self, configuration: FrameworkResearchConfiguration) -> None:
        self.configuration = validate_research_configuration(configuration)
        self.framework = load_trading_framework(self.configuration.framework, self.configuration.parameters)

    def run(self, timeframe_data: Mapping[str, pd.DataFrame]) -> DecisionSeriesResult:
        started = perf_counter()
        prepare_started = perf_counter()
        prepared = prepare_timeframe_data(self.configuration, self.framework, timeframe_data)
        preparation_seconds = perf_counter() - prepare_started
        align_started = perf_counter()
        alignment = build_causal_alignment(prepared, self.configuration.primary_role, self.configuration.start_timestamp, self.configuration.end_timestamp)
        alignment_seconds = perf_counter() - align_started
        decision_started = perf_counter(); rows = []; skipped = 0
        controller = ResearchStateController(self.framework.metadata.name,cooldown_bars=self.configuration.cooldown_bars,allow_repeated_entries=self.configuration.allow_repeated_entries,reverse_on_opposite_signal=self.configuration.reverse_on_opposite_signal) if self.configuration.enable_stateful_research else None
        stale_ages: dict[str, list[float]] = {role: [] for role in prepared}
        for index, timestamp in enumerate(alignment.timeline):
            diagnostics = alignment_diagnostics(alignment, index)
            positions = {role: alignment.positions[role][index] for role in prepared}
            diagnostic_payload = {role: item.to_dict() for role, item in diagnostics.items()}
            for role, item in diagnostics.items():
                if item.stale_age_seconds is not None: stale_ages[role].append(item.stale_age_seconds)
            warmup = all(
                positions[role] >= self.framework.minimum_history.get(role, 1)
                and prepared[role].first_valid_timestamp is not None
                and diagnostics[role].source_timestamp is not None
                and diagnostics[role].source_timestamp >= prepared[role].first_valid_timestamp
                for role in prepared
            )
            if not warmup and self.configuration.warmup_policy == "skip":
                row=_skipped_row(timestamp, self.framework, diagnostic_payload, positions, "warmup_incomplete")
                if controller:
                    snap=controller.snapshot(timestamp);session={k:v for k,v in snap.session.items() if k!="entry_allowed"};row.update({"research_position_state":snap.position["status"],"previous_position_state":snap.position["status"],"position_transition":"none","bars_in_position_state":snap.position["bars_in_state"],"setup_state":snap.setup["status"],"previous_setup_state":snap.setup["status"],"setup_id":snap.setup["setup_id"],"setup_age":snap.setup["bars_alive"],"setup_transition":"none",**session,"state_warning":"","state_valid":True})
                rows.append(row); skipped += 1
                continue
            direction=FrameworkDirection.FLAT
            if controller and controller.position.direction in {"long","short"}: direction=FrameworkDirection(controller.position.direction)
            context = FrameworkContext(
                {role: item.frame.iloc[:positions[role]] for role, item in prepared.items()},
                current_position=direction,
                symbol=self.configuration.symbol,
            )
            decision = self.framework.execute_prepared(context, timestamp)
            row=_decision_row(decision, diagnostic_payload, positions, self.configuration.include_diagnostics, self.configuration.include_warnings)
            if controller: row.update(controller.apply(decision,timestamp))
            rows.append(row)
        decision_seconds = perf_counter() - decision_started
        frame = pd.DataFrame(rows, columns=DECISION_COLUMNS + (STATE_COLUMNS if controller else ()))
        duration = perf_counter() - started
        validation = validate_decision_series(frame)
        warnings = tuple(warning for item in prepared.values() for warning in item.warnings)
        if self.configuration.allow_experimental:
            warnings += ("Experimental features explicitly allowed; output is not production-ready.",)
        summary = summarize_decisions(frame, stale_ages, duration)
        return DecisionSeriesResult(
            self.configuration, self.framework.metadata.to_dict(), frame, summary, validation, warnings,
            duration, len(frame) - skipped, skipped,
            pd.Timestamp(frame["timestamp"].iloc[0]) if len(frame) else None,
            pd.Timestamp(frame["timestamp"].iloc[-1]) if len(frame) else None,
            {
                "configuration_hash": stable_identity_hash(self.configuration.to_dict()),
                "random_seed": self.configuration.random_seed,
                "preparation_seconds": preparation_seconds, "alignment_seconds": alignment_seconds,
                "decision_generation_seconds": decision_seconds, "repeated_indicator_calculation_count": 0,
            },
        )


def run_framework_decision_series(configuration, timeframe_data) -> DecisionSeriesResult:
    return FrameworkResearchAdapter(configuration).run(timeframe_data)
