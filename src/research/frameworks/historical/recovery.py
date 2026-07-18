from __future__ import annotations

import shutil
from pathlib import Path

from src.research.frameworks.configuration import configuration_from_dict
from src.research.frameworks.historical.exceptions import CodeMismatchError, ConfigurationMismatchError, InvalidChunkPlanError, SourceMismatchError
from src.research.frameworks.historical.integrity import validate_chunk
from src.research.frameworks.historical.models import ChunkPlan, ChunkStatus, HistoricalResearchRunConfig, HistoricalRunPlan, RecoveryReport
from src.research.frameworks.historical.orchestrator import run_historical_research
from src.research.frameworks.historical.storage import read_json
from src.research.run_management.run_identity import stable_identity_hash


def load_plan(run_directory):
    payload=read_json(Path(run_directory)/"plan.json")
    framework_configuration=configuration_from_dict(payload["framework_configuration"])
    run_config=dict(payload["run_configuration"]);run_config["framework_configuration"]=framework_configuration
    config=HistoricalResearchRunConfig(**run_config)
    expected_configuration_fingerprint=stable_identity_hash(config.identity_snapshot())
    if payload.get("configuration_fingerprint")!=expected_configuration_fingerprint:
        raise ConfigurationMismatchError(f"run {payload.get('run_id')} stored configuration fingerprint is invalid")
    chunks=tuple(ChunkPlan(**{**item,"status":ChunkStatus(item["status"])}) for item in payload["chunks"])
    expected_start=0
    for index,chunk in enumerate(chunks):
        if chunk.chunk_index!=index or chunk.run_id!=payload["run_id"] or chunk.logical_start!=expected_start or chunk.logical_end<chunk.logical_start:
            raise InvalidChunkPlanError(f"run {payload.get('run_id')} stored chunk plan is out of order, overlapping, or has a gap")
        expected_start=chunk.logical_end+1
    if expected_start!=payload["execution_row_count"]:
        raise InvalidChunkPlanError(f"run {payload.get('run_id')} stored chunk plan does not cover the execution range")
    return HistoricalRunPlan(payload["run_id"],config,payload["source_fingerprints"],payload["configuration_fingerprint"],payload["code_fingerprint"],chunks,payload["execution_row_count"],payload["warmup_rows"],payload.get("execution_start",0),payload.get("source_descriptors",{}))


def recover_historical_run(run_directory,plan=None):
    run_directory=Path(run_directory);plan=plan or load_plan(run_directory)
    retained=[];invalid=[];rerun=[];orphans=[];incompatible=[];predecessor="CLEAN_INITIAL_STATE";frontier_valid=True
    for chunk in plan.chunks:
        directory=run_directory/"chunks"/f"chunk_{chunk.chunk_index:06d}"
        if frontier_valid and (directory/"checkpoint.json").exists():
            try:result=validate_chunk(run_directory,chunk,plan,False,predecessor)
            except Exception as error:result={"valid":False,"errors":[str(error)],"checkpoint":None}
            if result["valid"]:
                retained.append(chunk.chunk_id);predecessor=result["checkpoint"].final_state_fingerprint;continue
        frontier_valid=False;rerun.append(chunk.chunk_id)
        if directory.exists():
            invalid.append(chunk.chunk_id);superseded=run_directory/"superseded"/f"chunk_{chunk.chunk_index:06d}"
            superseded.parent.mkdir(parents=True,exist_ok=True)
            if superseded.exists():shutil.rmtree(superseded)
            shutil.move(str(directory),str(superseded))
    for temporary in run_directory.rglob("*.tmp"):orphans.append(str(temporary.relative_to(run_directory)));temporary.unlink(missing_ok=True)
    return RecoveryReport(plan.run_id,tuple(retained),tuple(invalid),tuple(rerun),tuple(orphans),tuple(incompatible),"Resume from the first chunk listed in chunks_to_rerun." if rerun else "No recovery action required.")


def resume_historical_research(run_directory,sources,allow_compatible_code=False,cancellation_token=None):
    plan=load_plan(run_directory)
    actual={role:source.fingerprint() for role,source in sources.items()}
    if actual!=dict(plan.source_fingerprints):raise SourceMismatchError(f"run {plan.run_id} source fingerprint mismatch; create a new deterministic run")
    from src.research.frameworks.historical.planner import _code_fingerprint
    current=_code_fingerprint()
    if current!=plan.code_fingerprint and plan.config.strict_integrity_mode and not allow_compatible_code:raise CodeMismatchError(f"run {plan.run_id} code fingerprint expected {plan.code_fingerprint}, got {current}; resume with matching code")
    recover_historical_run(run_directory,plan)
    return run_historical_research(plan,sources,cancellation_token=cancellation_token)
