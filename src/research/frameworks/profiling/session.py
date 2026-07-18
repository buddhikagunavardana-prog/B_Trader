from __future__ import annotations

from dataclasses import dataclass
from datetime import time
from types import MappingProxyType
from typing import Mapping
from zoneinfo import ZoneInfo

import pandas as pd

from src.research.frameworks.state.models import SessionType
from src.research.frameworks.state.session_state import SessionConfiguration


@dataclass(frozen=True)
class SessionRuntimeContext:
    configuration: SessionConfiguration
    snapshots: tuple[Mapping[str, object], ...]

    @classmethod
    def build(cls, timeline: pd.DatetimeIndex, configuration: SessionConfiguration) -> "SessionRuntimeContext":
        zone = ZoneInfo(configuration.timezone)
        start_h, start_m = map(int, configuration.start.split(":"))
        end_h, end_m = map(int, configuration.end.split(":"))
        cutoff = time(*map(int, configuration.entry_cutoff.split(":")))
        timezone_id = configuration.timezone.replace("/", "-")
        opening_delta = pd.Timedelta(minutes=configuration.opening_range_minutes)
        rows = []
        for raw in timeline:
            ts = pd.Timestamp(raw)
            if ts.tzinfo is None:
                ts = ts.tz_localize("UTC")
            ts = ts.tz_convert(zone)
            normalized = ts.normalize()
            start = normalized + pd.Timedelta(hours=start_h, minutes=start_m)
            end = normalized + pd.Timedelta(hours=end_h, minutes=end_m)
            if configuration.session_type is SessionType.OVERNIGHT_SESSION and end <= start:
                if ts < end:
                    start -= pd.Timedelta(days=1)
                else:
                    end += pd.Timedelta(days=1)
            active = ts.weekday() in configuration.weekdays and start <= ts <= end
            rows.append(MappingProxyType({
                "session_id": f"{start.strftime('%Y-%m-%d')}_{timezone_id}_{configuration.start}",
                "session_state": "active" if active else "closed",
                "session_open": start.isoformat(),
                "session_close": end.isoformat(),
                "opening_range_complete": ts >= start + opening_delta,
                "entry_allowed": active and ts.time() <= cutoff,
            }))
        return cls(configuration, tuple(rows))
