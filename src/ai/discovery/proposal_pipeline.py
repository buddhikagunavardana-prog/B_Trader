import json
from pathlib import Path

from src.ai.discovery.proposal_prompt_builder import build_proposal_prompt
from src.ai.discovery.proposal_schema import (
    ProposalValidationError,
    estimate_search_space,
    validate_strategy_proposal,
)
from src.ai.providers.gemini_provider import GeminiProvider
from src.ai.providers.mock_provider import MockProvider
from src.ai.research.research_analyst import load_ai_research_config
from src.ai.research.research_context_builder import build_research_context
from src.research.pipeline.pipeline_reporter import save_json_report
from src.strategies.json_strategy_loader import load_enabled_json_strategies
from src.strategies.parameter_generator import ParameterGenerator


def _provider(config: dict):
    if config["provider"] == "mock":
        return MockProvider()
    if config["provider"] == "gemini":
        return GeminiProvider(
            config["model"], config["timeout_seconds"], config["retry_count"]
        )
    raise ValueError(f"Unsupported AI provider: {config['provider']}")


def _indicator_signature_from_config(strategy: dict) -> frozenset[str]:
    return frozenset(
        name.upper()
        for name, settings in strategy.get("indicators", {}).items()
        if settings.get("enabled", True)
        and name.upper() in {
            "EMA", "RSI", "MACD", "VOLUME", "BOLLINGER",
            "SUPERTREND", "CANDLESTICK",
        }
    )


def _proposal_signature(proposal: dict) -> frozenset[str]:
    conditions = proposal["entry_conditions"] + proposal["confirmation_conditions"]
    return frozenset(item["indicator"].upper() for item in conditions)


def existing_strategy_signatures() -> set[frozenset[str]]:
    signatures = {
        _indicator_signature_from_config(config)
        for config in load_enabled_json_strategies()
    }
    signatures.update(
        _indicator_signature_from_config(candidate["config"])
        for candidate in ParameterGenerator().generate_candidates()
    )
    return {signature for signature in signatures if signature}


def _duplicate_reason(
    proposal: dict,
    existing_signatures: set[frozenset[str]],
    accepted_signatures: set[frozenset[str]],
) -> str | None:
    signature = _proposal_signature(proposal)
    if signature in existing_signatures or signature in accepted_signatures:
        return "Exact strategy-indicator combination already exists"
    for existing in existing_signatures | accepted_signatures:
        similarity = len(signature & existing) / len(signature | existing)
        if similarity >= 0.80:
            return "Near-duplicate strategy-indicator combination already exists"
    return None


def generate_strategy_proposals(
    config_override: dict | None = None,
    provider=None,
    write_output: bool = True,
) -> dict:
    config = load_ai_research_config()
    if config_override:
        config.update(config_override)
    if not config["enable_strategy_proposals"]:
        return {"status": "DISABLED", "provider_called": False, "proposals": []}
    context = build_research_context(
        config["input_report_paths"], config["max_candidates"]
    )
    prompt = build_proposal_prompt(context, config)
    provider = provider or _provider(config)
    try:
        response = json.loads(provider.generate(prompt, context))
    except (TypeError, json.JSONDecodeError) as error:
        raise ProposalValidationError("Provider returned malformed proposal JSON") from error
    if not isinstance(response, dict) or set(response) != {"proposals"}:
        raise ProposalValidationError("Proposal response must contain only proposals")
    proposals = response["proposals"]
    if not isinstance(proposals, list):
        raise ProposalValidationError("proposals must be a list")
    if len(proposals) > int(config["max_strategy_proposals"]):
        raise ProposalValidationError("Provider exceeded max_strategy_proposals")

    existing = existing_strategy_signatures()
    accepted_signatures = set()
    proposed = []
    rejected = []
    seen_ids = set()
    for proposal in proposals:
        proposal_id = proposal.get("proposal_id", "UNKNOWN") if isinstance(proposal, dict) else "UNKNOWN"
        try:
            normalized = validate_strategy_proposal(proposal, config)
            if normalized["proposal_id"] in seen_ids:
                raise ProposalValidationError("Duplicate proposal_id")
            reason = _duplicate_reason(normalized, existing, accepted_signatures)
            if reason:
                raise ProposalValidationError(reason)
            signature = _proposal_signature(normalized)
            seen_ids.add(normalized["proposal_id"])
            accepted_signatures.add(signature)
            proposed.append({
                "review_status": "PROPOSED",
                "activation_status": "INACTIVE",
                "estimated_search_space": estimate_search_space(
                    normalized["parameter_ranges"]
                ),
                "proposal": normalized,
            })
        except (ProposalValidationError, KeyError, TypeError, ValueError) as error:
            rejected.append({"proposal_id": proposal_id, "reason": str(error)})
    artifact = {
        "status": "COMPLETED",
        "run_id": context["run_id"],
        "provider": provider.name,
        "model": provider.model,
        "advisory_only": True,
        "human_review_required": bool(
            config["require_human_review_before_activation"]
        ),
        "proposals": proposed,
        "rejected_proposals": rejected,
    }
    if write_output:
        save_json_report(artifact, config["proposal_output_path"])
    return artifact


def review_strategy_proposal(
    proposal_artifact: dict,
    proposal_id: str,
    reviewed_by: str,
    output_path: str | Path,
) -> dict:
    if not reviewed_by.strip():
        raise ValueError("Human reviewer identity is required")
    if proposal_artifact.get("advisory_only") is not True or proposal_artifact.get(
        "human_review_required"
    ) is not True:
        raise ValueError("Proposal artifact is not human-review-gated advisory output")
    matches = [
        item for item in proposal_artifact.get("proposals", [])
        if item.get("proposal", {}).get("proposal_id") == proposal_id
        and item.get("review_status") == "PROPOSED"
    ]
    if len(matches) != 1:
        raise ValueError("Exactly one PROPOSED strategy must be selected for review")
    accepted = {
        **matches[0],
        "review_status": "REVIEWED",
        "activation_status": "RESEARCH_ONLY",
        "reviewed_by": reviewed_by,
        "review_basis": "Explicit Phase 22.1 controlled-research authorization",
    }
    artifact = {
        "status": "REVIEWED",
        "human_review_required": True,
        "production_activation_allowed": False,
        "accepted_proposals": [accepted],
    }
    save_json_report(artifact, str(output_path))
    return artifact
