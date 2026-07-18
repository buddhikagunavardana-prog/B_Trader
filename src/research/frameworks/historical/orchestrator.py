from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from time import perf_counter

from src.research.frameworks.adapter import run_framework_decision_series
from src.research.frameworks.historical.cancellation import CancellationToken
from src.research.frameworks.historical.checkpoints import checkpoint_path, write_checkpoint
from src.research.frameworks.historical.continuity import CLEAN_STATE, continuity_state, state_fingerprint
from src.research.frameworks.historical.exceptions import ConfigurationMismatchError, HistoricalCancellationError, InvalidChunkPlanError
from src.research.frameworks.historical.integrity import validate_chunk
from src.research.frameworks.historical.locking import ChunkLock
from src.research.frameworks.historical.models import ChunkCheckpoint, ChunkStatus, HistoricalRunManifest, HistoricalRunResult, RunStatus
from src.research.frameworks.historical.storage import artifact_name, atomic_json, read_decision_artifact, read_json, safe_run_directory, schema_fingerprint, write_decision_artifact
from src.research.frameworks.profiling.memory import dataframe_memory_bytes


def _plan_payload(plan):
    return {
        "manifest_version":"1.0","integrity_version":"1.0","run_id":plan.run_id,
        "configuration":plan.config.identity_snapshot(),"run_configuration":{
            **plan.config.identity_snapshot(),"output_directory":plan.config.output_directory,
            "checkpoint_directory":plan.config.checkpoint_directory,"maximum_memory_bytes":plan.config.maximum_memory_bytes,
            "strict_integrity_mode":plan.config.strict_integrity_mode,"resume_enabled":plan.config.resume_enabled,
            "overwrite_policy":plan.config.overwrite_policy,"cancellation_check_interval":plan.config.cancellation_check_interval,
            "run_id":plan.run_id,
        },
        "source_fingerprints":dict(plan.source_fingerprints),"configuration_fingerprint":plan.configuration_fingerprint,
        "source_descriptors":{role:dict(value) for role,value in plan.source_descriptors.items()},
        "code_fingerprint":plan.code_fingerprint,"execution_row_count":plan.execution_row_count,"execution_start":plan.execution_start,"warmup_rows":plan.warmup_rows,
        "chunks":[chunk.to_dict() for chunk in plan.chunks],"framework":plan.config.framework_configuration.framework,
        "framework_configuration":plan.config.framework_configuration.to_dict(),
    }


def _manifest_payload(plan,status,completed,warnings=()):
    pending=tuple(chunk.chunk_id for chunk in plan.chunks if chunk.chunk_id not in completed)
    manifest=HistoricalRunManifest(plan.run_id,status,tuple(completed),pending,len(completed)-1,dict(plan.source_fingerprints),plan.configuration_fingerprint,plan.code_fingerprint,tuple(warnings)).to_dict()
    return {**_plan_payload(plan),**manifest,
        "failed_chunks":[],"cancelled_chunks":[],"corrupt_chunks":[],"continuity_frontier":len(completed)-1,
        "diagnostic_level":plan.config.diagnostic_level,"snapshot_mode":plan.config.snapshot_mode,
        "state_schema_version":"1.0","checkpoint_schema_version":"1.0","warnings":list(warnings)}


def _read_chunk_sources(plan,sources,chunk):
    primary=plan.config.framework_configuration.primary_role
    primary_index=sources[primary].index();absolute_start=plan.execution_start+chunk.read_start;absolute_end=plan.execution_start+chunk.read_end
    start_ts=primary_index[absolute_start];end_ts=primary_index[absolute_end]
    result={primary:sources[primary].read_rows(absolute_start,absolute_end+1)};offsets={primary:absolute_start}
    for role,source in sources.items():
        if role==primary:continue
        index=source.index();end=int(index.searchsorted(end_ts,side="right"));start=max(0,int(index.searchsorted(start_ts,side="left"))-plan.warmup_rows)
        result[role]=source.read_rows(start,end);offsets[role]=start
    return result,offsets


