import json,tempfile
from dataclasses import replace
from pathlib import Path
from src.tests.historical_test_data import historical_case
from src.research.frameworks.historical.checkpoints import load_checkpoint
from src.research.frameworks.historical.exceptions import SourceMismatchError,UnsupportedSchemaVersionError
from src.research.frameworks.historical.recovery import recover_historical_run,resume_historical_research
from src.research.frameworks.historical.source import source_bundle
from src.utils.trading_framework_performance import _context

def test_historical_recovery_scenarios():
    with tempfile.TemporaryDirectory() as root:
        plan,result,_,_,_,sources=historical_case("ema_ribbon_trend",120,40,root)
        run=Path(result.run_directory);orphan=run/"orphan.tmp";orphan.write_text("partial",encoding="utf-8")
        checkpoint=run/"chunks/chunk_000001/checkpoint.json";payload=json.loads(checkpoint.read_text(encoding="utf-8"));payload["checkpoint_version"]="99";checkpoint.write_text(json.dumps(payload),encoding="utf-8")
        try:load_checkpoint(checkpoint)
        except UnsupportedSchemaVersionError:pass
        else:raise AssertionError("unsupported checkpoint accepted")
        report=recover_historical_run(run,plan);assert report.retained_chunks==(plan.chunks[0].chunk_id,) and len(report.chunks_to_rerun)==2 and report.orphan_files
        changed={role:frame.copy(deep=True) for role,frame in _context("ema_ribbon_trend",120).frames.items()};changed["execution"].iloc[-1,0]+=1
        try:resume_historical_research(run,source_bundle(changed))
        except SourceMismatchError:pass
        else:raise AssertionError("changed source accepted")
if __name__=="__main__":test_historical_recovery_scenarios();print("test_historical_recovery_scenarios passed")
