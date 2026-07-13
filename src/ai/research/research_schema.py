import math
import re


class ResearchSchemaError(ValueError):
    pass


TOP_LEVEL_FIELDS = {
    "analysis_version", "run_id", "provider", "model",
    "overall_assessment", "data_quality_issues", "candidate_findings",
    "recommended_experiments", "paper_trading_recommendation",
    "confidence", "warnings",
}
CANDIDATE_FIELDS = {
    "candidate_id", "strengths", "weaknesses", "failed_gates",
    "dominant_failure", "evidence",
}
EVIDENCE_FIELDS = {"metric", "observed", "required"}
EXPERIMENT_FIELDS = {
    "priority", "title", "hypothesis", "expected_benefit",
    "overfitting_risk", "required_changes", "validation_plan",
    "do_not_change",
}
FORBIDDEN_CHANGE_TERMS = {
    "lower threshold", "relax threshold", "change threshold",
    "change readiness", "mark ready", "execute trade", "place trade",
    "edit configuration", "change configuration",
}


def _require_exact_fields(payload: dict, fields: set[str], label: str) -> None:
    if not isinstance(payload, dict):
        raise ResearchSchemaError(f"{label} must be an object")
    missing = fields.difference(payload)
    extra = set(payload).difference(fields)
    if missing or extra:
        raise ResearchSchemaError(
            f"{label} fields invalid; missing={sorted(missing)}, extra={sorted(extra)}"
        )


def _require_string_list(value, label: str) -> None:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise ResearchSchemaError(f"{label} must be a list of strings")


def _reject_narrative_numbers(values: list[str], label: str) -> None:
    if any(re.search(r"(?<![A-Za-z])[-+]?\d+(?:\.\d+)?%?", value) for value in values):
        raise ResearchSchemaError(
            f"Unsupported numeric claim in {label}; use structured evidence"
        )


def validate_research_analysis(
    payload: dict,
    context: dict,
    max_recommendations: int,
) -> dict:
    _require_exact_fields(payload, TOP_LEVEL_FIELDS, "analysis")
    if payload["analysis_version"] != "1.0":
        raise ResearchSchemaError("analysis_version must be 1.0")
    for field in ["run_id", "provider", "model", "overall_assessment"]:
        if not isinstance(payload[field], str) or not payload[field]:
            raise ResearchSchemaError(f"{field} must be a non-empty string")
    if payload["run_id"] != context["run_id"]:
        raise ResearchSchemaError("AI run_id does not match deterministic context")
    if payload["paper_trading_recommendation"] != context["paper_trading_readiness"]:
        raise ResearchSchemaError("AI cannot alter paper-trading readiness")
    confidence = payload["confidence"]
    if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
        raise ResearchSchemaError("confidence must be numeric")
    if not math.isfinite(float(confidence)) or not 0 <= float(confidence) <= 1:
        raise ResearchSchemaError("confidence must be between zero and one")

    _require_string_list(payload["data_quality_issues"], "data_quality_issues")
    _require_string_list(payload["warnings"], "warnings")
    _reject_narrative_numbers(
        [payload["overall_assessment"]]
        + payload["data_quality_issues"]
        + payload["warnings"],
        "analysis narrative",
    )

    candidates = {item["candidate_id"]: item for item in context["candidates"]}
    if not isinstance(payload["candidate_findings"], list):
        raise ResearchSchemaError("candidate_findings must be a list")
    for finding in payload["candidate_findings"]:
        _require_exact_fields(finding, CANDIDATE_FIELDS, "candidate finding")
        candidate_id = finding["candidate_id"]
        if candidate_id not in candidates:
            raise ResearchSchemaError(f"Unknown candidate evidence: {candidate_id}")
        for field in ["strengths", "weaknesses", "failed_gates"]:
            _require_string_list(finding[field], field)
            _reject_narrative_numbers(finding[field], field)
        if not isinstance(finding["dominant_failure"], str):
            raise ResearchSchemaError("dominant_failure must be a string")
        _reject_narrative_numbers([finding["dominant_failure"]], "dominant_failure")
        if not isinstance(finding["evidence"], list):
            raise ResearchSchemaError("evidence must be a list")
        for evidence in finding["evidence"]:
            _require_exact_fields(evidence, EVIDENCE_FIELDS, "evidence")
            metric = evidence["metric"]
            expected = candidates[candidate_id]["metrics"].get(metric)
            required = context["readiness_thresholds"].get(metric)
            if expected is None or required is None:
                raise ResearchSchemaError(f"Unsupported evidence metric: {metric}")
            if evidence["observed"] != expected or evidence["required"] != required:
                raise ResearchSchemaError(f"Unsupported numeric claim for {metric}")

    experiments = payload["recommended_experiments"]
    if not isinstance(experiments, list) or len(experiments) > max_recommendations:
        raise ResearchSchemaError("recommended_experiments exceeds configured limit")
    priorities = []
    for experiment in experiments:
        _require_exact_fields(experiment, EXPERIMENT_FIELDS, "experiment")
        if not isinstance(experiment["priority"], int) or experiment["priority"] < 1:
            raise ResearchSchemaError("experiment priority must be a positive integer")
        priorities.append(experiment["priority"])
        text_values = []
        for field in ["title", "hypothesis", "expected_benefit", "overfitting_risk"]:
            if not isinstance(experiment[field], str):
                raise ResearchSchemaError(f"{field} must be a string")
            text_values.append(experiment[field])
        for field in ["required_changes", "validation_plan", "do_not_change"]:
            _require_string_list(experiment[field], field)
            text_values.extend(experiment[field])
        _reject_narrative_numbers(text_values, "recommended experiment")
        combined = " ".join(text_values).lower()
        if any(term in combined for term in FORBIDDEN_CHANGE_TERMS):
            raise ResearchSchemaError("AI recommendation attempts a forbidden change")
    if len(priorities) != len(set(priorities)):
        raise ResearchSchemaError("experiment priorities must be unique")
    return payload
