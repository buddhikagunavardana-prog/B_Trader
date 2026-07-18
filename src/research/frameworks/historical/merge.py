from __future__ import annotations

import os
from pathlib import Path

import pandas as pd

from src.research.frameworks.historical.exceptions import MergeGapError, MergeOverlapError
from src.research.frameworks.historical.integrity import validate_chunk
from src.research.frameworks.historical.models import MergeResult
from src.research.frameworks.historical.recovery import load_plan
from src.research.frameworks.historical.storage import atomic_json, file_checksum, read_decision_artifact, schema_fingerprint


def merge_historical_artifacts(run_directory):
    run_directory=Path(run_directory);plan=load_plan(run_directory);temporary=run_directory/"merged_decisions.csv.tmp";target=run_directory/"merged_decisions.csv"
    if temporary.exists():temporary.unlink()
    prior_end=None;columns=None;rows=0;schema=None;predecessor="CLEAN_INITIAL_STATE"
    for chunk in plan.chunks:
        checked=validate_chunk(run_directory,chunk,plan,True,predecessor);checkpoint=checked["checkpoint"];predecessor=checkpoint.final_state_fingerprint
        if prior_end is not None:
            if chunk.logical_start<=prior_end:raise MergeOverlapError(f"run {plan.run_id} chunk {chunk.chunk_id} overlaps prior output")
            if chunk.logical_start!=prior_end+1:raise MergeGapError(f"run {plan.run_id} chunk {chunk.chunk_id} leaves an output gap")
        frame=read_decision_artifact(run_directory/"chunks"/f"chunk_{chunk.chunk_index:06d}"/checkpoint.output_artifact,plan.config.artifact_format)
        if columns is None:columns=list(frame.columns);schema=schema_fingerprint(frame)
        elif list(frame.columns)!=columns or schema_fingerprint(frame)!=schema:raise MergeOverlapError(f"run {plan.run_id} chunk {chunk.chunk_id} schema differs; do not merge")
        frame.to_csv(temporary,index=False,mode="a",header=rows==0,float_format="%.17g",lineterminator="\n");rows+=len(frame);prior_end=chunk.logical_end
    os.replace(temporary,target);checksum=file_checksum(target)
    atomic_json(run_directory/"merge_manifest.json",{"run_id":plan.run_id,"row_count":rows,"checksum":checksum,"schema_fingerprint":schema,"chunks":[chunk.chunk_id for chunk in plan.chunks]})
    return MergeResult(plan.run_id,str(target),rows,checksum,schema)
