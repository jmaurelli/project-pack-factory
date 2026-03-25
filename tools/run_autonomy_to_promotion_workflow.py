#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, cast

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from factory_ops import discover_pack, isoformat_z, load_json, read_now, resolve_factory_root, timestamp_token, write_json
from promote_build_pack import promote_build_pack
from run_multi_hop_autonomy_rehearsal import run_multi_hop_autonomy_rehearsal


WORKFLOW_PREFIX = "autonomy-to-promotion-workflow"
DEFAULT_RELEASE_ARTIFACT_PATHS = (
    "src/",
    "tests/",
    "contracts/",
    "docs/specs/",
    "benchmarks/active-set.json",
    "eval/latest/index.json",
)


def _load_object(path: Path) -> dict[str, Any]:
    payload = load_json(path)
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: JSON document must contain an object")
    return cast(dict[str, Any], payload)


def _workflow_id(target_build_pack_id: str) -> str:
    return f"{WORKFLOW_PREFIX}-{target_build_pack_id}-{timestamp_token(read_now())}"


def _workflow_root(factory_root: Path, workflow_id: str) -> Path:
    return factory_root / ".pack-state" / "autonomy-to-promotion-workflows" / workflow_id


def _release_id(target_build_pack_id: str, explicit_release_id: str | None) -> str:
    if explicit_release_id and explicit_release_id.strip():
        return explicit_release_id.strip()
    return f"{target_build_pack_id}-r1"


def _release_artifact_paths(pack_root: Path) -> list[str]:
    artifact_paths: list[str] = []
    for candidate in DEFAULT_RELEASE_ARTIFACT_PATHS:
        if (pack_root / candidate.rstrip("/")).exists():
            artifact_paths.append(candidate)
    return artifact_paths or ["src/"]


def _source_template_fields(pack_root: Path, manifest: dict[str, Any]) -> tuple[str, str]:
    source_template_id = manifest.get("source_template_id")
    source_template_revision = manifest.get("source_template_revision")
    if isinstance(source_template_id, str) and source_template_id and isinstance(source_template_revision, str) and source_template_revision:
        return source_template_id, source_template_revision

    lineage_path = pack_root / "lineage/source-template.json"
    if not lineage_path.exists():
        raise ValueError("build pack is missing lineage/source-template.json needed for release preparation")
    lineage = _load_object(lineage_path)
    lineage_template_id = lineage.get("source_template_id")
    lineage_template_revision = lineage.get("source_template_revision")
    if not isinstance(lineage_template_id, str) or not lineage_template_id:
        raise ValueError("lineage/source-template.json is missing source_template_id")
    if not isinstance(lineage_template_revision, str) or not lineage_template_revision:
        raise ValueError("lineage/source-template.json is missing source_template_revision")
    return lineage_template_id, lineage_template_revision


def _prepare_release(*, pack_root: Path, release_id: str) -> dict[str, Any]:
    manifest = _load_object(pack_root / "pack.json")
    pack_id = str(manifest["pack_id"])
    source_template_id, source_template_revision = _source_template_fields(pack_root, manifest)
    built_at = isoformat_z(read_now())
    artifact_paths = _release_artifact_paths(pack_root)
    release = {
        "schema_version": "pack-release/v1",
        "build_pack_id": pack_id,
        "release_id": release_id,
        "source_template_id": source_template_id,
        "source_template_revision": source_template_revision,
        "built_at": built_at,
        "release_state": "testing",
        "artifact_paths": artifact_paths,
    }
    release_path = pack_root / "dist/releases" / release_id / "release.json"
    candidate_path = pack_root / "dist/candidates" / release_id / "release.json"
    write_json(release_path, release)
    write_json(candidate_path, release)
    return {
        "status": "completed",
        "release_id": release_id,
        "built_at": built_at,
        "release_path": str(release_path),
        "candidate_path": str(candidate_path),
        "artifact_paths": artifact_paths,
    }


def _promotion_request(
    *,
    build_pack_id: str,
    target_environment: str,
    release_id: str,
    promoted_by: str,
    promotion_reason: str,
    verification_timestamp: str,
) -> dict[str, Any]:
    return {
        "schema_version": "build-pack-promotion-request/v1",
        "build_pack_id": build_pack_id,
        "target_environment": target_environment,
        "release_id": release_id,
        "promoted_by": promoted_by,
        "promotion_reason": promotion_reason,
        "verification_timestamp": verification_timestamp,
    }


def _final_state(pack_root: Path) -> dict[str, Any]:
    return {
        "readiness": _load_object(pack_root / "status/readiness.json"),
        "work_state": _load_object(pack_root / "status/work-state.json"),
        "deployment": _load_object(pack_root / "status/deployment.json"),
        "latest_memory": _load_object(pack_root / ".pack-state/agent-memory/latest-memory.json"),
    }


