from __future__ import annotations

import unittest

from src.research.frameworks.historical.campaign.framework_research_orchestrator import (
    FrameworkResearchOrchestrator,
)
from src.research.frameworks.historical.campaign.research_models import (
    FrameworkOptimizationResult,
    FrameworkValidationResult,
)


def _optimization_result(
    *,
    framework_name: str,
    fingerprint: str,
    category: str,
    optimization_score: float,
) -> FrameworkOptimizationResult:
    return FrameworkOptimizationResult(
        framework_name=framework_name,
        framework_version="1.0.0",
        status="completed",
        selected_configuration={
            "parameter": 20,
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


def _validation_result(
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
        win_rate_pct=54.0,
        profit_factor=1.30,
        max_drawdown_pct=14.0,
        expectancy=0.10,
        total_trades=80,
        wins=43,
        losses=37,
        fold_count=3,
        completed_fold_count=3,
        diagnostics={
            "robustness_score": robustness_score,
        },
    )


class FrameworkResearchOrchestratorTests(unittest.TestCase):
    def test_successful_campaign_pipeline(self) -> None:
        def run_optimization():
            return (
                _optimization_result(
                    framework_name="ema_trend",
                    fingerprint="cfg_ema_001",
                    category="trend",
                    optimization_score=78.0,
                ),
                _optimization_result(
                    framework_name="bollinger_reversal",
                    fingerprint="cfg_bb_001",
                    category="mean_reversion",
                    optimization_score=75.0,
                ),
            )

        def run_validation(optimization_results):
            self.assertEqual(
                len(optimization_results),
                2,
            )

            return (
                _validation_result(
                    framework_name="ema_trend",
                    fingerprint="cfg_ema_001",
                    validation_score=74.0,
                    robustness_score=72.0,
                ),
                _validation_result(
                    framework_name="bollinger_reversal",
                    fingerprint="cfg_bb_001",
                    validation_score=71.0,
                    robustness_score=70.0,
                ),
            )

        orchestrator = FrameworkResearchOrchestrator(
            optimization_executor=run_optimization,
            validation_executor=run_validation,
        )

        result = orchestrator.run(
            campaign_id="phase_27_test",
            configuration_fingerprint="campaign_cfg_001",
            maximum_selected=2,
            maximum_per_category=1,
            fill_remaining=False,
        )

        self.assertEqual(
            result.status,
            "completed",
        )
        self.assertEqual(
            result.errors,
            (),
        )
        self.assertEqual(
            len(result.optimization_results),
            2,
        )
        self.assertEqual(
            len(result.validation_results),
            2,
        )
        self.assertEqual(
            len(result.ranking_rows),
            2,
        )

        self.assertIsNotNone(result.summary)

        assert result.summary is not None

        self.assertEqual(
            result.summary.framework_count,
            2,
        )
        self.assertEqual(
            result.summary.selected_framework_count,
            2,
        )

        selected_names = [
            row.framework_name
            for row in result.summary.top_frameworks
        ]

        self.assertEqual(
            selected_names,
            [
                "ema_trend",
                "bollinger_reversal",
            ],
        )

        self.assertEqual(
            result.ranking_rows[0].rank,
            1,
        )
        self.assertEqual(
            result.ranking_rows[0].framework_name,
            "ema_trend",
        )

    def test_executor_failure_is_captured(self) -> None:
        def failing_optimization():
            raise RuntimeError(
                "simulated optimization failure"
            )

        def unused_validation(_optimization_results):
            self.fail(
                "validation executor must not run"
            )

        orchestrator = FrameworkResearchOrchestrator(
            optimization_executor=failing_optimization,
            validation_executor=unused_validation,
        )

        result = orchestrator.run(
            campaign_id="phase_27_failure_test",
            configuration_fingerprint="campaign_cfg_failure",
        )

        self.assertEqual(
            result.status,
            "failed",
        )
        self.assertIsNone(result.summary)
        self.assertEqual(
            result.optimization_results,
            (),
        )
        self.assertEqual(
            result.validation_results,
            (),
        )
        self.assertEqual(
            result.ranking_rows,
            (),
        )
        self.assertEqual(
            result.diagnostics["failed_stage"],
            "optimization",
        )
        self.assertIn(
            "RuntimeError: simulated optimization failure",
            result.errors,
        )

    def test_raise_on_error_propagates_exception(self) -> None:
        def failing_optimization():
            raise ValueError(
                "invalid optimization configuration"
            )

        orchestrator = FrameworkResearchOrchestrator(
            optimization_executor=failing_optimization,
            validation_executor=lambda _results: (),
        )

        with self.assertRaisesRegex(
            ValueError,
            "invalid optimization configuration",
        ):
            orchestrator.run(
                campaign_id="phase_27_raise_test",
                configuration_fingerprint=(
                    "campaign_cfg_raise"
                ),
                raise_on_error=True,
            )

    def test_duplicate_optimization_result_fails(self) -> None:
        duplicate = _optimization_result(
            framework_name="ema_trend",
            fingerprint="cfg_ema_001",
            category="trend",
            optimization_score=78.0,
        )

        orchestrator = FrameworkResearchOrchestrator(
            optimization_executor=lambda: (
                duplicate,
                duplicate,
            ),
            validation_executor=lambda _results: (),
        )

        result = orchestrator.run(
            campaign_id="phase_27_duplicate_test",
            configuration_fingerprint=(
                "campaign_cfg_duplicate"
            ),
        )

        self.assertEqual(
            result.status,
            "failed",
        )
        self.assertEqual(
            result.diagnostics["failed_stage"],
            "optimization",
        )
        self.assertTrue(
            any(
                "duplicate optimization result"
                in error
                for error in result.errors
            )
        )


if __name__ == "__main__":
    unittest.main()