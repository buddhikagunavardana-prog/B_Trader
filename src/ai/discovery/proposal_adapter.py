import json
from pathlib import Path

from src.ai.discovery.proposal_schema import validate_strategy_proposal
from src.ai.research.research_analyst import load_ai_research_config
from src.research.pipeline.pipeline_reporter import save_json_report


RULE_BY_INDICATOR = {
    "EMA": "ema_cross",
    "RSI": "rsi_filter",
    "MACD": "macd_confirmation",
    "VOLUME": "volume_confirmation",
    "BOLLINGER": "bollinger_reversal",
    "SUPERTREND": "supertrend_confirmation",
    "CANDLESTICK": "candlestick_confirmation",
}


def _selected_parameters(proposal: dict) -> dict:
    return {
        key: values[0]
        for key, values in proposal["parameter_ranges"].items()
    }


def _indicator_config(condition: dict, selected: dict) -> dict:
    indicator = condition["indicator"].upper()
    parameters = dict(condition["parameters"])
    prefix = indicator.lower() + "."
    for key, value in selected.items():
        if key.startswith(prefix):
            parameters[key[len(prefix):]] = value
    if indicator == "EMA":
        parameters["trend"] = parameters["slow"]
    return {"enabled": True, **parameters}


def _build_candidate_config(proposal: dict, review: dict, config: dict) -> dict:
    if proposal["confirmation_timeframes"]:
        raise ValueError(
            "Deterministic multi-timeframe adapter is not implemented"
        )
    selected = _selected_parameters(proposal)
    conditions = proposal["entry_conditions"] + proposal["confirmation_conditions"]
    indicators = {}
    entry_rules = {}
    for condition in conditions:
        indicator = condition["indicator"].upper()
        indicators[indicator.lower()] = _indicator_config(condition, selected)
        entry_rules[RULE_BY_INDICATOR[indicator]] = True

    if proposal["exit_mode"] == "atr":
        exit_rules = {
            "simulated_exit_mode": "atr_full_position",
            "atr_period": int(selected["atr_period"]),
            "atr_stop_multiplier": float(selected["atr_stop_multiplier"]),
            "atr_target_multiplier": float(selected["atr_target_multiplier"]),
        }
        indicators["atr"] = {
            "enabled": True,
            "period": int(selected["atr_period"]),
        }
    else:
        exit_rules = {
            "simulated_exit_mode": "fixed_percent_full_position",
            "stop_loss_percent": float(selected["stop_loss_pct"]),
            "take_profit_percent": float(selected["take_profit_pct"]),
        }

    if proposal["risk_mode"] == "risk_normalized":
        risk = {
            "position_sizing_mode": "risk_normalized",
            "risk_per_trade_fraction": float(
                config["proposal_risk_per_trade_fraction"]
            ),
            "max_capital_allocation_fraction": float(
                config["proposal_max_capital_allocation_fraction"]
            ),
            "leverage_allowed": False,
            "risk_per_trade": float(
                config["proposal_risk_per_trade_fraction"]
            ) * 100,
        }
    else:
        risk = {
            "position_sizing_mode": "full_allocation",
            "risk_per_trade": 2,
        }

    proposal_id = proposal["proposal_id"]
    return {
        "strategy_id": f"AI_{proposal_id}",
        "name": proposal["title"],
        "timeframe": proposal["entry_timeframe"],
        "indicators": indicators,
        "entry_rules": entry_rules,
        "exit_rules": exit_rules,
        "risk": risk,
        "enabled": False,
        "template": "ai_reviewed",
        "parameters": selected,
        "parameter_ranges": proposal["parameter_ranges"],
        "metadata": {
            "proposal_id": proposal_id,
            "market_scope": list(proposal["market_scope"]),
            "origin": "AI_REVIEWED_PROPOSAL",
            "reviewed_by": review["reviewed_by"],
            "activation_status": "RESEARCH_ONLY",
            "production_activation_allowed": False,
            "advisory_source_only": True,
        },
    }


def convert_reviewed_proposals(
    accepted_artifact_path: str | Path,
    output_path: str | Path | None = None,
    config_override: dict | None = None,
) -> dict:
    config = load_ai_research_config()
    if config_override:
        config.update(config_override)
    with open(accepted_artifact_path, "r", encoding="utf-8") as file:
        accepted = json.load(file)
    if (
        accepted.get("status") != "REVIEWED"
        or accepted.get("human_review_required") is not True
        or accepted.get("production_activation_allowed") is not False
    ):
        raise ValueError("Accepted proposal artifact is not safely review-gated")
    reviews = accepted.get("accepted_proposals", [])
    if len(reviews) != 1:
        raise ValueError("Exactly one reviewed proposal may be converted")
    review = reviews[0]
    if review.get("review_status") != "REVIEWED":
        raise ValueError("Proposal must pass explicit human review")
    if review.get("activation_status") != "RESEARCH_ONLY":
        raise ValueError("Reviewed proposal must remain research-only")
    proposal = validate_strategy_proposal(review["proposal"], config)
    candidate = _build_candidate_config(proposal, review, config)
    artifact = {
        "status": "RESEARCH_ONLY",
        "production_activation_allowed": False,
        "candidate_count": 1,
        "candidate_definitions": [candidate],
    }
    target = output_path or config["candidate_definition_output_path"]
    save_json_report(artifact, str(target))
    return artifact
