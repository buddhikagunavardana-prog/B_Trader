import hashlib
import json
from dataclasses import dataclass, field
from typing import Any

from src.research.optimizer.optimizer_constraints import ConstraintResult


def canonical_candidate_payload(
    strategy_id: str,
    template_type: str,
    parameters: dict,
    metadata: dict | None = None,
) -> dict:
    return {
        "strategy_id": strategy_id,
        "template_type": template_type,
        "parameters": parameters,
        "metadata": metadata or {},
    }


def calculate_candidate_hash(payload: dict) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class OptimizationCandidate:
    candidate_id: str
    strategy_id: str
    template_type: str
    parameters: dict
    validation_status: str
    optimization_metadata: dict[str, Any] = field(default_factory=dict)
    candidate_hash: str = ""
    validation_reasons: list[str] = field(default_factory=list)

    @classmethod
    def create(
        cls,
        strategy_id: str,
        template_type: str,
        parameters: dict,
        validation: ConstraintResult,
        optimization_metadata: dict | None = None,
    ):
        metadata = optimization_metadata or {}
        payload = canonical_candidate_payload(
            strategy_id,
            template_type,
            parameters,
            metadata,
        )
        candidate_hash = calculate_candidate_hash(payload)

        return cls(
            candidate_id=f"OPT_{candidate_hash[:12].upper()}",
            strategy_id=strategy_id,
            template_type=template_type,
            parameters=dict(parameters),
            validation_status="VALID" if validation.is_valid else "INVALID",
            optimization_metadata=metadata,
            candidate_hash=candidate_hash,
            validation_reasons=list(validation.reasons),
        )

    def to_dict(self) -> dict:
        return {
            "Candidate ID": self.candidate_id,
            "Strategy ID": self.strategy_id,
            "Template Type": self.template_type,
            "Parameters": json.dumps(self.parameters, sort_keys=True),
            "Validation Status": self.validation_status,
            "Validation Reasons": " | ".join(self.validation_reasons),
            "Optimization Metadata": json.dumps(
                self.optimization_metadata,
                sort_keys=True,
            ),
            "Hash": self.candidate_hash,
        }
