import tempfile
from pathlib import Path
from src.tests.historical_test_data import historical_case,stable_columns
from src.utils.trading_framework_performance import _context
from src.research.frameworks.historical.source import source_bundle
from src.research.frameworks.historical.models import HistoricalResearchRunConfig
from src.research.frameworks.historical.planner import plan_historical_run
from src.research.frameworks.historical.orchestrator import run_historical_research
from src.research.frameworks.historical.merge import merge_historical_artifacts
from src.research.frameworks.reporting import _configuration
from dataclasses import replace
import pandas as pd

def test_historical_causality():
    with tempfile.TemporaryDirectory() as root:
        for name,cutoff in (("ema_ribbon_trend",79),("opening_range_breakout",80),("stochastic_pullback_trend",61),("triple_screen_trading",90)):
            _,_,_,_,original,original_sources=historical_case(name,180,60,root,run_name=f"causal_original_{name}")
            frames={role:source.read_rows(0,source.row_count()) for role,source in original_sources.items()};cutoff_time=frames[_configuration(name).primary_role].index[cutoff]
            for frame in frames.values():
                numeric=list(frame.select_dtypes(include="number").columns);frame.loc[frame.index>cutoff_time,numeric]+=1_000_000.0
            configuration=replace(_configuration(name),run_id=None);sources=source_bundle(frames);config=HistoricalResearchRunConfig(f"causal_changed_{name}",configuration,configuration.timeframe_roles[configuration.primary_role],chunk_size_rows=60,output_directory=root);plan=plan_historical_run(config,sources);result=run_historical_research(plan,sources);merged=merge_historical_artifacts(result.run_directory);changed=pd.read_csv(merged.artifact_path,parse_dates=["timestamp"])
            columns=stable_columns(original);left=original.loc[original.timestamp<=cutoff_time,columns].reset_index(drop=True);right=changed.loc[changed.timestamp<=cutoff_time,columns].reset_index(drop=True)
            pd.testing.assert_frame_equal(left,right,check_dtype=False,obj=f"{name} pre-cutoff chunked output")
if __name__=="__main__":test_historical_causality();print("test_historical_causality passed")
