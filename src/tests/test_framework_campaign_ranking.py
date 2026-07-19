from __future__ import annotations

import unittest

from src.research.frameworks.historical.campaign.ranking import (
    calculate_framework_final_score,
    rank_framework_results,
)
from src.research.frameworks.historical.campaign.research_models import (
    FrameworkOptimizationResult,
    FrameworkValidationResult,
)


def build_optimization_result(
    *,
    framework_name: str,
    fingerprint: str,
    optimization_score: float,
    category: str,
) -> FrameworkOptimizationResult:
    return FrameworkOptimizationResult(
        framework_name=framework_name,
        framework_version="1.0.0",
        status="completed",
        selected_configuration={
            "period": 20,
        },
        selected_configuration_fingerprint=fingerprint,
        optimization_score=optimization_score,
        roi_pct=15.0,
        win_rate_pct=56.0,
        profit_factor=1.40,
        max_drawdown_pct=12.0,
        expectancy=0.15,
        total_trades=100,
        wins=56,
        losses=44,
        candidate_count=10,
        diagnostics={
            "category": category,
        },
    )


def build_validation_result(
    *,
    framework_name: str,
    fingerprint: str,
    validation_score: float,
    robustness_score: float,
) -> FrameworkValidationResult:
    return FrameworkValidationResult(
        framework_name=framework_name,
        framework_version="1.0.0",
        status="completed",
        configuration_fingerprint=fingerprint,
        validation_score=validation_score,
        roi_pct=10.0,
        win_rate_pct=55.0,
        profit_factor=1.30,
        max_drawdown_pct=14.0,
        expectancy=0.10,
        total_trades=80,
        wins=44,
        losses=36,
        fold_count=3,
        completed_fold_count=3,
        diagnostics={
            "robustness_score": robustness_score,
        },
    )


class FrameworkCampaignRankingTests(unittest.TestCase):
    def test_default_final_score_calculation(self) -> None:
        score = calculate_framework_final_score(
            optimization_score=78.0,
            validation_score=74.0,
            robustness_score=72.0,
        )

        self.assertIsInstance(score, float)
        self.assertGreater(score, 0.0)
        self.assertLessEqual(score, 100.0)

    def test_frameworks_are_ranked_by_score(self) -> None:
        optimization_results = (
            build_optimization_result(
                framework_name="ema_trend",
                fingerprint="cfg_ema_001",
                optimization_score=80.0,
                category="trend",
            ),
            build_optimization_result(
                framework_name="bollinger_reversal",
                fingerprint="cfg_bb_001",
                optimization_score=70.0,
                category="mean_reversion",
            ),
        )

        validation_results = (
            build_validation_result(
                framework_name="ema_trend",
                fingerprint="cfg_ema_001",
                validation_score=78.0,
                robustness_score=76.0,
            ),
            build_validation_result(
                framework_name="bollinger_reversal",
                fingerprint="cfg_bb_001",
                validation_score=68.0,
                robustness_score=66.0,
            ),
        )

        ranking_rows = rank_framework_results(
            optimization_results=optimization_results,
            validation_results=validation_results,
        )

        self.assertEqual(len(ranking_rows), 2)

        self.assertEqual(
            ranking_rows[0].framework_name,
            "ema_trend",
        )
        self.assertEqual(
            ranking_rows[0].rank,
            1,
        )

        self.assertEqual(
            ranking_rows[1].framework_name,
            "bollinger_reversal",
        )
        self.assertEqual(
            ranking_rows[1].rank,
            2,
        )

        self.assertGreater(
            ranking_rows[0].final_score,
            ranking_rows[1].final_score,
        )

    def test_category_and_robustness_are_preserved(self) -> None:
        ranking_rows = rank_framework_results(
            optimization_results=(
                build_optimization_result(
                    framework_name="ema_trend",
                    fingerprint="cfg_ema_001",
                    optimization_score=80.0,
                    category="trend",
                ),
            ),
            validation_results=(
                build_validation_result(
                    framework_name="ema_trend",
                    fingerprint="cfg_ema_001",
                    validation_score=78.0,
                    robustness_score=76.0,
                ),
            ),
        )

        self.assertEqual(len(ranking_rows), 1)

        row = ranking_rows[0]

        self.assertEqual(
            row.category,
            "trend",
        )
        self.assertEqual(
            row.robustness_score,
            76.0,
        )

    def test_fingerprint_mismatch_is_rejected(self) -> None:
        ranking_rows = rank_framework_results(
            optimization_results=(
                build_optimization_result(
                    framework_name="ema_trend",
                    fingerprint="cfg_optimization",
                    optimization_score=80.0,
                    category="trend",
                ),
            ),
            validation_results=(
                build_validation_result(
                    framework_name="ema_trend",
                    fingerprint="cfg_validation",
                    validation_score=78.0,
                    robustness_score=76.0,
                ),
            ),
        )

        self.assertEqual(len(ranking_rows), 1)

        row = ranking_rows[0]

        self.assertFalse(
            row.eligible_for_paper_trading
        )
        self.assertIn(
            "Optimization and validation configuration fingerprints differ",
            row.rejection_reasons,
        )


if __name__ == "__main__":
    unittest.main()

