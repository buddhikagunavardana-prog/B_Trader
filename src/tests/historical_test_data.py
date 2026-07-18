from dataclasses import replace
from io import StringIO
from pathlib import Path
import pandas as pd

from src.research.frameworks.adapter import run_framework_decision_series
from src.research.frameworks.historical.merge import merge_historical_artifacts
from src.research.frameworks.historical.models import HistoricalResearchRunConfig
from src.research.frameworks.historical.orchestrator import run_historical_research
from src.research.frameworks.historical.planner import plan_historical_run
from src.research.frameworks.historical.source import source_bundle
from src.research.frameworks.reporting import _configuration
from src.utils.trading_framework_performance import _context


def normalized_csv(frame):
    payload=frame.to_csv(index=False,float_format="%.17g",lineterminator="\n")
    return pd.read_csv(StringIO(payload),parse_dates=["timestamp"])


def historical_case(name,rows,chunk_size,root,run_name=None,**overrides):
    configuration=replace(_configuration(name),run_id=None)
    frames=_context(name,rows).frames;sources=source_bundle(frames)
    config=HistoricalResearchRunConfig(run_name or f"test_{name}_{rows}_{chunk_size}",configuration,configuration.timeframe_roles[configuration.primary_role],chunk_size_rows=chunk_size,output_directory=str(root),**overrides)
    plan=plan_historical_run(config,sources);result=run_historical_research(plan,sources);merged=merge_historical_artifacts(result.run_directory)
    continuous=normalized_csv(run_framework_decision_series(configuration,frames).decisions)
    chunked=pd.read_csv(merged.artifact_path,parse_dates=["timestamp"])
    return plan,result,merged,continuous,chunked,sources


def stable_columns(frame):return [column for column in frame.columns if column not in {"controller_time_ns","policy_time_ns"}]
