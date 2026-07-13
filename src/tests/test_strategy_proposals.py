import copy
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from src.ai.discovery.proposal_adapter import convert_reviewed_proposals
from src.ai.discovery.proposal_pipeline import (
    generate_strategy_proposals,
    review_strategy_proposal,
)
from src.ai.discovery.proposal_experiment import _matched_baseline
from src.ai.discovery.proposal_schema import (
    ProposalValidationError,
    validate_strategy_proposal,
)
from src.ai.providers.mock_provider import MockProvider
from src.ai.research.research_analyst import load_ai_research_config
from src.research.benchmark.benchmark_context import build_benchmark_context
from src.strategies.strategy_factory import create_strategy_from_json_config


def _proposal():
    response = MockProvider().generate("STRATEGY_PROPOSAL_REQUEST", {})
    return json.loads(response)["proposals"][0]


def _digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class StaticProposalProvider:
    name = "mock"
    model = "static-proposal-test"

    def __init__(self, proposals):
        self.proposals = proposals
        self.call_count = 0

    def generate(self, prompt, context):
        self.call_count += 1
        return json.dumps({"proposals": self.proposals})


def test_valid_proposal_accepted_and_mock_is_deterministic():
    config = load_ai_research_config()
    proposal = _proposal()
    validated = validate_strategy_proposal(proposal, config)
    assert validated == proposal

    first = generate_strategy_proposals(
        {"enable_strategy_proposals": True},
        provider=MockProvider(),
        write_output=False,
    )
    second = generate_strategy_proposals(
        {"enable_strategy_proposals": True},
        provider=MockProvider(),
        write_output=False,
    )
    assert first == second
    assert len(first["proposals"]) == 1
    assert first["proposals"][0]["review_status"] == "PROPOSED"
    assert first["proposals"][0]["activation_status"] == "INACTIVE"


def test_malformed_unsupported_and_future_data_proposals_rejected():
    config = load_ai_research_config()
    malformed = _proposal()
    malformed.pop("hypothesis")
    try:
        validate_strategy_proposal(malformed, config)
    except ProposalValidationError as error:
        assert "fields invalid" in str(error)
    else:
        raise AssertionError("Malformed proposal was accepted")

    malformed_conditions = _proposal()
    malformed_conditions["entry_conditions"] = {"indicator": "EMA"}
    try:
        validate_strategy_proposal(malformed_conditions, config)
    except ProposalValidationError as error:
        assert "conditions must be lists" in str(error)
    else:
        raise AssertionError("Malformed condition collection was accepted")

    unsupported = _proposal()
    unsupported["entry_conditions"][0]["indicator"] = "ADX"
    try:
        validate_strategy_proposal(unsupported, config)
    except ProposalValidationError as error:
        assert "Unsupported indicator" in str(error)
    else:
        raise AssertionError("Unsupported indicator was accepted")

    future = _proposal()
    future["hypothesis"] = "Use next candle close to confirm momentum"
    try:
        validate_strategy_proposal(future, config)
    except ProposalValidationError as error:
        assert "forbidden" in str(error)
    else:
        raise AssertionError("Future-data proposal was accepted")


def test_duplicate_and_excessive_search_space_rejected():
    duplicate = _proposal()
    duplicate["confirmation_conditions"] = []
    duplicate["parameter_ranges"].pop("volume.multiplier")
    provider = StaticProposalProvider([duplicate])
    result = generate_strategy_proposals(
        {"enable_strategy_proposals": True},
        provider=provider,
        write_output=False,
    )
    assert result["proposals"] == []
    assert "already exists" in result["rejected_proposals"][0]["reason"]

    excessive = _proposal()
    excessive["parameter_ranges"]["stop_loss_pct"] = [1, 1.5, 2, 2.5, 3]
    excessive["parameter_ranges"]["take_profit_pct"] = [2, 3, 4, 5]
    provider = StaticProposalProvider([excessive])
    result = generate_strategy_proposals(
        {"enable_strategy_proposals": True},
        provider=provider,
        write_output=False,
    )
    assert result["proposals"] == []
    assert "search space" in result["rejected_proposals"][0]["reason"]


