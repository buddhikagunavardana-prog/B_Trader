import json
import time
from pathlib import Path

from src.research.pipeline.pipeline_reporter import save_json_report


STATUS_COMPLETED = "COMPLETED"
STATUS_PARTIAL = "PARTIAL"
STATUS_SKIPPED = "SKIPPED"
STATUS_FAILED = "FAILED"
STATUS_BLOCKED = "BLOCKED"

FAILURE_CODE = "CODE_FAILURE"
FAILURE_DATA = "DATA_FAILURE"
FAILURE_NETWORK = "NETWORK_FAILURE"
FAILURE_BINANCE_SSL = "BINANCE_SSL_FAILURE"
FAILURE_CONFIG = "CONFIG_FAILURE"
FAILURE_BUDGET = "BUDGET_EXCEEDED"
FAILURE_INSUFFICIENT_HISTORY = "INSUFFICIENT_HISTORY"
FAILURE_ARTIFACT = "ARTIFACT_FAILURE"
FAILURE_UNKNOWN = "UNKNOWN_FAILURE"


def now_utc() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def classify_failure(error: Exception) -> str:
    message = str(error).lower()
    if "ssl" in message:
        return FAILURE_BINANCE_SSL
    if "network" in message or "connection" in message or "timeout" in message:
        return FAILURE_NETWORK
    if "config" in message or "missing config" in message:
        return FAILURE_CONFIG
    if "budget" in message:
        return FAILURE_BUDGET
    if "history" in message or "not enough data" in message:
        return FAILURE_INSUFFICIENT_HISTORY
    if "artifact" in message or "report not found" in message:
        return FAILURE_ARTIFACT
    if "data" in message or "ohlcv" in message or "cache" in message:
        return FAILURE_DATA
    return FAILURE_UNKNOWN


def make_artifact(
    path: str | Path,
    name: str,
    producer_stage: str,
    artifact_type: str,
    required: bool = True,
    metadata: dict | None = None,
) -> dict:
    return {
        "name": name,
        "artifact_type": artifact_type,
        "path": str(path),
        "producer_stage": producer_stage,
        "schema_version": "1",
        "required": required,
        "status": "CREATED" if Path(path).exists() else "MISSING",
        "created_at": now_utc(),
        "metadata": metadata or {},
    }


def stage_payload(
    stage_name: str,
    message: str,
    task_usage: int = 1,
    artifacts: list[dict] | None = None,
    metrics: dict | None = None,
    warnings: list[str] | None = None,
    errors: list[str] | None = None,
    status: str = STATUS_COMPLETED,
    failure_type: str | None = None,
    metadata: dict | None = None,
) -> dict:
    return {
        "message": message,
        "task_usage": int(task_usage),
        "artifacts": list(artifacts or []),
        "metadata": {
            "adapter_result": {
                "stage_name": stage_name,
                "status": status,
                "success": status in {STATUS_COMPLETED, STATUS_PARTIAL, STATUS_SKIPPED},
                "message": message,
                "task_usage": int(task_usage),
                "output_artifacts": list(artifacts or []),
                "metrics": metrics or {},
                "warnings": list(warnings or []),
                "errors": list(errors or []),
                "failure_type": failure_type,
                "metadata": metadata or {},
            }
        },
    }


def blocked_payload(stage_name: str, message: str, failure_type: str = FAILURE_ARTIFACT):
    return stage_payload(
        stage_name,
        message,
        task_usage=0,
        artifacts=[],
        errors=[message],
        status=STATUS_BLOCKED,
        failure_type=failure_type,
    )


def benchmark_settings(context) -> dict:
    return dict(context.metadata.get("benchmark", {}))


def configured_pairs(context) -> list[str]:
    benchmark = benchmark_settings(context)
    return list(benchmark.get("pairs") or ["BTCUSDT"])


def configured_timeframe(context) -> str:
    benchmark = benchmark_settings(context)
    timeframes = list(benchmark.get("timeframes") or ["15m"])
    return str(timeframes[0])


def configured_lookback(context) -> str:
    benchmark = benchmark_settings(context)
    if benchmark.get("mode") == "SMALL_BENCHMARK":
        return "1 year ago UTC"
    return "1 year ago UTC"


def write_stage_json(context, stage_name: str, payload: dict) -> Path:
    path = context.run_directory() / f"{stage_name}.json"
    save_json_report(payload, str(path))
    return path


def read_json(path: str | Path, default=None):
    path = Path(path)
    if not path.exists():
        return default
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def artifact_path_from_state(state, name: str) -> str | None:
    for artifact in reversed(state.artifact_manifest):
        if artifact.get("name") == name:
            return artifact.get("path")
    return None
