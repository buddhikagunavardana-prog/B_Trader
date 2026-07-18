from __future__ import annotations

from typing import Any, Mapping

import numpy as np
import pandas as pd

from src.indicators.registry import indicator_registry
from src.research.frameworks.exceptions import ResearchPreparationError
from src.research.frameworks.models import FrameworkResearchConfiguration, PreparedTimeframeData, PreparationMode
from src.trading_frameworks.base import BaseTradingFramework
from src.trading_frameworks.utilities.timeframe import validate_completed_bar_frame


def _attach(frame: pd.DataFrame, output: Any, columns: tuple[str, ...]) -> None:
    if isinstance(output, pd.Series):
        frame[columns[0]] = output
    elif isinstance(output, pd.DataFrame):
        for column in columns:
            frame[column] = output[column]
    elif isinstance(output, (tuple, list)):
        for column, value in zip(columns, output):
            frame[column] = value
    elif isinstance(output, dict):
        for column, value in zip(columns, output.values()):
            frame[column] = value
    else:
        raise ResearchPreparationError(f"unsupported indicator output: {type(output)!r}")


def _compute_missing(frame: pd.DataFrame, framework: BaseTradingFramework, role: str) -> list[str]:
    computed: list[str] = []
    required = set(framework.schema.required_columns_by_role[role])
    for name in framework.metadata.required_indicators:
        definition = indicator_registry.get(name)
        outputs = tuple(definition["output_columns"])
        if required.intersection(outputs) and not set(outputs).issubset(frame.columns):
            _attach(frame, indicator_registry.calculate(name, frame), outputs)
            computed.extend(column for column in outputs if column in required)
    if framework.metadata.name in {"turtle_trading", "donchian_breakout"} and role == "execution":
        entry_period = int(framework.parameters.get("entry_period", framework.parameters.get("channel_period", 20)))
        exit_period = int(framework.parameters["exit_period"])
        entry = indicator_registry.calculate("donchian_channel", frame, {"period": entry_period})
        exit_channel = indicator_registry.calculate("donchian_channel", frame, {"period": exit_period})
        _attach(frame, entry, ("DONCHIAN_UPPER", "DONCHIAN_MIDDLE", "DONCHIAN_LOWER"))
        _attach(frame, exit_channel, ("DONCHIAN_EXIT_UPPER", "DONCHIAN_EXIT_MIDDLE", "DONCHIAN_EXIT_LOWER"))
        computed.extend(["DONCHIAN_UPPER", "DONCHIAN_LOWER", "DONCHIAN_EXIT_UPPER", "DONCHIAN_EXIT_LOWER"])
    return sorted(set(computed))


def prepare_timeframe_data(
    configuration: FrameworkResearchConfiguration,
    framework: BaseTradingFramework,
    timeframe_data: Mapping[str, pd.DataFrame],
) -> dict[str, PreparedTimeframeData]:
    roles = set(framework.metadata.timeframe_roles)
    if set(timeframe_data) != roles:
        raise ResearchPreparationError(f"timeframe data roles must be exactly {sorted(roles)}")
    prepared: dict[str, PreparedTimeframeData] = {}
    for role in framework.metadata.timeframe_roles:
        source = timeframe_data[role]
        validate_completed_bar_frame(source, role)
        frame = source.copy(deep=True)
        if frame.index.tz is None:
            frame.index = frame.index.tz_localize("UTC")
        else:
            frame.index = frame.index.tz_convert("UTC")
        warnings: list[str] = []
        numeric = list(frame.select_dtypes(include="number").columns)
        infinite = int(np.isinf(frame[numeric].to_numpy()).sum()) if numeric else 0
        if infinite:
            frame[numeric] = frame[numeric].replace([np.inf, -np.inf], np.nan)
            warnings.append(f"sanitized {infinite} infinite values to NaN")
        required = tuple(framework.schema.required_columns_by_role[role])
        missing = [column for column in required if column not in frame.columns]
        computed: list[str] = []
        if missing and configuration.preparation_mode is PreparationMode.COMPUTE_MISSING:
            try:
                computed = _compute_missing(frame, framework, role)
            except (KeyError, ValueError) as error:
                raise ResearchPreparationError(f"cannot compute indicators for role '{role}': {error}") from error
            missing = [column for column in required if column not in frame.columns]
        if missing:
            raise ResearchPreparationError(f"role '{role}' missing precomputed columns: {', '.join(missing)}")
        valid_mask = frame[list(required)].notna().all(axis=1)
        first_valid = pd.Timestamp(frame.index[valid_mask.argmax()]) if valid_mask.any() else None
        warmup_rows = int((~valid_mask).cumprod().sum()) if len(valid_mask) else 0
        indicator_columns = tuple(column for column in required if column not in {"open", "high", "low", "close", "volume"})
        prepared[role] = PreparedTimeframeData(
            role, configuration.timeframe_roles[role], frame, indicator_columns, first_valid,
            pd.Timestamp(frame.index[-1]) if len(frame) else None, len(frame), warmup_rows,
            {"mode": configuration.preparation_mode.value, "timezone": "UTC", "source_preserved": True, "computed_columns": computed}, tuple(warnings),
        )
    return prepared