def test_human_review_gate_and_deterministic_conversion():
    proposed = generate_strategy_proposals(
        {"enable_strategy_proposals": True},
        provider=MockProvider(),
        write_output=False,
    )
    with TemporaryDirectory() as directory:
        proposed_path = Path(directory) / "proposed.json"
        reviewed_path = Path(directory) / "reviewed.json"
        candidate_path = Path(directory) / "candidates.json"
        proposed_path.write_text(json.dumps(proposed), encoding="utf-8")

        try:
            convert_reviewed_proposals(proposed_path, candidate_path)
        except ValueError as error:
            assert "review-gated" in str(error).lower()
        else:
            raise AssertionError("PROPOSED strategy bypassed review gate")

        try:
            review_strategy_proposal(
                proposed,
                proposed["proposals"][0]["proposal"]["proposal_id"],
                "",
                reviewed_path,
            )
        except ValueError as error:
            assert "reviewer" in str(error).lower()
        else:
            raise AssertionError("Anonymous review was accepted")

        unsafe_artifact = dict(proposed)
        unsafe_artifact["advisory_only"] = False
        try:
            review_strategy_proposal(
                unsafe_artifact,
                proposed["proposals"][0]["proposal"]["proposal_id"],
                "USER_AUTHORIZED_PHASE_22_1",
                reviewed_path,
            )
        except ValueError as error:
            assert "human-review-gated" in str(error)
        else:
            raise AssertionError("Non-advisory proposal artifact was accepted")

        reviewed = review_strategy_proposal(
            proposed,
            proposed["proposals"][0]["proposal"]["proposal_id"],
            "USER_AUTHORIZED_PHASE_22_1",
            reviewed_path,
        )
        unsafe_review = dict(reviewed)
        unsafe_review["production_activation_allowed"] = True
        reviewed_path.write_text(json.dumps(unsafe_review), encoding="utf-8")
        try:
            convert_reviewed_proposals(reviewed_path, candidate_path)
        except ValueError as error:
            assert "safely review-gated" in str(error)
        else:
            raise AssertionError("Production-enabled review artifact was converted")
        reviewed_path.write_text(json.dumps(reviewed), encoding="utf-8")
        converted = convert_reviewed_proposals(reviewed_path, candidate_path)
        assert reviewed["production_activation_allowed"] is False
        assert converted["status"] == "RESEARCH_ONLY"
        candidate = converted["candidate_definitions"][0]
        assert candidate["enabled"] is False
        assert candidate["metadata"]["production_activation_allowed"] is False
        assert candidate["risk"]["position_sizing_mode"] == "risk_normalized"
        assert set(candidate["indicators"]) == {"ema", "macd", "volume"}
        strategy = create_strategy_from_json_config(candidate)
        assert strategy.strategy_id.startswith("AI_AIPROP_")
        baseline = _matched_baseline(candidate)
        assert "volume" not in baseline["indicators"]
        assert "volume_confirmation" not in baseline["entry_rules"]
        assert baseline["risk"] == candidate["risk"]
        assert baseline["exit_rules"] == candidate["exit_rules"]
        assert baseline["indicators"]["ema"] == candidate["indicators"]["ema"]
        assert baseline["indicators"]["macd"] == candidate["indicators"]["macd"]


def test_disabled_mode_has_zero_calls_and_baseline_plan_unchanged():
    provider = StaticProposalProvider([_proposal()])
    tracked = [
        "reports/final_benchmark_summary.json",
        "reports/final_benchmark_shortlist.json",
        "reports/final_benchmark_ranking.csv",
    ]
    before = {path: _digest(path) for path in tracked}
    result = generate_strategy_proposals(provider=provider, write_output=False)
    assert result["status"] == "DISABLED"
    assert provider.call_count == 0
    assert before == {path: _digest(path) for path in tracked}

    benchmark = build_benchmark_context({"enabled": True})
    override = benchmark.to_orchestrator_override()
    assert len(override["enabled_stages"]) == 15
    assert "ai_research_review" not in override["enabled_stages"]


def test_proposal_cannot_mutate_thresholds_or_leak_secrets():
    config = load_ai_research_config()
    threshold = _proposal()
    threshold["do_not_change"] = ["Lower threshold for acceptance"]
    try:
        validate_strategy_proposal(threshold, config)
    except ProposalValidationError as error:
        assert "forbidden" in str(error)
    else:
        raise AssertionError("Threshold mutation was accepted")

    proposal = _proposal()
    serialized = json.dumps(proposal)
    assert "GEMINI_API_KEY" not in serialized
    assert "AIza" not in serialized
    assert "PAPER_TRADING_READY" not in serialized


if __name__ == "__main__":
    test_valid_proposal_accepted_and_mock_is_deterministic()
    test_malformed_unsupported_and_future_data_proposals_rejected()
    test_duplicate_and_excessive_search_space_rejected()
    test_human_review_gate_and_deterministic_conversion()
    test_disabled_mode_has_zero_calls_and_baseline_plan_unchanged()
    test_proposal_cannot_mutate_thresholds_or_leak_secrets()
    print("test_strategy_proposals passed")
