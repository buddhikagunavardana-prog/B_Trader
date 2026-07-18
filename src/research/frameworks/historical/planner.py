from __future__ import annotations

import hashlib
from pathlib import Path

from src.research.frameworks.historical.exceptions import InvalidChunkPlanError
from src.research.frameworks.historical.models import ChunkPlan, HistoricalRunPlan, OverlapMode
from src.research.run_management.run_identity import stable_identity_hash
from src.trading_frameworks.loader import load_trading_framework


def _code_fingerprint():
    digest=hashlib.sha256()
    historical_root=Path(__file__).resolve().parent
    paths=sorted(historical_root.glob("*.py"))
    paths.extend((historical_root.parent/"adapter.py",historical_root.parent/"state"/"controller.py"))
    for path in paths:
        digest.update(str(path.relative_to(historical_root.parent.parent.parent)).encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def dependency_warmup(config):
    framework=load_trading_framework(config.framework_configuration.framework,config.framework_configuration.parameters)
    base=max(framework.minimum_history.values(),default=1)
    requested=config.warmup_rows
    if config.overlap_policy is OverlapMode.NONE:return 0
    if config.overlap_policy is OverlapMode.FIXED_ROWS:return requested
    periods=[int(value) for key,value in framework.parameters.items() if "period" in key and isinstance(value,(int,float))]
    session_floor=100 if framework.metadata.name in {"opening_range_breakout","pivot_range_breakout","vwap_mean_reversion"} else 0
    multi_floor=50 if len(framework.metadata.timeframe_roles)>1 else 0
    return max([requested,base,session_floor,multi_floor,*periods])+config.warmup_safety_margin


def plan_historical_run(config,sources):
    if not sources: raise InvalidChunkPlanError("historical source bundle is empty")
    for source in sources.values(): source.validate()
    primary=config.framework_configuration.primary_role
    if primary not in sources: raise InvalidChunkPlanError(f"primary source role missing: {primary}")
    required_roles=set(config.framework_configuration.timeframe_roles)
    missing_roles=required_roles-set(sources)
    if missing_roles: raise InvalidChunkPlanError(f"historical source roles missing: {','.join(sorted(missing_roles))}")
    if config.chunk_size_rows>config.maximum_output_rows_per_artifact: raise InvalidChunkPlanError("chunk_size_rows exceeds maximum_output_rows_per_artifact")
    primary_index=sources[primary].index()
    execution_start=0 if config.start_timestamp is None else int(primary_index.searchsorted(config.start_timestamp,side="left"))
    execution_end=len(primary_index) if config.end_timestamp is None else int(primary_index.searchsorted(config.end_timestamp,side="right"))
    rows=execution_end-execution_start
    if rows<1: raise InvalidChunkPlanError("empty historical range")
    for role,source in sources.items():
        if source.row_count()<1: raise InvalidChunkPlanError(f"empty source role: {role}")
    fingerprints={role:source.fingerprint() for role,source in sources.items()}
    descriptors={role:dict(source.descriptor()) for role,source in sources.items()}
    identity={**config.identity_snapshot(),"source_fingerprints":fingerprints,"schema_version":"1.0"}
    run_id=config.run_id or f"historical_{stable_identity_hash(identity)}"
    configuration_fingerprint=stable_identity_hash(config.identity_snapshot())
    warmup=dependency_warmup(config)
    count=(rows+config.chunk_size_rows-1)//config.chunk_size_rows
    chunks=[]
    for index in range(count):
        logical_start=index*config.chunk_size_rows;logical_end=min(rows,(index+1)*config.chunk_size_rows)-1
        # A ranged run may read warm-up rows before its logical row zero while
        # keeping output coordinates local to the requested range.
        read_start=max(-execution_start,logical_start-warmup);read_end=logical_end
        chunk_id=f"{run_id}_chunk_{index:06d}"
        chunks.append(ChunkPlan(run_id,index,logical_start,logical_end,read_start,read_end,logical_start-read_start,logical_start,logical_end,read_end-read_start+1,logical_end-logical_start+1,None if index==0 else f"{run_id}_chunk_{index-1:06d}",None if index==count-1 else f"{run_id}_chunk_{index+1:06d}",chunk_id))
    return HistoricalRunPlan(run_id,config,fingerprints,configuration_fingerprint,_code_fingerprint(),tuple(chunks),rows,warmup,execution_start,descriptors)
