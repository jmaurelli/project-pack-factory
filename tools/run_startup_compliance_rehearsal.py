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

from factory_ops import isoformat_z, load_json, read_now, resolve_factory_root, schema_path, timestamp_token, validate_json_document, write_json
from run_multi_hop_autonomy_rehearsal import run_multi_hop_autonomy_rehearsal


REPORT_SCHEMA_NAME = "startup-compliance-rehearsal-report.schema.json"
REPORT_SCHEMA_VERSION = "startup-compliance-rehearsal-report/v1"
REHEARSAL_PREFIX = "startup-compliance-rehearsal"

ROOT_MARKER_CHECKS: dict[str, tuple[str, ...]] = {
    "AGENTS.md": (
        "remote Codex session management",
        "raw stdout/stderr",
        "PROJECT-PACK-FACTORY-AUTONOMY-STATE-BRIEF.md",
    ),
    "README.md": (
        "Remote Session Compliance",
        "raw stdout/stderr",
        "tools/import_external_runtime_evidence.py",
    ),
    "docs/specs/project-pack-factory/PROJECT-PACK-FACTORY-AUTONOMY-OPERATIONS-NOTE.md": (
        "Remote Session Compliance",
        "pack-local remote-session path",
        "raw stdout/stderr",
    ),
}

TEMPLATE_MARKER_CHECKS: dict[str, tuple[str, ...]] = {
    "templates/json-health-checker-template-pack/AGENTS.md": (
        "remote Codex session management",
        "tools/import_external_runtime_evidence.py",
    ),
    "templates/json-health-checker-template-pack/project-context.md": (
        "remote Codex session management",
        "raw stdout/stderr",
    ),
    "templates/json-health-checker-template-pack/pack.json": (
        "factory_startup_compliance",
        "remote-session compliance",
    ),
}

BUILD_PACK_MARKER_CHECKS: tuple[str, ...] = (
    "status/readiness.json.operator_hint_status",
    "status/work-state.json.branch_selection_hints",
    "remote Codex session management",
    "tools/import_external_runtime_evidence.py",
    "raw remote stdout/stderr",
)


def _load_object(path: Path) -> dict[str, Any]:
    payload = load_json(path)
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: JSON document must contain an object")
    return cast(dict[str, Any], payload)


def _rehearsal_id(target_build_pack_id: str) -> str:
    return f"{REHEARSAL_PREFIX}-{target_build_pack_id}-{timestamp_token(read_now())}"


def _rehearsal_root(factory_root: Path, rehearsal_id: str) -> Path:
    return factory_root / ".pack-state" / "startup-compliance-rehearsals" / rehearsal_id


def _verify_text_markers(path: Path, markers: tuple[str, ...]) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    missing = [marker for marker in markers if marker not in text]
    return {
        "path": str(path),
        "status": "pass" if not missing else "fail",
        "markers_checked": list(markers),
        "missing_markers": missing,
    }


def run_startup_compliance_rehearsal(
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
) -> dict[str, Any]:
    rehearsal_id = _rehearsal_id(target_build_pack_id)
    rehearsal_root = _rehearsal_root(factory_root, rehearsal_id)
    rehearsal_root.mkdir(parents=True, exist_ok=False)

    root_marker_checks = {
        relative_path: _verify_text_markers(factory_root / relative_path, markers)
        for relative_path, markers in ROOT_MARKER_CHECKS.items()
    }
    template_marker_checks = {
        relative_path: _verify_text_markers(factory_root / relative_path, markers)
        for relative_path, markers in TEMPLATE_MARKER_CHECKS.items()
    }
    for relative_path, result in {**root_marker_checks, **template_marker_checks}.items():
        if result["status"] != "pass":
            missing = ", ".join(cast(list[str], result["missing_markers"]))
            raise ValueError(f"{factory_root / relative_path}: startup-compliance rehearsal missing required markers: {missing}")

    multi_hop_result = run_multi_hop_autonomy_rehearsal(
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

    build_pack_root = factory_root / "build-packs" / target_build_pack_id
    build_pack_agents_path = build_pack_root / "AGENTS.md"
    build_pack_marker_check = _verify_text_markers(build_pack_agents_path, BUILD_PACK_MARKER_CHECKS)
    if build_pack_marker_check["status"] != "pass":
        missing = ", ".join(cast(list[str], build_pack_marker_check["missing_markers"]))
        raise ValueError(f"{build_pack_agents_path}: startup-compliance rehearsal missing required markers: {missing}")

    final_readiness = _load_object(build_pack_root / "status/readiness.json")
    latest_memory = _load_object(build_pack_root / ".pack-state/agent-memory/latest-memory.json")
    report = {
        "schema_version": REPORT_SCHEMA_VERSION,
        "rehearsal_id": rehearsal_id,
        "generated_at": isoformat_z(read_now()),
        "status": "completed",
        "source_template_id": source_template_id,
        "target_build_pack_id": target_build_pack_id,
        "target_build_pack_root": str(build_pack_root),
        "remote_target_label": remote_target_label,
        "remote_host": remote_host,
        "remote_user": remote_user,
        "root_marker_checks": root_marker_checks,
        "template_marker_checks": template_marker_checks,
        "build_pack_marker_check": build_pack_marker_check,
        "multi_hop_rehearsal_result": multi_hop_result,
        "final_readiness": final_readiness,
        "latest_memory": latest_memory,
    }
    report_path = rehearsal_root / "rehearsal-report.json"
    write_json(report_path, report)
    errors = validate_json_document(report_path, schema_path(factory_root, REPORT_SCHEMA_NAME))
    if errors:
        raise ValueError("; ".join(errors))
    return {
        "status": "completed",
        "rehearsal_id": rehearsal_id,
        "report_path": str(report_path),
        "target_build_pack_id": target_build_pack_id,
        "target_build_pack_root": str(build_pack_root),
        "final_readiness_state": final_readiness.get("readiness_state"),
        "final_ready_for_deployment": final_readiness.get("ready_for_deployment"),
        "latest_memory_run_id": latest_memory.get("selected_run_id"),
    }


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a PackFactory startup-compliance rehearsal on a fresh build-pack.")
    parser.add_argument("--factory-root", required=True)
    parser.add_argument("--source-template-id", default="json-health-checker-template-pack")
    parser.add_argument("--target-build-pack-id", required=True)
    parser.add_argument("--target-display-name", required=True)
    parser.add_argument("--target-version", default="0.1.0")
    parser.add_argument("--target-revision", default="startup-compliance-v1")
    parser.add_argument("--remote-target-label", required=True)
    parser.add_argument("--remote-host", required=True)
    parser.add_argument("--remote-user", required=True)
    parser.add_argument("--actor", default="codex")
    parser.add_argument("--output", choices=("json",), default="json")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    result = run_startup_compliance_rehearsal(
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
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
