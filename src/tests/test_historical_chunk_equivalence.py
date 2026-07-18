import tempfile
from dataclasses import replace
import pandas as pd

from src.research.frameworks.adapter import run_framework_decision_series
from src.research.frameworks.historical.merge import merge_historical_artifacts
from src.research.frameworks.historical.models import HistoricalResearchRunConfig
from src.research.frameworks.historical.orchestrator import run_historical_research
from src.research.frameworks.historical.planner import plan_historical_run
from src.research.frameworks.historical.source import source_bundle
from src.research.frameworks.reporting import _configuration
from src.tests.historical_test_data import historical_case,normalized_csv,stable_columns
from src.utils.trading_framework_performance import _context

def test_historical_chunk_equivalence():
    with tempfile.TemporaryDirectory() as root:
        for name in ("ema_ribbon_trend","opening_range_breakout","heikin_ashi_trend"):
            _,_,_,continuous,chunked,_=historical_case(name,220,55,root,run_name=f"equivalence_{name}")
            assert continuous[stable_columns(continuous)].equals(chunked[stable_columns(chunked)])
        configuration=replace(_configuration("ema_ribbon_trend"),run_id=None)
        frames=_context(configuration.framework,220).frames;index=frames[configuration.primary_role].index
        start,end=index[20],index[149];ranged_configuration=replace(configuration,start_timestamp=start,end_timestamp=end,run_id=None)
        continuous=normalized_csv(run_framework_decision_series(ranged_configuration,frames).decisions)
        sources=source_bundle(frames);historical=HistoricalResearchRunConfig("equivalence_range",configuration,"15m",start_timestamp=start,end_timestamp=end,chunk_size_rows=37,output_directory=root)
        result=run_historical_research(plan_historical_run(historical,sources),sources);merged=merge_historical_artifacts(result.run_directory);chunked=pd.read_csv(merged.artifact_path,parse_dates=["timestamp"])
        pd.testing.assert_frame_equal(continuous[stable_columns(continuous)].reset_index(drop=True),chunked[stable_columns(chunked)].reset_index(drop=True),check_dtype=False)
if __name__=="__main__":test_historical_chunk_equivalence();print("test_historical_chunk_equivalence passed")
