from __future__ import annotations

import hashlib, json, os
from pathlib import Path

import pandas as pd

from src.research.frameworks.historical.exceptions import ArtifactCorruptionError
from src.research.run_management.run_identity import stable_identity_hash


def safe_run_directory(root,run_id):
    if not run_id or any(part in run_id for part in ("..","/","\\")): raise ValueError("unsafe run identity")
    base=Path(root).resolve();target=(base/run_id).resolve()
    if base not in target.parents: raise ValueError("run path escapes output root")
    return target


def atomic_json(path,payload):
    target=Path(path);target.parent.mkdir(parents=True,exist_ok=True);temporary=target.with_name(target.name+".tmp")
    with temporary.open("w",encoding="utf-8",newline="\n") as handle:
        json.dump(payload,handle,sort_keys=True,indent=2,default=str);handle.flush();os.fsync(handle.fileno())
    os.replace(temporary,target);return target


def read_json(path): return json.loads(Path(path).read_text(encoding="utf-8"))


def file_checksum(path):
    digest=hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda:handle.read(1024*1024),b""):digest.update(block)
    return digest.hexdigest()


def schema_fingerprint(frame):
    # CSV nullable columns can infer differently per bounded chunk when a chunk is
    # entirely null. The normalized column contract, not incidental inference, is
    # the stable cross-chunk schema identity.
    return stable_identity_hash({"columns":list(frame.columns),"schema_version":"normalized_decision_v1"})


def artifact_name(config):
    if config.artifact_format=="parquet":return "decisions.parquet"
    return "decisions.csv.gz" if config.compression=="gzip" else "decisions.csv"


def write_decision_artifact(frame,path,config):
    if len(frame)>config.maximum_output_rows_per_artifact:raise ValueError("decision artifact exceeds configured row limit")
    target=Path(path);target.parent.mkdir(parents=True,exist_ok=True);temporary=target.with_name(target.name+".tmp")
    if config.artifact_format=="parquet": frame.to_parquet(temporary,index=False)
    else: frame.to_csv(temporary,index=False,compression=config.compression,float_format="%.17g",lineterminator="\n")
    os.replace(temporary,target);return target,file_checksum(target)


def read_decision_artifact(path,artifact_format="csv",compression="infer"):
    target=Path(path)
    if not target.is_file():raise ArtifactCorruptionError(f"artifact missing: {target}")
    if artifact_format=="parquet":return pd.read_parquet(target)
    return pd.read_csv(target,compression=compression,parse_dates=["timestamp"])
