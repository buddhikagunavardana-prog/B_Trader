from __future__ import annotations

from dataclasses import replace

import pandas as pd

from src.research.frameworks.historical.models import HistoricalResearchRunConfig, RunStatus
from src.research.frameworks.historical.orchestrator import run_historical_research
from src.research.frameworks.historical.planner import plan_historical_run
from src.research.frameworks.historical.recovery import resume_historical_research
from src.research.frameworks.historical.source import source_bundle
from src.research.frameworks.reporting import _configuration
from src.tests.historical_test_data import historical_case, stable_columns
from src.trading_frameworks.smc.frameworks import SMC_NAMES
from src.utils.trading_framework_performance import _context


def test_all_smc_continuous_and_chunked_outputs_are_equivalent(tmp_path):
    for name in SMC_NAMES:
        _, _, _, continuous, chunked, _ = historical_case(name, 60, 30, tmp_path, run_name=f"smc_equivalence_{name}")
        columns = stable_columns(continuous)
        pd.testing.assert_frame_equal(continuous[columns], chunked[columns], check_dtype=False, obj=name)


def test_smc_interrupted_checkpoint_resume(tmp_path):
    configuration = replace(_configuration("fair_value_gap"), run_id=None)
    sources = source_bundle(_context("fair_value_gap", 90).frames)
    plan = plan_historical_run(HistoricalResearchRunConfig("smc_resume", configuration, "15m", chunk_size_rows=30, output_directory=str(tmp_path)), sources)
    interrupted = run_historical_research(plan, sources, stop_after_chunks=1)
    assert interrupted.status is RunStatus.CANCELLED and interrupted.completed_chunks == 1
    resumed = resume_historical_research(interrupted.run_directory, sources)
    assert resumed.status is RunStatus.COMPLETED and resumed.completed_chunks == 3
