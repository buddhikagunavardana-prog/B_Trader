import json

from src.ai.providers.base_provider import BaseProvider


class MockProvider(BaseProvider):
    def __init__(self, model: str = "mock-research-analyst-v1"):
        self._model = model
        self.call_count = 0

    @property
    def name(self) -> str:
        return "mock"

    @property
    def model(self) -> str:
        return self._model

    def generate(self, prompt: str, context: dict) -> str:
        self.call_count += 1
        if "STRATEGY_PROPOSAL_REQUEST" in prompt:
            return json.dumps({
                "proposals": [{
                    "proposal_version": "1.0",
                    "proposal_id": "AIPROP_EMA_MACD_VOLUME_001",
                    "title": "EMA MACD trend with volume selectivity",
                    "hypothesis": (
                        "Volume confirmation may suppress weak momentum entries "
                        "in the existing EMA MACD family"
                    ),
                    "strategy_family": "trend_momentum",
                    "market_scope": ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT"],
                    "entry_timeframe": "15m",
                    "confirmation_timeframes": [],
                    "entry_conditions": [
                        {
                            "indicator": "EMA",
                            "parameters": {"fast": 20, "slow": 100},
                            "operator": "cross_above"
                        },
                        {
                            "indicator": "MACD",
                            "parameters": {"fast": 12, "slow": 26, "signal": 9},
                            "operator": "above_signal"
                        }
                    ],
                    "confirmation_conditions": [
                        {
                            "indicator": "VOLUME",
                            "parameters": {"period": 20, "multiplier": 1.5},
                            "operator": "above_multiplier"
                        }
                    ],
                    "exit_mode": "fixed",
                    "risk_mode": "risk_normalized",
                    "parameter_ranges": {
                        "ema.fast": [20],
                        "ema.slow": [100],
                        "volume.multiplier": [1.5],
                        "stop_loss_pct": [1.5],
                        "take_profit_pct": [3.0]
                    },
                    "expected_market_regimes": ["TRENDING", "HIGH_VOLATILITY"],
                    "expected_benefit": "Improve entry selectivity without relaxing validation",
                    "known_risks": ["Lower trade frequency", "Volume confirmation may lag"],
                    "overfitting_risk": "Low when tested as one predeclared bounded proposal",
                    "validation_plan": [
                        "Compare with the matched EMA MACD baseline",
                        "Run unchanged funnel and robustness gates"
                    ],
                    "do_not_change": [
                        "Readiness thresholds",
                        "Final validation period",
                        "Production configuration"
                    ]
                }]
            }, sort_keys=True)
        findings = []
        for candidate in context["candidates"]:
            evidence = []
            failed_gates = list(candidate["failed_gates"])
            for gate in failed_gates[:2]:
                metric = gate["metric"]
                evidence.append({
                    "metric": metric,
                    "observed": candidate["metrics"][metric],
                    "required": context["readiness_thresholds"][metric],
                })
            findings.append({
                "candidate_id": candidate["candidate_id"],
                "strengths": ["Passed deterministic robustness review"],
                "weaknesses": [gate["reason"] for gate in failed_gates],
                "failed_gates": [gate["reason"] for gate in failed_gates],
                "dominant_failure": (
                    failed_gates[0]["reason"]
                    if failed_gates
                    else "No failed gate was supplied"
                ),
                "evidence": evidence,
            })

        experiments = [{
            "priority": 1,
            "title": "Post-cost signal selectivity experiment",
            "hypothesis": (
                "Regime-aware entry suppression may improve weak raw edge "
                "after realistic execution costs"
            ),
            "expected_benefit": "Reduce low-quality trades without relaxing gates",
            "overfitting_risk": "Moderate if variants are not predeclared",
            "required_changes": [
                "Add an isolated execution-cost research variant",
                "Add one predeclared regime-aware entry variant",
            ],
            "validation_plan": [
                "Run the unchanged progressive funnel",
                "Run unchanged robustness and walk-forward validation",
            ],
            "do_not_change": [
                "Readiness thresholds",
                "Deterministic candidate status",
                "Trade execution authority",
            ],
        }]
        payload = {
            "analysis_version": "1.0",
            "run_id": context["run_id"],
            "provider": self.name,
            "model": self.model,
            "overall_assessment": (
                "The benchmark is operationally stable but candidate edge "
                "remains below deterministic readiness requirements"
            ),
            "data_quality_issues": list(context["data_quality_issues"]),
            "candidate_findings": findings,
            "recommended_experiments": experiments,
            "paper_trading_recommendation": context["paper_trading_readiness"],
            "confidence": 0.82,
            "warnings": ["Advisory output cannot change deterministic results"],
        }
        return json.dumps(payload, sort_keys=True)
