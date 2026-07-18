from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

import pandas as pd
from math import isfinite

from src.trading_frameworks.base import BaseTradingFramework
from src.trading_frameworks.models import FrameworkContext, FrameworkDecision
from src.trading_frameworks.registry import VALID_CATEGORIES, TradingFrameworkRegistry, trading_framework_registry
from src.trading_frameworks.utilities.dependencies import resolve_indicator_dependencies


class ValidationSeverity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    severity: ValidationSeverity
    message: str
    framework: str | None = None


@dataclass(frozen=True)
class ValidationResult:
    issues: tuple[ValidationIssue, ...]

    @property
    def valid(self) -> bool:
        return not any(issue.severity is ValidationSeverity.ERROR for issue in self.issues)

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "issues": [
                {"code": i.code, "severity": i.severity.value, "message": i.message, "framework": i.framework}
                for i in self.issues
            ],
        }


def validate_registry(registry: TradingFrameworkRegistry = trading_framework_registry) -> ValidationResult:
    issues: list[ValidationIssue] = []
    for name in registry.list_names():
        framework_class = registry.resolve(name)
        schema = framework_class.schema
        metadata = schema.metadata
        if metadata.category not in VALID_CATEGORIES:
            issues.append(ValidationIssue("invalid_category", ValidationSeverity.ERROR, metadata.category, name))
        required_metadata = {
            "display_name": metadata.display_name,
            "description": metadata.description,
            "version": metadata.version,
            "attribution": metadata.attribution,
            "reference_notes": metadata.reference_notes,
        }
        for field, value in required_metadata.items():
            if not str(value).strip():
                issues.append(ValidationIssue("incomplete_metadata", ValidationSeverity.ERROR, f"Missing {field}.", name))
        if not metadata.supported_markets or not metadata.supported_directions:
            issues.append(ValidationIssue("unsupported_scope", ValidationSeverity.ERROR, "Market or direction support is empty.", name))
        if set(metadata.timeframe_roles) != set(schema.required_columns_by_role):
            issues.append(ValidationIssue("role_schema_mismatch", ValidationSeverity.ERROR, "Role and column schemas differ.", name))
        try:
            resolve_indicator_dependencies(metadata.required_indicators)
        except (KeyError, ValueError) as error:
            issues.append(ValidationIssue("unresolved_indicator", ValidationSeverity.ERROR, str(error), name))
        try:
            framework_class()
        except Exception as error:
            issues.append(ValidationIssue("invalid_defaults", ValidationSeverity.ERROR, str(error), name))
        if not all(item.description.strip() for item in schema.parameters):
            issues.append(ValidationIssue("undocumented_parameter", ValidationSeverity.ERROR, "A parameter lacks documentation.", name))
        parameter_names = [item.name for item in schema.parameters]
        if len(parameter_names) != len(set(parameter_names)):
            issues.append(ValidationIssue("duplicate_parameter", ValidationSeverity.ERROR, "Parameter names are not unique.", name))
    return ValidationResult(tuple(issues))


def validate_runtime(
    framework: BaseTradingFramework,
    context: FrameworkContext,
    timestamp: pd.Timestamp | str | None = None,
) -> ValidationResult:
    snapshots = {role: frame.copy(deep=True) for role, frame in context.frames.items()}
    issues: list[ValidationIssue] = []
    name = framework.metadata.name
    try:
        first = framework.execute(context, timestamp)
        second = framework.execute(context, timestamp)
        if not isinstance(first, FrameworkDecision):
            issues.append(ValidationIssue("invalid_output", ValidationSeverity.ERROR, "Output is not FrameworkDecision.", name))
        elif first.to_dict() != second.to_dict():
            issues.append(ValidationIssue("nondeterministic", ValidationSeverity.ERROR, "Repeated decisions differ.", name))
        elif not _finite_decision(first.to_dict()):
            issues.append(ValidationIssue("nonfinite_output", ValidationSeverity.ERROR, "Decision contains a non-finite number.", name))
    except Exception as error:
        issues.append(ValidationIssue("execution_error", ValidationSeverity.ERROR, str(error), name))
    for role, before in snapshots.items():
        try:
            pd.testing.assert_frame_equal(context.frames[role], before, check_exact=True)
        except AssertionError:
            issues.append(ValidationIssue("input_mutation", ValidationSeverity.ERROR, f"Role '{role}' was mutated.", name))
    return ValidationResult(tuple(issues))


def _finite_decision(value: Any) -> bool:
    if isinstance(value, dict):
        return all(_finite_decision(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return all(_finite_decision(item) for item in value)
    if isinstance(value, float):
        return isfinite(value)
    return True


def validate_causality(
    framework: BaseTradingFramework,
    context: FrameworkContext,
    cutoff: pd.Timestamp | str,
) -> ValidationResult:
    timestamp = pd.Timestamp(cutoff)
    before = framework.execute(context, timestamp).to_dict()
    changed = {role: frame.copy(deep=True) for role, frame in context.frames.items()}
    for frame in changed.values():
        future = frame.index > timestamp
        numeric = list(frame.select_dtypes(include="number").columns)
        if numeric:
            frame.loc[future, numeric] = frame.loc[future, numeric] + 1_000_000.0
    after = framework.execute(FrameworkContext(changed, context.current_position, context.symbol), timestamp).to_dict()
    if before != after:
        return ValidationResult((ValidationIssue("causality_failure", ValidationSeverity.ERROR, "Future rows changed an earlier decision.", framework.metadata.name),))
    return ValidationResult(())
