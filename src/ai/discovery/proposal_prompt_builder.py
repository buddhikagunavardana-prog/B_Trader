import json


def build_proposal_prompt(context: dict, config: dict) -> str:
    schema = {
        "proposals": [{
            "proposal_version": "1.0",
            "proposal_id": "STABLE_UPPERCASE_ID",
            "title": "text without unsupported numerical claims",
            "hypothesis": "testable hypothesis using supplied evidence only",
            "strategy_family": "descriptive family",
            "market_scope": ["allowed symbol"],
            "entry_timeframe": "allowed timeframe",
            "confirmation_timeframes": [],
            "entry_conditions": [{
                "indicator": "allowed indicator",
                "parameters": {},
                "operator": "supported operator",
            }],
            "confirmation_conditions": [],
            "exit_mode": "fixed",
            "risk_mode": "risk_normalized",
            "parameter_ranges": {
                "stop_loss_pct": [1.5],
                "take_profit_pct": [3.0],
            },
            "expected_market_regimes": [],
            "expected_benefit": "bounded expectation",
            "known_risks": [],
            "overfitting_risk": "explicit risk",
            "validation_plan": [],
            "do_not_change": [],
        }]
    }
    constraints = {
        "max_strategy_proposals": config["max_strategy_proposals"],
        "max_indicators_per_strategy": config["max_indicators_per_strategy"],
        "max_parameter_combinations_per_proposal": config[
            "max_parameter_combinations_per_proposal"
        ],
        "allowed_indicators": config["allowed_indicators"],
        "allowed_timeframes": config["allowed_timeframes"],
        "allowed_market_scope": config["allowed_market_scope"],
        "allow_multi_timeframe_confirmation": config[
            "allow_multi_timeframe_confirmation"
        ],
    }
    return (
        "STRATEGY_PROPOSAL_REQUEST\n"
        "Return JSON only. Proposals are advisory and cannot enter production.\n"
        "Use only supplied evidence. Do not cite final validation outcomes, "
        "relax thresholds, execute trades, or modify configuration.\n"
        "OUTPUT_SCHEMA_JSON\n"
        + json.dumps(schema, sort_keys=True, separators=(",", ":"))
        + "\nCONSTRAINTS_JSON\n"
        + json.dumps(constraints, sort_keys=True, separators=(",", ":"))
        + "\nRESEARCH_CONTEXT_JSON\n"
        + json.dumps(context, sort_keys=True, separators=(",", ":"))
    )
