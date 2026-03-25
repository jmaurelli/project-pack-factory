#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from factory_ops import (
    discover_pack,
    isoformat_z,
    read_now,
    relative_path,
    resolve_factory_root,
    schema_path,
    timestamp_token,
    validate_json_document,
    write_json,
)


SCHEMA_NAME = "autonomy-improvement-promotion-report.schema.json"
SCHEMA_VERSION = "autonomy-improvement-promotion-report/v1"
SURFACE_CHOICES = (
    "materializer_defaults",
    "source_template_tracking",
    "factory_root_discoverability",
    "factory_root_memory",
)


def _report_id(improvement_id: str) -> str:
    return f"{improvement_id}-{timestamp_token(read_now())}"


def _report_root(factory_root: Path, report_id: str) -> Path:
    return factory_root / ".pack-state" / "autonomy-improvement-promotions" / report_id


def _resolve_existing_path(factory_root: Path, raw_path: str) -> str:
    candidate = Path(raw_path).expanduser()
    if not candidate.is_absolute():
        candidate = (factory_root / candidate).resolve()
    else:
        candidate = candidate.resolve()
    if not candidate.exists():
        raise FileNotFoundError(f"path does not exist: {raw_path}")
    try:
        candidate.relative_to(factory_root)
    except ValueError as exc:
        raise ValueError(f"path must stay inside the factory root: {candidate}") from exc
    return relative_path(factory_root, candidate)


def _surface_record(
    *,
    factory_root: Path,
    surface_id: str,
    adoption_status: str,
    source_template_id: str | None,
) -> dict[str, Any]:
    if surface_id == "materializer_defaults":
        target_paths = ["tools/materialize_build_pack.py"]
        inheritance_effect = "factory_default_for_new_build_packs"
        notes = [
            "This is the main automatic inheritance path for future build-packs.",
            "When an autonomy improvement lands here, newly materialized build-packs receive it by default.",
        ]
    elif surface_id == "source_template_tracking":
        if not source_template_id:
            raise ValueError("source_template_tracking requires --source-template-id")
        target_paths = [
            f"templates/{source_template_id}/AGENTS.md",
            f"templates/{source_template_id}/pack.json",
            f"templates/{source_template_id}/project-context.md",
        ]
        inheritance_effect = "template_source_tracking"
        notes = [
            "This records whether the source template itself has been updated to describe or carry the improvement.",
            "Pending here means the improvement may still be inherited through factory tooling without being reflected directly in the template source.",
        ]
    elif surface_id == "factory_root_discoverability":
        target_paths = [
            "AGENTS.md",
            "README.md",
            "docs/specs/project-pack-factory/PROJECT-PACK-FACTORY-AUTONOMY-OPERATIONS-NOTE.md",
        ]
        inheritance_effect = "factory_root_default"
        notes = [
            "This captures whether a fresh factory-root agent can discover the improvement without entering a pack.",
        ]
    elif surface_id == "factory_root_memory":
        target_paths = [
            ".pack-state/agent-memory/latest-memory.json",
            "tools/refresh_factory_autonomy_memory.py",
        ]
        inheritance_effect = "factory_root_default"
        notes = [
            "This captures whether the improvement is reflected in the factory's own restart-memory handoff.",
        ]
    else:
        raise ValueError(f"unsupported surface_id: {surface_id}")

    resolved_paths = [_resolve_existing_path(factory_root, path) for path in target_paths]
    return {
        "surface_id": surface_id,
        "adoption_status": adoption_status,
        "inheritance_effect": inheritance_effect,
        "target_paths": resolved_paths,
        "notes": notes,
    }


def record_autonomy_improvement_promotion(
    *,
    factory_root: Path,
    improvement_id: str,
    summary: str,
    source_build_pack_id: str,
    source_template_id: str | None,
    proof_paths: list[str],
    adopted_surfaces: list[str],
    pending_surfaces: list[str],
    recorded_by: str,
) -> dict[str, Any]:
    discover_pack(factory_root, source_build_pack_id)
    if source_template_id is not None:
        discover_pack(factory_root, source_template_id)

    normalized_proof_paths = sorted({_resolve_existing_path(factory_root, path) for path in proof_paths})
    if not normalized_proof_paths:
        raise ValueError("at least one proof path is required")

    duplicate_surfaces = sorted(set(adopted_surfaces).intersection(pending_surfaces))
    if duplicate_surfaces:
        raise ValueError(f"surface cannot be both adopted and pending: {', '.join(duplicate_surfaces)}")

    surface_records: list[dict[str, Any]] = []
    for surface_id in adopted_surfaces:
        surface_records.append(
            _surface_record(
                factory_root=factory_root,
                surface_id=surface_id,
                adoption_status="adopted",
                source_template_id=source_template_id,
            )
        )
    for surface_id in pending_surfaces:
        surface_records.append(
            _surface_record(
                factory_root=factory_root,
                surface_id=surface_id,
                adoption_status="pending",
                source_template_id=source_template_id,
            )
        )

    surface_records.sort(key=lambda item: (item["adoption_status"], item["surface_id"]))
    adopted_labels = [record["surface_id"] for record in surface_records if record["adoption_status"] == "adopted"]
    pending_labels = [record["surface_id"] for record in surface_records if record["adoption_status"] == "pending"]
    operator_summary = (
        f"Proved autonomy improvement `{improvement_id}` from `{source_build_pack_id}`. "
        f"Adopted surfaces: {', '.join(adopted_labels) if adopted_labels else 'none'}. "
        f"Pending surfaces: {', '.join(pending_labels) if pending_labels else 'none'}."
    )

    report_id = _report_id(improvement_id)
    report_root = _report_root(factory_root, report_id)
    report_root.mkdir(parents=True, exist_ok=False)
    report_path = report_root / "promotion-report.json"
    payload = {
        "schema_version": SCHEMA_VERSION,
        "report_id": report_id,
        "generated_at": isoformat_z(read_now()),
        "improvement_id": improvement_id,
        "summary": summary,
        "operator_summary": operator_summary,
        "source_build_pack_id": source_build_pack_id,
        "source_template_id": source_template_id,
        "proof_paths": normalized_proof_paths,
        "surface_records": surface_records,
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
        "adopted_surfaces": adopted_labels,
        "pending_surfaces": pending_labels,
    }


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Record where a proven PackFactory autonomy improvement has been promoted into factory defaults.",
    )
    parser.add_argument("--factory-root", required=True)
    parser.add_argument("--improvement-id", required=True)
    parser.add_argument("--summary", required=True)
    parser.add_argument("--source-build-pack-id", required=True)
    parser.add_argument("--source-template-id")
    parser.add_argument("--proof-path", action="append", default=[])
    parser.add_argument("--adopted-surface", action="append", choices=SURFACE_CHOICES, default=[])
    parser.add_argument("--pending-surface", action="append", choices=SURFACE_CHOICES, default=[])
    parser.add_argument("--recorded-by", default="codex")
    parser.add_argument("--output", choices=("json",), default="json")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    result = record_autonomy_improvement_promotion(
        factory_root=resolve_factory_root(args.factory_root),
        improvement_id=args.improvement_id,
        summary=args.summary,
        source_build_pack_id=args.source_build_pack_id,
        source_template_id=args.source_template_id,
        proof_paths=list(args.proof_path),
        adopted_surfaces=list(args.adopted_surface),
        pending_surfaces=list(args.pending_surface),
        recorded_by=args.recorded_by,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
