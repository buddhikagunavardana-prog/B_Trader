import hashlib
import json
from dataclasses import dataclass, field
from typing import Any


def _candidate_hash(strategy_id: str, pair: str, template_type: str) -> str:
    payload = json.dumps(
        {
            "strategy_id": strategy_id,
            "pair": pair,
            "template_type": template_type,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class PortfolioCandidate:
    candidate_id: str
    strategy_id: str
    pair: str
    template_type: str
    expected_roi: float
    profit_factor: float
    drawdown: float
    walk_forward_score: float
    robustness_score: float
    risk_score: float
    allocation_weight: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        strategy_id: str,
        pair: str,
        template_type: str,
        expected_roi: float,
        profit_factor: float,
        drawdown: float,
        walk_forward_score: float,
        robustness_score: float,
        risk_score: float,
        allocation_weight: float = 0.0,
        metadata: dict | None = None,
    ):
        digest = _candidate_hash(strategy_id, pair, template_type)
        return cls(
            candidate_id=f"PORT_{digest[:12].upper()}",
            strategy_id=strategy_id,
            pair=pair,
            template_type=template_type,
            expected_roi=float(expected_roi),
            profit_factor=float(profit_factor),
            drawdown=float(drawdown),
            walk_forward_score=float(walk_forward_score),
            robustness_score=float(robustness_score),
            risk_score=float(risk_score),
            allocation_weight=float(allocation_weight),
            metadata=dict(metadata or {}),
        )

    @classmethod
    def from_robustness_row(cls, row):
        return cls.create(
            strategy_id=row["Strategy ID"],
            pair=row["Original Pair"],
            template_type=row["Template Type"],
            expected_roi=row["Original ROI %"],
            profit_factor=row["Original Profit Factor"],
            drawdown=row["Original Max Drawdown %"],
            walk_forward_score=row["Average Walk Forward Score"],
            robustness_score=row["Robustness Score"],
            risk_score=row["Overfitting Risk Score"],
            metadata={
                "source": "generated_strategy_robustness",
                "status": row.get("Status", ""),
            },
        )

    def with_allocation(self, allocation_weight: float):
        return PortfolioCandidate(
            candidate_id=self.candidate_id,
            strategy_id=self.strategy_id,
            pair=self.pair,
            template_type=self.template_type,
            expected_roi=self.expected_roi,
            profit_factor=self.profit_factor,
            drawdown=self.drawdown,
            walk_forward_score=self.walk_forward_score,
            robustness_score=self.robustness_score,
            risk_score=self.risk_score,
            allocation_weight=float(allocation_weight),
            metadata=dict(self.metadata),
        )

    def quality_score(self) -> float:
        pf_score = min(self.profit_factor / 2.0 * 100.0, 100.0)
        drawdown_score = max(0.0, 100.0 - abs(self.drawdown))
        risk_adjustment = max(0.0, 100.0 - self.risk_score)
        return round(
            self.expected_roi * 0.25
            + pf_score * 0.20
            + self.walk_forward_score * 0.20
            + self.robustness_score * 0.20
            + drawdown_score * 0.10
            + risk_adjustment * 0.05,
            2,
        )

    def to_dict(self) -> dict:
        return {
            "Candidate ID": self.candidate_id,
            "Strategy ID": self.strategy_id,
            "Pair": self.pair,
            "Template Type": self.template_type,
            "Expected ROI": self.expected_roi,
            "Profit Factor": self.profit_factor,
            "Drawdown": self.drawdown,
            "Walk Forward Score": self.walk_forward_score,
            "Robustness Score": self.robustness_score,
            "Risk Score": self.risk_score,
            "Allocation Weight": self.allocation_weight,
            "Quality Score": self.quality_score(),
            "Metadata": json.dumps(self.metadata, sort_keys=True),
        }
