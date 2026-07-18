from __future__ import annotations

from pathlib import Path

from src.research.frameworks.historical.checkpoints import load_checkpoint
from src.research.frameworks.historical.continuity import CLEAN_STATE, state_fingerprint
from src.research.frameworks.historical.exceptions import ArtifactCorruptionError, StateContinuityError
from src.research.frameworks.historical.models import ChunkStatus
from src.research.frameworks.historical.storage import file_checksum, read_decision_artifact, read_json, schema_fingerprint


def validate_chunk(run_directory,chunk,plan,strict=True,expected_predecessor_fingerprint=None):
    directory=Path(run_directory)/"chunks"/f"chunk_{chunk.chunk_index:06d}"
    checkpoint=load_checkpoint(directory/"checkpoint.json")
    errors=[]
    if checkpoint.run_id!=plan.run_id:errors.append("run_id")
    if checkpoint.chunk_id!=chunk.chunk_id:errors.append("chunk_id")
    if checkpoint.configuration_fingerprint!=plan.configuration_fingerprint:errors.append("configuration_fingerprint")
    if strict and checkpoint.code_fingerprint!=plan.code_fingerprint:errors.append("code_fingerprint")
    primary=plan.config.framework_configuration.primary_role
    if checkpoint.input_fingerprint!=plan.source_fingerprints[primary]:errors.append("source_fingerprint")
    if checkpoint.status is not ChunkStatus.COMPLETED:errors.append("status")
    if expected_predecessor_fingerprint is not None and checkpoint.predecessor_final_state_fingerprint!=expected_predecessor_fingerprint:errors.append("predecessor_state")
    expected_initial=state_fingerprint(CLEAN_STATE) if chunk.chunk_index==0 else expected_predecessor_fingerprint
    if expected_initial is not None and checkpoint.initial_state_fingerprint!=expected_initial:errors.append("initial_state")
    if checkpoint.logical_start!=chunk.logical_start or checkpoint.logical_end!=chunk.logical_end:errors.append("logical_range")
    artifact=directory/checkpoint.output_artifact
    if not artifact.is_file():errors.append("artifact_missing")
    elif file_checksum(artifact)!=checkpoint.artifact_checksum:errors.append("artifact_checksum")
    else:
        frame=read_decision_artifact(artifact,plan.config.artifact_format)
        if len(frame)!=checkpoint.output_row_count or len(frame)!=chunk.expected_output_row_count:errors.append("row_count")
        if frame["timestamp"].duplicated().any() or not frame["timestamp"].is_monotonic_increasing:errors.append("index_order")
        if schema_fingerprint(frame)!=checkpoint.schema_fingerprint:errors.append("schema_fingerprint")
    if errors and strict:raise ArtifactCorruptionError(f"run {plan.run_id} chunk {chunk.chunk_id} failed integrity: {','.join(errors)}; rerun this chunk and downstream chunks")
    return {"valid":not errors,"errors":errors,"checkpoint":checkpoint}


def validate_historical_run(run_directory,plan=None,strict=True):
    from src.research.frameworks.historical.recovery import load_plan
    plan=plan or load_plan(run_directory)
    results=[];predecessor="CLEAN_INITIAL_STATE"
    for chunk in plan.chunks:
        try:result=validate_chunk(run_directory,chunk,plan,strict,predecessor)
        except Exception as error:
            if strict:raise
            result={"valid":False,"errors":[str(error)],"checkpoint":None}
        results.append(result)
        if result["valid"]:predecessor=result["checkpoint"].final_state_fingerprint
        else:predecessor="INVALID"
    manifest_errors=[];manifest_path=Path(run_directory)/"manifest.json"
    if not manifest_path.is_file():manifest_errors.append("manifest_missing")
    else:
        try:manifest=read_json(manifest_path)
        except Exception:manifest_errors.append("manifest_unreadable");manifest={}
        expected_completed=[chunk.chunk_id for chunk,result in zip(plan.chunks,results) if result["valid"]]
        if manifest.get("run_id")!=plan.run_id:manifest_errors.append("manifest_run_id")
        if manifest.get("configuration_fingerprint")!=plan.configuration_fingerprint:manifest_errors.append("manifest_configuration")
        if strict and manifest.get("code_fingerprint")!=plan.code_fingerprint:manifest_errors.append("manifest_code")
        if manifest.get("source_fingerprints")!=dict(plan.source_fingerprints):manifest_errors.append("manifest_sources")
        if manifest.get("completed_chunks")!=expected_completed:manifest_errors.append("manifest_completed_chunks")
        if all(item["valid"] for item in results) and manifest.get("status")!="completed":manifest_errors.append("manifest_status")
    valid=all(item["valid"] for item in results) and not manifest_errors
    if strict and manifest_errors:raise ArtifactCorruptionError(f"run {plan.run_id} manifest failed integrity: {','.join(manifest_errors)}")
    return {"valid":valid,"chunks":results,"manifest_errors":manifest_errors,"run_id":plan.run_id}
