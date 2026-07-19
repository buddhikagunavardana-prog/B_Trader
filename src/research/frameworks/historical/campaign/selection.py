from __future__ import annotations

import hashlib
import json
from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Any

from src.research.frameworks.historical.campaign.research_models import (
    FrameworkOptimizationResult,
    FrameworkRankingRow,
    FrameworkResearchSummary,
    FrameworkValidationResult,
)


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        default=str,
    )


def _fingerprint(value: Any) -> str:
    return hashlib.sha256(
        _canonical_json(value).encode("utf-8")
    ).hexdigest()


def calculate_ranking_fingerprint(
    ranking_rows: Sequence[FrameworkRankingRow],
) -> str:
    """
    Return a deterministic fingerprint for the complete framework ranking.

    The fingerprint changes whenever ranking order, scores, eligibility,
    status, metrics, or rejection reasons change.
    """
    normalized_rows = []

    for row in ranking_rows:
        if not isinstance(row, FrameworkRankingRow):
            raise TypeError(
                "ranking_rows must contain only "
                "FrameworkRankingRow instances"
            )

        normalized_rows.append(row.to_dict())

    return _fingerprint(normalized_rows)


def _validate_rank_order(
    ranking_rows: Sequence[FrameworkRankingRow],
) -> None:
    seen_ranks: set[int] = set()
    seen_frameworks: set[tuple[str, str]] = set()

    previous_rank = 0

    for row in ranking_rows:
        if not isinstance(row, FrameworkRankingRow):
            raise TypeError(
                "ranking_rows must contain only "
                "FrameworkRankingRow instances"
            )

        if row.rank in seen_ranks:
            raise ValueError(
                f"duplicate framework ranking position: {row.rank}"
            )

        if row.rank <= previous_rank:
            raise ValueError(
                "ranking_rows must be ordered by strictly increasing rank"
            )

        framework_key = (
            row.framework_name,
            row.framework_version,
        )

        if framework_key in seen_frameworks:
            raise ValueError(
                "duplicate ranked framework: "
                f"{row.framework_name!r} "
                f"version {row.framework_version!r}"
            )

        seen_ranks.add(row.rank)
        seen_frameworks.add(framework_key)
        previous_rank = row.rank


def _normalized_category(value: str) -> str:
    normalized = str(value).strip()
    return normalized or "uncategorized"


def select_frameworks_for_paper_trading(
    ranking_rows: Sequence[FrameworkRankingRow],
    *,
    maximum_selected: int = 5,
    maximum_per_category: int | None = None,
    eligible_only: bool = True,
    fill_remaining: bool = True,
) -> tuple[FrameworkRankingRow, ...]:
    """
    Select a deterministic paper-trading shortlist from ranked frameworks.

    Selection order always follows the supplied ranking.

    When maximum_per_category is set, the first pass enforces category
    diversification. When fill_remaining is True, remaining shortlist slots
    may then be filled from the best skipped candidates even when that exceeds
    the category limit.

    The original ranking positions are preserved.
    """
    if maximum_selected < 0:
        raise ValueError("maximum_selected cannot be negative")

    if (
        maximum_per_category is not None
        and maximum_per_category < 1
    ):
        raise ValueError(
            "maximum_per_category must be at least 1 or None"
        )

    ordered_rows = tuple(ranking_rows)
    _validate_rank_order(ordered_rows)

    if maximum_selected == 0 or not ordered_rows:
        return ()

    candidates = tuple(
        row
        for row in ordered_rows
        if (
            not eligible_only
            or row.eligible_for_paper_trading
        )
    )

    if maximum_per_category is None:
        return candidates[:maximum_selected]

    selected: list[FrameworkRankingRow] = []
    skipped: list[FrameworkRankingRow] = []
    category_counts: Counter[str] = Counter()

    for row in candidates:
        if len(selected) >= maximum_selected:
            break

        category = _normalized_category(row.category)

        if category_counts[category] >= maximum_per_category:
            skipped.append(row)
            continue

        selected.append(row)
        category_counts[category] += 1

    if fill_remaining and len(selected) < maximum_selected:
        selected_keys = {
            (
                row.framework_name,
                row.framework_version,
                row.selected_configuration_fingerprint,
            )
            for row in selected
        }

        remaining_candidates = [
            row
            for row in candidates
            if (
                row.framework_name,
                row.framework_version,
                row.selected_configuration_fingerprint,
            )
            not in selected_keys
        ]

        for row in remaining_candidates:
            if len(selected) >= maximum_selected:
                break

            selected.append(row)

    selected.sort(key=lambda row: row.rank)

    return tuple(selected)


def _optimization_completed_count(
    results: Sequence[FrameworkOptimizationResult],
) -> int:
    count = 0

    for result in results:
        if not isinstance(result, FrameworkOptimizationResult):
            raise TypeError(
                "optimization_results must contain only "
                "FrameworkOptimizationResult instances"
            )

        if result.status == "completed":
            count += 1

    return count