def run_autonomy_to_promotion_workflow(
    *,
    factory_root: Path,
    source_template_id: str,
    target_build_pack_id: str,
    target_display_name: str,
    target_version: str,
    target_revision: str,
    remote_target_label: str,
    remote_host: str,
    remote_user: str,
    actor: str,
    target_environment: str,
    release_id: str | None,
    skip_promotion: bool,
) -> dict[str, Any]:
    workflow_id = _workflow_id(target_build_pack_id)
    workflow_root = _workflow_root(factory_root, workflow_id)
    workflow_root.mkdir(parents=True, exist_ok=False)

    rehearsal_result = run_multi_hop_autonomy_rehearsal(
        factory_root=factory_root,
        source_template_id=source_template_id,
        target_build_pack_id=target_build_pack_id,
        target_display_name=target_display_name,
        target_version=target_version,
        target_revision=target_revision,
        remote_target_label=remote_target_label,
        remote_host=remote_host,
        remote_user=remote_user,
        actor=actor,
    )

    target_pack = discover_pack(factory_root, target_build_pack_id)
    if target_pack.pack_kind != "build_pack":
        raise ValueError(f"{target_build_pack_id} is not a build_pack")

    resolved_release_id = _release_id(target_build_pack_id, release_id)
    release_result = _prepare_release(pack_root=target_pack.pack_root, release_id=resolved_release_id)
    promotion_request = _promotion_request(
        build_pack_id=target_build_pack_id,
        target_environment=target_environment,
        release_id=resolved_release_id,
        promoted_by=actor,
        promotion_reason="Run the factory-default autonomy-to-promotion workflow after a successful multi-hop autonomy rehearsal.",
        verification_timestamp=str(release_result["built_at"]),
    )
    promotion_request_path = workflow_root / "promotion-request.json"
    write_json(promotion_request_path, promotion_request)

    promotion_result: dict[str, Any] | None = None
    if not skip_promotion:
        promotion_result = promote_build_pack(factory_root, promotion_request)

    final_state = _final_state(target_pack.pack_root)
    report = {
        "schema_version": "autonomy-to-promotion-workflow-report/v1",
        "workflow_id": workflow_id,
        "generated_at": isoformat_z(read_now()),
        "status": "completed",
        "source_template_id": source_template_id,
        "target_build_pack_id": target_build_pack_id,
        "target_build_pack_root": str(target_pack.pack_root),
        "remote_target_label": remote_target_label,
        "remote_host": remote_host,
        "remote_user": remote_user,
        "target_environment": target_environment,
        "skip_promotion": skip_promotion,
        "rehearsal_result": rehearsal_result,
        "release_result": release_result,
        "promotion_request_path": str(promotion_request_path),
        "promotion_result": promotion_result,
        "final_state": final_state,
    }
    report_path = workflow_root / "workflow-report.json"
    write_json(report_path, report)
    return {
        "status": "completed",
        "workflow_id": workflow_id,
        "report_path": str(report_path),
        "target_build_pack_id": target_build_pack_id,
        "release_id": resolved_release_id,
        "promotion_status": None if promotion_result is None else promotion_result.get("status"),
        "promotion_report_path": None if promotion_result is None else promotion_result.get("promotion_report_path"),
        "final_readiness_state": final_state["readiness"].get("readiness_state"),
        "final_ready_for_deployment": final_state["readiness"].get("ready_for_deployment"),
        "final_deployment_state": final_state["deployment"].get("deployment_state"),
        "latest_memory_run_id": final_state["latest_memory"].get("selected_run_id"),
    }


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the factory-default autonomy-to-promotion workflow on a fresh build-pack.",
    )
    parser.add_argument("--factory-root", required=True)
    parser.add_argument("--source-template-id", default="json-health-checker-template-pack")
    parser.add_argument("--target-build-pack-id", required=True)
    parser.add_argument("--target-display-name", required=True)
    parser.add_argument("--target-version", default="0.1.0")
    parser.add_argument("--target-revision", default="autonomy-to-promotion-v1")
    parser.add_argument("--remote-target-label", required=True)
    parser.add_argument("--remote-host", required=True)
    parser.add_argument("--remote-user", required=True)
    parser.add_argument("--target-environment", default="testing", choices=("testing", "staging", "production"))
    parser.add_argument("--release-id")
    parser.add_argument("--skip-promotion", action="store_true")
    parser.add_argument("--actor", default="codex")
    parser.add_argument("--output", choices=("json",), default="json")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    result = run_autonomy_to_promotion_workflow(
        factory_root=resolve_factory_root(args.factory_root),
        source_template_id=args.source_template_id,
        target_build_pack_id=args.target_build_pack_id,
        target_display_name=args.target_display_name,
        target_version=args.target_version,
        target_revision=args.target_revision,
        remote_target_label=args.remote_target_label,
        remote_host=args.remote_host,
        remote_user=args.remote_user,
        actor=args.actor,
        target_environment=args.target_environment,
        release_id=args.release_id,
        skip_promotion=args.skip_promotion,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
