from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Mapping


class SMCDirection(str, Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


class SMCLifecycle(str, Enum):
    UNDEFINED = "undefined"
    CANDIDATE = "candidate"
    DETECTED = "detected"
    CONFIRMED = "confirmed"
    ACTIVE = "active"
    TOUCHED = "touched"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    MITIGATED = "mitigated"
    INVALIDATED = "invalidated"
    EXPIRED = "expired"
    RESOLVED = "resolved"
    ACCUMULATION = "accumulation"
    MANIPULATION = "manipulation"
    DISTRIBUTION = "distribution"
    COMPLETED = "completed"


@dataclass(frozen=True)
class SMCZone:
    zone_id: str
    direction: SMCDirection
    lower: float
    upper: float
    detected_at: str
    lifecycle: SMCLifecycle = SMCLifecycle.DETECTED
    lineage: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["direction"] = self.direction.value
        value["lifecycle"] = self.lifecycle.value
        value["lineage"] = list(self.lineage)
        return value

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "SMCZone":
        data = dict(value)
        data["direction"] = SMCDirection(data["direction"])
        data["lifecycle"] = SMCLifecycle(data["lifecycle"])
        data["lineage"] = tuple(data.get("lineage", ()))
        return cls(**data)


@dataclass(frozen=True)
class SMCFrameworkState:
    framework_id: str
    lifecycle: SMCLifecycle = SMCLifecycle.UNDEFINED
    direction: SMCDirection = SMCDirection.NEUTRAL
    reason_code: str = "NO_ACTION"
    updated_at: str | None = None
    zones: tuple[SMCZone, ...] = ()
    attributes: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "framework_id": self.framework_id,
            "lifecycle": self.lifecycle.value,
            "direction": self.direction.value,
            "reason_code": self.reason_code,
            "updated_at": self.updated_at,
            "zones": [zone.to_dict() for zone in self.zones],
            "attributes": dict(self.attributes),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "SMCFrameworkState":
        return cls(
            framework_id=str(value["framework_id"]),
            lifecycle=SMCLifecycle(value.get("lifecycle", "undefined")),
            direction=SMCDirection(value.get("direction", "neutral")),
            reason_code=str(value.get("reason_code", "NO_ACTION")),
            updated_at=value.get("updated_at"),
            zones=tuple(SMCZone.from_dict(item) for item in value.get("zones", ())),
            attributes=dict(value.get("attributes", {})),
        )