def run_historical_research(plan,sources,cancellation_token=None,stop_after_chunks=None):
    cancellation_token=cancellation_token or CancellationToken()
    run_directory=safe_run_directory(plan.config.output_directory,plan.run_id);run_directory.mkdir(parents=True,exist_ok=True)
    plan_path=run_directory/"plan.json";payload=_plan_payload(plan)
    if plan_path.exists():
        stored=read_json(plan_path)
        identity_keys=("run_id","source_fingerprints","configuration_fingerprint","code_fingerprint","execution_row_count","execution_start","chunks")
        if any(stored.get(key)!=payload.get(key) for key in identity_keys):
            raise ConfigurationMismatchError(f"run {plan.run_id} stored plan differs from requested deterministic plan")
    else:atomic_json(plan_path,payload)
    completed=[];initial_state=CLEAN_STATE;predecessor_fingerprint="CLEAN_INITIAL_STATE";total_rows=0
    started=perf_counter();timing={"source_read_seconds":0.0,"adapter_seconds":0.0,"artifact_write_seconds":0.0,"checkpoint_seconds":0.0,"validation_seconds":0.0,"manifest_seconds":0.0}
    atomic_json(run_directory/"manifest.json",_manifest_payload(plan,RunStatus.RUNNING,completed))
    try:
        for chunk in plan.chunks:
            cancellation_token.raise_if_cancelled()
            if stop_after_chunks is not None and len(completed)>=stop_after_chunks:raise HistoricalCancellationError("synthetic interruption at safe chunk boundary")
            chunk_directory=run_directory/"chunks"/f"chunk_{chunk.chunk_index:06d}"
            existing=chunk_directory/"checkpoint.json"
            if existing.exists() and plan.config.resume_enabled:
                checked=validate_chunk(run_directory,chunk,plan,plan.config.strict_integrity_mode,predecessor_fingerprint)
                checkpoint=checked["checkpoint"];completed.append(chunk.chunk_id);total_rows+=checkpoint.output_row_count
                initial_state=dict(checkpoint.final_state);predecessor_fingerprint=checkpoint.final_state_fingerprint;continue
            with ChunkLock(chunk_directory/"chunk.lock"):
                read_started=perf_counter();data,row_offsets=_read_chunk_sources(plan,sources,chunk);timing["source_read_seconds"]+=perf_counter()-read_started
                memory=sum(dataframe_memory_bytes(frame) for frame in data.values())
                if memory>plan.config.maximum_memory_bytes and plan.config.strict_integrity_mode:
                    raise MemoryError(f"run {plan.run_id} chunk {chunk.chunk_id} estimated memory {memory} exceeds target {plan.config.maximum_memory_bytes}; create a new plan with smaller chunks")
                primary=plan.config.framework_configuration.primary_role;logical_index=sources[primary].index();absolute_logical_start=plan.execution_start+chunk.logical_start;absolute_logical_end=plan.execution_start+chunk.logical_end
                configuration=replace(plan.config.framework_configuration,start_timestamp=logical_index[absolute_logical_start],end_timestamp=logical_index[absolute_logical_end],state_diagnostics_level=plan.config.diagnostic_level,persist_state_snapshots=plan.config.snapshot_mode,enable_stateful_research=plan.config.stateful_mode,enable_controller_timing=plan.config.instrumentation_mode,run_id=None)
                adapter_started=perf_counter();result=run_framework_decision_series(configuration,data,initial_state=initial_state if chunk.chunk_index else None,row_offsets=row_offsets);timing["adapter_seconds"]+=perf_counter()-adapter_started
                decisions=result.decisions
                if len(decisions)!=chunk.expected_output_row_count:raise InvalidChunkPlanError(f"run {plan.run_id} chunk {chunk.chunk_id} expected {chunk.expected_output_row_count} output rows, got {len(decisions)}")
                final_state=continuity_state(result.reproducibility.get("final_policy_state_summary"));final_fingerprint=state_fingerprint(final_state)
                artifact_started=perf_counter();artifact_path,checksum=write_decision_artifact(decisions,chunk_directory/artifact_name(plan.config),plan.config);timing["artifact_write_seconds"]+=perf_counter()-artifact_started
                persisted_decisions=read_decision_artifact(artifact_path,plan.config.artifact_format)
                checkpoint=ChunkCheckpoint(plan.run_id,chunk.chunk_id,chunk.chunk_index,1,ChunkStatus.COMPLETED,plan.source_fingerprints[primary],plan.configuration_fingerprint,plan.code_fingerprint,predecessor_fingerprint,state_fingerprint(initial_state),final_state,final_fingerprint,artifact_path.name,checksum,sum(len(frame) for frame in data.values()),len(decisions),chunk.logical_start,chunk.logical_end,None if decisions.empty else str(decisions["timestamp"].iloc[0]),None if decisions.empty else str(decisions["timestamp"].iloc[-1]),schema_fingerprint(persisted_decisions),tuple(result.warnings),timing_summary={"adapter_seconds":result.execution_duration_seconds},memory_summary={"input_bytes":memory,"output_bytes":dataframe_memory_bytes(decisions)})
                checkpoint_started=perf_counter();write_checkpoint(checkpoint_path(run_directory,chunk.chunk_index),checkpoint);timing["checkpoint_seconds"]+=perf_counter()-checkpoint_started
                validation_started=perf_counter();validate_chunk(run_directory,chunk,plan,True,predecessor_fingerprint);timing["validation_seconds"]+=perf_counter()-validation_started
                completed.append(chunk.chunk_id);total_rows+=len(decisions);initial_state=final_state;predecessor_fingerprint=final_fingerprint
                manifest_started=perf_counter();atomic_json(run_directory/"manifest.json",_manifest_payload(plan,RunStatus.RUNNING,completed));timing["manifest_seconds"]+=perf_counter()-manifest_started
        atomic_json(run_directory/"manifest.json",_manifest_payload(plan,RunStatus.COMPLETED,completed));timing["total_seconds"]=perf_counter()-started
        return HistoricalRunResult(plan.run_id,RunStatus.COMPLETED,str(run_directory),len(completed),len(plan.chunks),total_rows,timing_summary=timing)
    except HistoricalCancellationError:
        atomic_json(run_directory/"manifest.json",_manifest_payload(plan,RunStatus.CANCELLED,completed,("Run stopped at a safe chunk boundary.",)))
        return HistoricalRunResult(plan.run_id,RunStatus.CANCELLED,str(run_directory),len(completed),len(plan.chunks),total_rows,("Run stopped at a safe chunk boundary.",),timing)
    except Exception as error:
        atomic_json(run_directory/"manifest.json",_manifest_payload(plan,RunStatus.FAILED,completed,(f"{type(error).__name__}: {error}",)))
        raise
