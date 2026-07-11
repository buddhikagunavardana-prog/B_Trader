def _config_hashes(manifest: dict) -> dict[str, str]:
    configs = manifest.get("config_snapshots", {}).get("configs", [])
    return {
        config.get("filename"): config.get("sha256")
        for config in configs
        if config.get("filename")
    }


def compare_run_manifests(base_manifest: dict, candidate_manifest: dict) -> dict:
    base_configs = _config_hashes(base_manifest)
    candidate_configs = _config_hashes(candidate_manifest)
    all_config_names = sorted(set(base_configs) | set(candidate_configs))
    changed_configs = [
        name
        for name in all_config_names
        if base_configs.get(name) != candidate_configs.get(name)
    ]

    base_stages = set(base_manifest.get("enabled_stages", []))
    candidate_stages = set(candidate_manifest.get("enabled_stages", []))
    metric_differences = {
        "task_usage": (
            base_manifest.get("task_usage", 0),
            candidate_manifest.get("task_usage", 0),
        ),
        "runtime_usage": (
            base_manifest.get("runtime_usage", 0.0),
            candidate_manifest.get("runtime_usage", 0.0),
        ),
    }
    artifact_differences = {
        "base_artifact_count": len(base_manifest.get("artifacts", [])),
        "candidate_artifact_count": len(candidate_manifest.get("artifacts", [])),
    }

    same_config = not changed_configs
    same_commit = (
        base_manifest.get("repository", {}).get("commit")
        == candidate_manifest.get("repository", {}).get("commit")
    )
    changed_stages = sorted(base_stages.symmetric_difference(candidate_stages))
    warnings = []
    if not same_config:
        warnings.append("Config snapshots differ")
    if not same_commit:
        warnings.append("Repository commit differs")

    conclusion = "MATCH" if same_config and same_commit and not changed_stages else "DIFFERENT"

    return {
        "base_run_id": base_manifest.get("run_id"),
        "candidate_run_id": candidate_manifest.get("run_id"),
        "same_config": same_config,
        "same_commit": same_commit,
        "changed_configs": changed_configs,
        "changed_stages": changed_stages,
        "metric_differences": metric_differences,
        "artifact_differences": artifact_differences,
        "warnings": warnings,
        "conclusion": conclusion,
    }