def _validation_completed_count(
    results: Sequence[FrameworkValidationResult],
) -> int:
    count = 0

    for result in results:
        if not isinstance(result, FrameworkValidationResult):
            raise TypeError(
                "validation_results must contain only "
                "FrameworkValidationResult instances"
            )

        if result.status == "completed":
            count += 1

    return count


def _failed_framework_count(
    ranking_rows: Sequence[FrameworkRankingRow],
) -> int:
    return sum(
        1
        for row in ranking_rows
        if row.status == "REJECTED"
    )


def _eligible_framework_count(
    ranking_rows: Sequence[FrameworkRankingRow],
) -> int:
    return sum(
        1
        for row in ranking_rows
        if row.eligible_for_paper_trading
    )


def _selection_warnings(
    *,
    ranking_rows: Sequence[FrameworkRankingRow],
    selected_rows: Sequence[FrameworkRankingRow],
    maximum_selected: int,
    warnings: Sequence[str],
) -> tuple[str, ...]:
    normalized: list[str] = []

    for warning in warnings:
        text = str(warning).strip()
        if text and text not in normalized:
            normalized.append(text)

    if not ranking_rows:
        normalized.append(
            "Framework ranking is empty; no framework was selected."
        )

    eligible_count = _eligible_framework_count(ranking_rows)

    if ranking_rows and eligible_count == 0:
        normalized.append(
            "No framework passed the paper-trading eligibility gate."
        )

    if (
        maximum_selected > 0
        and eligible_count > 0
        and len(selected_rows) < min(
            maximum_selected,
            eligible_count,
        )
    ):
        normalized.append(
            "The shortlist contains fewer frameworks than the "
            "available eligible candidate count."
        )

    category_counts = Counter(
        _normalized_category(row.category)
        for row in selected_rows
    )

    if selected_rows and len(category_counts) == 1:
        normalized.append(
            "All selected frameworks belong to the same category."
        )

    return tuple(dict.fromkeys(normalized))


def build_framework_research_summary(
    *,
    campaign_id: str,
    configuration_fingerprint: str,
    ranking_rows: Sequence[FrameworkRankingRow],
    optimization_results: Sequence[FrameworkOptimizationResult],
    validation_results: Sequence[FrameworkValidationResult],
    maximum_selected: int = 5,
    maximum_per_category: int | None = None,
    fill_remaining: bool = True,
    warnings: Sequence[str] = (),
    diagnostics: Mapping[str, Any] | None = None,
) -> FrameworkResearchSummary:
    """
    Select the paper-trading shortlist and build the campaign summary.

    Only frameworks that passed the ranking eligibility gate may enter the
    final shortlist.
    """
    normalized_campaign_id = str(campaign_id).strip()
    normalized_configuration_fingerprint = str(
        configuration_fingerprint
    ).strip()

    if not normalized_campaign_id:
        raise ValueError("campaign_id must be a non-empty string")

    if not normalized_configuration_fingerprint:
        raise ValueError(
            "configuration_fingerprint must be a non-empty string"
        )

    ranking = tuple(ranking_rows)
    optimization = tuple(optimization_results)
    validation = tuple(validation_results)

    _validate_rank_order(ranking)

    selected_rows = select_frameworks_for_paper_trading(
        ranking,
        maximum_selected=maximum_selected,
        maximum_per_category=maximum_per_category,
        eligible_only=True,
        fill_remaining=fill_remaining,
    )

    ranking_fingerprint = calculate_ranking_fingerprint(ranking)

    summary_warnings = _selection_warnings(
        ranking_rows=ranking,
        selected_rows=selected_rows,
        maximum_selected=maximum_selected,
        warnings=warnings,
    )

    category_counts = Counter(
        _normalized_category(row.category)
        for row in selected_rows
    )

    summary_diagnostics: dict[str, Any] = {
        "maximum_selected": maximum_selected,
        "maximum_per_category": maximum_per_category,
        "fill_remaining": fill_remaining,
        "ranking_row_count": len(ranking),
        "selected_categories": dict(
            sorted(category_counts.items())
        ),
        "paper_trading_ready_frameworks": [
            row.framework_name
            for row in selected_rows
        ],
    }

    if diagnostics:
        for key in sorted(diagnostics):
            summary_diagnostics[str(key)] = diagnostics[key]

    return FrameworkResearchSummary(
        campaign_id=normalized_campaign_id,
        configuration_fingerprint=(
            normalized_configuration_fingerprint
        ),
        ranking_fingerprint=ranking_fingerprint,
        framework_count=len(ranking),
        optimization_completed_count=(
            _optimization_completed_count(optimization)
        ),
        validation_completed_count=(
            _validation_completed_count(validation)
        ),
        failed_framework_count=_failed_framework_count(ranking),
        eligible_framework_count=(
            _eligible_framework_count(ranking)
        ),
        selected_framework_count=len(selected_rows),
        top_frameworks=selected_rows,
        warnings=summary_warnings,
        diagnostics=summary_diagnostics,
    )