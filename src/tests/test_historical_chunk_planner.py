from dataclasses import replace
from src.research.frameworks.historical.models import HistoricalResearchRunConfig
from src.research.frameworks.historical.planner import plan_historical_run
from src.research.frameworks.historical.source import source_bundle
from src.research.frameworks.reporting import _configuration
from src.utils.trading_framework_performance import _context

def test_historical_chunk_planner():
    source=source_bundle(_context("ema_ribbon_trend",23).frames);configuration=replace(_configuration("ema_ribbon_trend"),run_id=None)
    for size in (1,3,7,23,50):
        plan=plan_historical_run(HistoricalResearchRunConfig(f"plan_{size}",configuration,"15m",chunk_size_rows=size),source)
        logical=[position for chunk in plan.chunks for position in range(chunk.logical_start,chunk.logical_end+1)]
        assert logical==list(range(23)) and len(logical)==len(set(logical))
        assert all(chunk.expected_output_row_count<=size for chunk in plan.chunks)
    index=source["execution"].index()
    ranged=plan_historical_run(HistoricalResearchRunConfig("plan_range",configuration,"15m",start_timestamp=index[5],end_timestamp=index[17],chunk_size_rows=5),source)
    assert ranged.execution_start==5 and ranged.execution_row_count==13
    assert [chunk.expected_output_row_count for chunk in ranged.chunks]==[5,5,3]
if __name__=="__main__":test_historical_chunk_planner();print("test_historical_chunk_planner passed")
