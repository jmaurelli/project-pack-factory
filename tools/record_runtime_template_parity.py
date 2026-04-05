#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from factory_ops import (
    discover_pack,
    isoformat_z,
    path_is_relative_to,
    read_now,
    relative_path,
    resolve_factory_root,
    schema_path,
    timestamp_token,
    validate_json_document,
    write_json,
)


SCHEMA_NAME = "template-parity-report.schema.json"
SCHEMA_VERSION = "template-parity-report/v1"
PARITY_STATUSES = (
    "runtime_only",
    "template_backported",
    "template_backported_and_lineage_refreshed",
    "not_required",
)


def _resolve_existing_factory_path(factory_root: Path, raw_path: str) -> str:
    candidate = Path(raw_path).expanduser()
    if not candidate.is_absolute():
        candidate = (factory_root / candidate).resolve()
    else:
        candidate = candidate.resolve()
    if not candidate.exists():
        raise FileNotFoundError(f"path does not exist: {raw_path}")
    if not path_is_relative_to(candidate, factory_root.resolve()):
        raise ValueError(f"path must stay inside the factory root: {candidate}")
    return relative_path(factory_root, candidate)


def _resolve_existing_pack_path(factory_root: Path, pack_root: Path, raw_path: str) -> str:
    candidate = Path(raw_path).expanduser()
    if not candidate.is_absolute():
        candidate = (factory_root / candidate).resolve()
    else:
        candidate = candidate.resolve()
    if not candidate.exists():
        raise FileNotFoundError(f"path does not exist: {raw_path}")
    if not path_is_relative_to(candidate, pack_root.resolve()):
        raise ValueError(f"path must stay inside pack root `{relative_path(factory_root, pack_root)}`: {candidate}")
    return relative_path(factory_root, candidate)


def _report_id(improvement_id: str) -> str:
    return f"template-parity-{improvement_id}-{timestamp_token(read_now())}"


def _report_root(factory_root: Path, report_id: str) -> Path:
    return factory_root / ".pack-state" / "template-parity-reports" / report_id


def record_runtime_template_parity(
    *,
    factory_root: Path,
    runtime_build_pack_id: str,
    source_template_id: str,
    improvement_id: str,
    summary: str,
    parity_status: str,
    proof_paths: list[str],
    runtime_paths: list[str],
    template_paths: list[str],
    factory_context_paths: list[str],
    pending_follow_up: list[str],
    recorded_by: str,
) -> dict[str, object]:
    runtime_pack = discover_pack(factory_root, runtime_build_pack_id)
    if runtime_pack.pack_kind != "build_pack":
        raise ValueError(f"{runtime_build_pack_id}: runtime parity requires a build_pack")
    template_pack = discover_pack(factory_root, source_template_id)
    if template_pack.pack_kind != "template_pack":
        raise ValueError(f"{source_template_id}: runtime parity requires a template_pack")

    normalized_proof_paths = sorted({_resolve_existing_factory_path(factory_root, path) for path in proof_paths})
    normalized_runtime_paths = sorted(
        {_resolve_existing_pack_path(factory_root, runtime_pack.pack_root, path) for path in runtime_paths}
    )
    normalized_template_paths = sorted(
        {_resolve_existing_pack_path(factory_root, template_pack.pack_root, path) for path in template_paths}
    )
    normalized_factory_context_paths = sorted(
        {_resolve_existing_factory_path(factory_root, path) for path in factory_context_paths}
    )
    normalized_pending_follow_up = sorted({item.strip() for item in pending_follow_up if item.strip()})

    if not normalized_proof_paths:
        raise ValueError("at least one proof path is required")
    if not normalized_runtime_paths:
        raise ValueError("at least one runtime path is required")
    if not normalized_template_paths:
        raise ValueError("at least one template path is required")
    if not normalized_factory_context_paths:
        raise ValueError("at least one factory context path is required")

    operator_summary = (
        f"Recorded runtime-template parity `{parity_status}` for `{improvement_id}` from "
        f"`{runtime_build_pack_id}` to `{source_template_id}`. Runtime paths: {len(normalized_runtime_paths)}. "
        f"Template paths: {len(normalized_template_paths)}. Pending follow-up: "
        f"{', '.join(normalized_pending_follow_up) if normalized_pending_follow_up else 'none'}."
    )

    report_id = _report_id(improvement_id)
    report_root = _report_root(factory_root, report_id)
    report_root.mkdir(parents=True, exist_ok=False)
    report_path = report_root / "parity-report.json"
    payload = {
        "schema_version": SCHEMA_VERSION,
        "report_id": report_id,
        "generated_at": isoformat_z(read_now()),
        "runtime_build_pack_id": runtime_build_pack_id,
        "runtime_build_pack_root": str(runtime_pack.pack_root),
        "source_template_id": source_template_id,
        "source_template_root": str(template_pack.pack_root),
        "improvement_id": improvement_id,
        "summary": summary,
        "operator_summary": operator_summary,
        "parity_status": parity_status,
        "proof_paths": normalized_proof_paths,
        "runtime_paths": normalized_runtime_paths,
        "template_paths": normalized_template_paths,
        "factory_context_paths": normalized_factory_context_paths,
        "pending_follow_up": normalized_pending_follow_up,
        "recorded_by": recorded_by,
    }
    write_json(report_path, payload)
    errors = validate_json_document(report_path, schema_path(factory_root, SCHEMA_NAME))
    if errors:
        raise ValueError("; ".join(errors))
    return {
        "status": "completed",
        "report_id": report_id,
        "report_path": str(report_path),
        "parity_status": parity_status,
    }


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Record explicit runtime-template parity for a reusable behavior proved in a build-pack and mirrored into a source template.",
    )
    parser.add_argument("--factory-root", required=True)
    parser.add_argument("--runtime-build-pack-id", required=True)
    parser.add_argument("--source-template-id", required=True)
    parser.add_argument("--improvement-id", required=True)
    parser.add_argument("--summary", required=True)
    parser.add_argument("--parity-status", choices=PARITY_STATUSES, required=True)
    parser.add_argument("--proof-path", action="append", default=[])
    parser.add_argument("--runtime-path", action="append", default=[])
    parser.add_argument("--template-path", action="append", default=[])
    parser.add_argument("--factory-context-path", action="append", default=[])
    parser.add_argument("--pending-follow-up", action="append", default=[])
    parser.add_argument("--recorded-by", default="codex")
    parser.add_argument("--output", choices=("json",), default="json")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    result = record_runtime_template_parity(
        factory_root=resolve_factory_root(args.factory_root),
        runtime_build_pack_id=args.runtime_build_pack_id,
        source_template_id=args.source_template_id,
        improvement_id=args.improvement_id,
        summary=args.summary,
        parity_status=args.parity_status,
        proof_paths=list(args.proof_path),
        runtime_paths=list(args.runtime_path),
        template_paths=list(args.template_path),
        factory_context_paths=list(args.factory_context_path),
        pending_follow_up=list(args.pending_follow_up),
        recorded_by=args.recorded_by,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
