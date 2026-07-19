from __future__ import annotations

import unittest

from src.research.frameworks.historical.campaign.research_models import (
    FrameworkOptimizationResult,
    FrameworkRankingRow,
    FrameworkValidationResult,
)
from src.research.frameworks.historical.campaign.selection import (
    build_framework_research_summary,
    calculate_ranking_fingerprint,
    select_frameworks_for_paper_trading,
)


def build_ranking_row(
    *,
    rank: int,
    framework_name: str,
    category: str,
    final_score: float,
    eligible: bool = True,
    status: str | None = None,
) -> FrameworkRankingRow:
    resolved_status = status or (
        "PAPER_TRADING_READY"
        if eligible
        else "REJECTED"
    )

    return FrameworkRankingRow(
        rank=rank,
        framework_name=framework_name,
        category=category,
        framework_version="1.0.0",
        selected_configuration_fingerprint=(
            f"cfg_{framework_name}"
        ),
        optimization_score=final_score,
        validation_score=final_score,
        robustness_score=final_score,
        final_score=final_score,
        validation_roi_pct=12.0,
        validation_win_rate_pct=55.0,
        validation_profit_factor=1.35,
        validation_max_drawdown_pct=10.0,
        validation_expectancy=0.12,
        validation_total_trades=100,
        validation_wins=55,
        validation_losses=45,
        status=resolved_status,
        eligible_for_paper_trading=eligible,
        rejection_reasons=(
            ()
            if eligible
            else ("Eligibility gate failed",)
        ),
    )


def build_optimization_result(
    row: FrameworkRankingRow,
    *,
    status: str = "completed",
) -> FrameworkOptimizationResult:
    return FrameworkOptimizationResult(
        framework_name=row.framework_name,
        framework_version=row.framework_version,
        status=status,
        selected_configuration={
            "period": 20,
        },
        selected_configuration_fingerprint=(
            row.selected_configuration_fingerprint
        ),
        optimization_score=row.optimization_score,
        roi_pct=12.0,
        win_rate_pct=55.0,
        profit_factor=1.35,
        max_drawdown_pct=10.0,
        expectancy=0.12,
        total_trades=100,
        wins=55,
        losses=45,
        candidate_count=10,
    )


def build_validation_result(
    row: FrameworkRankingRow,
    *,
    status: str = "completed",
) -> FrameworkValidationResult:
    return FrameworkValidationResult(
        framework_name=row.framework_name,
        framework_version=row.framework_version,
        status=status,
        configuration_fingerprint=(
            row.selected_configuration_fingerprint
        ),
        validation_score=row.validation_score,
        roi_pct=row.validation_roi_pct,
        win_rate_pct=row.validation_win_rate_pct,
        profit_factor=row.validation_profit_factor,
        max_drawdown_pct=(
            row.validation_max_drawdown_pct
        ),
        expectancy=row.validation_expectancy,
        total_trades=row.validation_total_trades,
        wins=row.validation_wins,
        losses=row.validation_losses,
        fold_count=3,
        completed_fold_count=(
            3
            if status == "completed"
            else 0
        ),
    )


class FrameworkCampaignSelectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.ranking_rows = (
            build_ranking_row(
                rank=1,
                framework_name="ema_trend",
                category="trend",
                final_score=84.0,
            ),
            build_ranking_row(
                rank=2,
                framework_name="supertrend",
                category="trend",
                final_score=82.0,
            ),
            build_ranking_row(
                rank=3,
                framework_name="bollinger_reversal",
                category="mean_reversion",
                final_score=80.0,
            ),
            build_ranking_row(
                rank=4,
                framework_name="volume_breakout",
                category="breakout",
                final_score=78.0,
            ),
            build_ranking_row(
                rank=5,
                framework_name="weak_framework",
                category="trend",
                final_score=40.0,
                eligible=False,
            ),
        )

    def test_selects_only_eligible_frameworks(self) -> None:
        selected = select_frameworks_for_paper_trading(
            self.ranking_rows,
            maximum_selected=10,
        )

        selected_names = tuple(
            row.framework_name
            for row in selected
        )

        self.assertEqual(len(selected), 4)
        self.assertNotIn(
            "weak_framework",
            selected_names,
        )

    def test_maximum_selected_is_enforced(self) -> None:
        selected = select_frameworks_for_paper_trading(
            self.ranking_rows,
            maximum_selected=2,
        )

        self.assertEqual(len(selected), 2)
        self.assertEqual(
            tuple(row.rank for row in selected),
            (1, 2),
        )

    def test_category_limit_diversifies_selection(self) -> None:
        selected = select_frameworks_for_paper_trading(
            self.ranking_rows,
            maximum_selected=3,
            maximum_per_category=1,
            fill_remaining=False,
        )

        self.assertEqual(
            tuple(
                row.framework_name
                for row in selected
            ),
            (
                "ema_trend",
                "bollinger_reversal",
                "volume_breakout",
            ),
        )

    def test_fill_remaining_uses_best_skipped_candidate(
        self,
    ) -> None:
        selected = select_frameworks_for_paper_trading(
            self.ranking_rows,
            maximum_selected=4,
            maximum_per_category=1,
            fill_remaining=True,
        )

        self.assertEqual(
            tuple(
                row.framework_name
                for row in selected
            ),
            (
                "ema_trend",
                "supertrend",
                "bollinger_reversal",
                "volume_breakout",
            ),
        )

    def test_eligible_only_false_can_include_rejected_rows(
        self,
    ) -> None:
        selected = select_frameworks_for_paper_trading(
            self.ranking_rows,
            maximum_selected=5,
            eligible_only=False,
        )

        self.assertEqual(len(selected), 5)
        self.assertEqual(
            selected[-1].framework_name,
            "weak_framework",
        )

    def test_zero_maximum_returns_empty_tuple(self) -> None:
        selected = select_frameworks_for_paper_trading(
            self.ranking_rows,
            maximum_selected=0,
        )

        self.assertEqual(selected, ())

    def test_negative_maximum_is_rejected(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "maximum_selected cannot be negative",
        ):
            select_frameworks_for_paper_trading(
                self.ranking_rows,
                maximum_selected=-1,
            )

    def test_invalid_category_limit_is_rejected(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "maximum_per_category must be at least 1",
        ):
            select_frameworks_for_paper_trading(
                self.ranking_rows,
                maximum_per_category=0,
            )

    def test_duplicate_rank_is_rejected(self) -> None:
        duplicate_rank_rows = (
            self.ranking_rows[0],
            build_ranking_row(
                rank=1,
                framework_name="duplicate_framework",
                category="trend",
                final_score=70.0,
            ),
        )

        with self.assertRaisesRegex(
            ValueError,
            "duplicate framework ranking position",
        ):
            select_frameworks_for_paper_trading(
                duplicate_rank_rows
            )

    def test_ranking_fingerprint_is_deterministic(self) -> None:
        first = calculate_ranking_fingerprint(
            self.ranking_rows
        )
        second = calculate_ranking_fingerprint(
            self.ranking_rows
        )

        self.assertEqual(first, second)
        self.assertEqual(len(first), 64)

    def test_ranking_fingerprint_changes_with_order(
        self,
    ) -> None:
        original = calculate_ranking_fingerprint(
            self.ranking_rows
        )

        reversed_rows = tuple(
            reversed(self.ranking_rows)
        )

        changed = calculate_ranking_fingerprint(
            reversed_rows
        )

        self.assertNotEqual(original, changed)

    def test_summary_counts_and_selection_are_correct(
        self,
    ) -> None:
        optimization_results = tuple(
            build_optimization_result(row)
            for row in self.ranking_rows
        )

        validation_results = tuple(
            build_validation_result(
                row,
                status=(
                    "completed"
                    if row.framework_name
                    != "weak_framework"
                    else "failed"
                ),
            )
            for row in self.ranking_rows
        )

        summary = build_framework_research_summary(
            campaign_id="phase_27_selection_test",
            configuration_fingerprint=(
                "campaign_cfg_001"
            ),
            ranking_rows=self.ranking_rows,
            optimization_results=(
                optimization_results
            ),
            validation_results=validation_results,
            maximum_selected=3,
            maximum_per_category=1,
            fill_remaining=False,
        )

        self.assertEqual(summary.framework_count, 5)

        self.assertEqual(
            summary.optimization_completed_count,
            5,
        )

        self.assertEqual(
            summary.validation_completed_count,
            4,
        )

        self.assertEqual(
            summary.failed_framework_count,
            1,
        )

        self.assertEqual(
            summary.eligible_framework_count,
            4,
        )

        self.assertEqual(
            summary.selected_framework_count,
            3,
        )

        self.assertEqual(
            tuple(
                row.framework_name
                for row in summary.top_frameworks
            ),
            (
                "ema_trend",
                "bollinger_reversal",
                "volume_breakout",
            ),
        )

        self.assertEqual(
            len(summary.ranking_fingerprint),
            64,
        )

    def test_summary_rejects_empty_campaign_id(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "campaign_id must be a non-empty string",
        ):
            build_framework_research_summary(
                campaign_id=" ",
                configuration_fingerprint="cfg_001",
                ranking_rows=(),
                optimization_results=(),
                validation_results=(),
            )

    def test_empty_ranking_adds_warning(self) -> None:
        summary = build_framework_research_summary(
            campaign_id="empty_campaign",
            configuration_fingerprint="cfg_001",
            ranking_rows=(),
            optimization_results=(),
            validation_results=(),
        )

        self.assertEqual(
            summary.selected_framework_count,
            0,
        )

        self.assertIn(
            "Framework ranking is empty; no framework was selected.",
            summary.warnings,
        )


if __name__ == "__main__":
    unittest.main()
