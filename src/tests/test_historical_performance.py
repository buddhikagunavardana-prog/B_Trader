import tempfile
from time import perf_counter
from src.tests.historical_test_data import historical_case

def test_historical_performance():
    with tempfile.TemporaryDirectory() as root:
        started=perf_counter();plan,result,merged,_,chunked,_=historical_case("ema_ribbon_trend",10_000,2_000,root);elapsed=perf_counter()-started
        peak=max(item.memory_summary["input_bytes"]+item.memory_summary["output_bytes"] for item in [__import__("src.research.frameworks.historical.checkpoints",fromlist=["load_checkpoint"]).load_checkpoint(__import__("src.research.frameworks.historical.checkpoints",fromlist=["checkpoint_path"]).checkpoint_path(result.run_directory,chunk.chunk_index)) for chunk in plan.chunks])
        assert result.output_rows==10_000 and merged.row_count==10_000 and peak<plan.config.maximum_memory_bytes
        assert elapsed<120 and len(chunked)==10_000
if __name__=="__main__":test_historical_performance();print("test_historical_performance passed")
