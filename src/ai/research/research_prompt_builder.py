import json


def build_research_prompt(context: dict, max_recommendations: int) -> str:
    rules = [
        "Return one JSON object only.",
        "Use only the supplied deterministic evidence.",
        "Put every numeric claim in a structured evidence item.",
        "Do not alter readiness, thresholds, configuration, status, or trades.",
        "Clearly label recommendations as hypotheses.",
        f"Return at most {int(max_recommendations)} recommended experiments.",
        "The deterministic B Trader benchmark remains the source of truth.",
    ]
    output_template = {
        "analysis_version": "1.0",
        "run_id": context["run_id"],
        "provider": "provider name",
        "model": "model identifier",
        "overall_assessment": "evidence-grounded assessment without numbers",
        "data_quality_issues": [],
        "candidate_findings": [{
            "candidate_id": "exact supplied candidate identifier",
            "strengths": [],
            "weaknesses": [],
            "failed_gates": [],
            "dominant_failure": "one supplied failed gate",
            "evidence": [{
                "metric": "exact supplied metric key",
                "observed": "exact supplied numeric value",
                "required": "exact supplied threshold value",
            }],
        }],
        "recommended_experiments": [{
            "priority": 1,
            "title": "hypothesis title without numbers",
            "hypothesis": "bounded hypothesis without numbers",
            "expected_benefit": "expected benefit without numbers",
            "overfitting_risk": "risk statement without numbers",
            "required_changes": [],
            "validation_plan": [],
            "do_not_change": [],
        }],
        "paper_trading_recommendation": context["paper_trading_readiness"],
        "confidence": 0.0,
        "warnings": [],
    }
    return (
        "You are an advisory B Trader research analyst.\n"
        + "\n".join(f"- {rule}" for rule in rules)
        + "\nOUTPUT_TEMPLATE_JSON\n"
        + json.dumps(output_template, sort_keys=True, separators=(",", ":"))
        + "\nDETERMINISTIC_CONTEXT_JSON\n"
        + json.dumps(context, sort_keys=True, separators=(",", ":"))
    )
