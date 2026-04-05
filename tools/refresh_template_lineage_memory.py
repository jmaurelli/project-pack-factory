#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from factory_ops import (
    REGISTRY_BUILD_PATH,
    REGISTRY_TEMPLATE_PATH,
    discover_pack,
    isoformat_z,
    load_json,
    read_now,
    relative_path,
    resolve_factory_root,
    schema_path,
    timestamp_token,
    validate_json_document,
    write_json,
)


SCHEMA_NAME = "template-lineage-memory.schema.json"
POINTER_SCHEMA_NAME = "template-lineage-memory-pointer.schema.json"
SOURCE_TOOL = "tools/refresh_template_lineage_memory.py"
MEMORY_DIR = Path(".pack-state") / "template-lineage-memory"
POINTER_NAME = "latest-memory.json"


def _load_object(path: Path) -> dict[str, Any]:
    payload = load_json(path)
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: JSON document must contain an object")
    return payload


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _capability_family(manifest: dict[str, Any]) -> str | None:
    notes = manifest.get("notes", [])
    if not isinstance(notes, list):
        return None
    for note in notes:
        if isinstance(note, str) and note.startswith("capability_family="):
            return note.split("=", 1)[1] or None
    return None


def _latest_distillation_path(factory_root: Path) -> str | None:
    root = factory_root / ".pack-state" / "autonomy-memory-distillations"
    if not root.exists():
        return None
    reports = sorted(root.glob("*/distillation-report.json"))
    if not reports:
        return None
    return relative_path(factory_root, reports[-1])


def _matching_distilled_lessons(
    *,
    factory_root: Path,
    latest_distillation_path: str | None,
    build_pack_ids: set[str],
) -> list[dict[str, Any]]:
    if not latest_distillation_path or not build_pack_ids:
        return []
    report_path = factory_root / latest_distillation_path
    if not report_path.exists():
        return []
    report = _load_object(report_path)
    lessons = report.get("lessons", [])
    if not isinstance(lessons, list):
        return []
    matched: list[dict[str, Any]] = []
    for lesson in lessons:
        if not isinstance(lesson, dict):
            continue
        source_build_pack_ids = lesson.get("source_build_pack_ids", [])
        if not isinstance(source_build_pack_ids, list):
            continue
        overlap = sorted(
            {
                build_pack_id
                for build_pack_id in source_build_pack_ids
                if isinstance(build_pack_id, str) and build_pack_id in build_pack_ids
            }
        )
        if not overlap:
            continue
        evidence_paths = [
            path
            for path in lesson.get("evidence_paths", [])
            if isinstance(path, str)
        ]
        matched.append(
            {
                "lesson_id": lesson.get("lesson_id"),
                "title": lesson.get("title"),
                "summary": lesson.get("summary"),
                "supporting_build_pack_ids": overlap,
                "evidence_paths": evidence_paths or [latest_distillation_path],
            }
        )
    return matched


def _matching_template_parity_reports(*, factory_root: Path, template_id: str) -> tuple[list[dict[str, Any]], str | None]:
    reports_root = factory_root / ".pack-state" / "template-parity-reports"
    if not reports_root.exists():
        return [], None

    matched: list[dict[str, Any]] = []
    latest_report_path: str | None = None
    for report_path in sorted(reports_root.glob("*/parity-report.json")):
        report = _load_object(report_path)
        if report.get("source_template_id") != template_id:
            continue
        report_relative = relative_path(factory_root, report_path)
        latest_report_path = report_relative
        proof_paths = [
            path
            for path in report.get("proof_paths", [])
            if isinstance(path, str)
        ]
        matched.append(
            {
                "report_id": report.get("report_id"),
                "runtime_build_pack_id": report.get("runtime_build_pack_id"),
                "parity_status": report.get("parity_status"),
                "summary": report.get("summary"),
                "proof_paths": proof_paths or [report_relative],
            }
        )
    return matched, latest_report_path


def refresh_template_lineage_memory(
    *,
    factory_root: Path,
    template_id: str,
    actor: str,
) -> dict[str, Any]:
    template = discover_pack(factory_root, template_id)
    if template.pack_kind != "template_pack":
        raise ValueError(f"{template_id}: template lineage memory only applies to template packs")

    build_registry_payload = _load_object(factory_root / REGISTRY_BUILD_PATH)
    build_entries = build_registry_payload.get("entries", [])
    if not isinstance(build_entries, list):
        raise ValueError("registry/build-packs.json: entries must be an array")

    source_build_pack_ids: list[str] = []
    active_build_pack_ids: list[str] = []
    retired_build_pack_ids: list[str] = []
    relevant_artifact_paths: list[str] = [
        relative_path(factory_root, factory_root / REGISTRY_TEMPLATE_PATH),
        relative_path(factory_root, factory_root / REGISTRY_BUILD_PATH),
    ]
    for entry in build_entries:
        if not isinstance(entry, dict):
            continue
        pack_id = entry.get("pack_id")
        pack_root_value = entry.get("pack_root")
        if not isinstance(pack_id, str) or not isinstance(pack_root_value, str):
            continue
        lineage_path = factory_root / pack_root_value / "lineage/source-template.json"
        if not lineage_path.exists():
            continue
        lineage = _load_object(lineage_path)
        if lineage.get("source_template_id") != template_id:
            continue
        source_build_pack_ids.append(pack_id)
        relevant_artifact_paths.append(relative_path(factory_root, lineage_path))
        if entry.get("active") is True:
            active_build_pack_ids.append(pack_id)
        if entry.get("retirement_state") == "retired":
            retired_build_pack_ids.append(pack_id)

    latest_distillation = _latest_distillation_path(factory_root)
    distilled_lessons = _matching_distilled_lessons(
        factory_root=factory_root,
        latest_distillation_path=latest_distillation,
        build_pack_ids=set(source_build_pack_ids),
    )
    template_parity_reports, latest_template_parity_report_path = _matching_template_parity_reports(
        factory_root=factory_root,
        template_id=template_id,
    )
    if latest_distillation:
        relevant_artifact_paths.append(latest_distillation)
    if latest_template_parity_report_path:
        relevant_artifact_paths.append(latest_template_parity_report_path)

    capability_family = _capability_family(template.manifest)
    generated_at = isoformat_z(read_now())
    memory_id = f"template-lineage-memory-{template_id}-{timestamp_token(read_now())}"
    memory_root = template.pack_root / MEMORY_DIR
    memory_root.mkdir(parents=True, exist_ok=True)

    summary = (
        f"Template `{template_id}` currently anchors {len(source_build_pack_ids)} known derived build-packs."
    )
    if distilled_lessons:
        summary += (
            f" {len(distilled_lessons)} factory-level distilled lesson(s) currently intersect this template family."
        )
    else:
        summary += " No factory-level distilled lessons intersect this template family yet."
    if template_parity_reports:
        summary += f" {len(template_parity_reports)} runtime-template parity report(s) now reference this template family."

    recommended_next_step = (
        "Use this template lineage memory when deciding whether the next proof should extend this template family or whether the lesson already belongs at the factory root."
    )
    if not source_build_pack_ids:
        recommended_next_step = (
            "Materialize the first build-pack from this template so the template family starts generating reusable lineage evidence."
        )

    payload = {
        "schema_version": "template-lineage-memory/v1",
        "generated_at": generated_at,
        "memory_id": memory_id,
        "template_id": template_id,
        "template_root": str(template.pack_root),
        "producer": actor,
        "capability_family": capability_family,
        "summary": summary,
        "source_build_pack_ids": sorted(source_build_pack_ids),
        "active_build_pack_ids": sorted(active_build_pack_ids),
        "retired_build_pack_ids": sorted(retired_build_pack_ids),
        "distilled_lessons": distilled_lessons,
        "latest_distillation_report_path": latest_distillation,
        "template_parity_reports": template_parity_reports,
        "latest_template_parity_report_path": latest_template_parity_report_path,
        "recommended_next_step": recommended_next_step,
        "discovery_entrypoints": [
            "AGENTS.md",
            "project-context.md",
            "pack.json",
            ".pack-state/template-lineage-memory/latest-memory.json",
            "registry/build-packs.json",
        ],
        "relevant_artifact_paths": sorted(dict.fromkeys(relevant_artifact_paths)),
        "status_snapshot": {
            "template_registry_path": relative_path(factory_root, factory_root / REGISTRY_TEMPLATE_PATH),
            "build_registry_path": relative_path(factory_root, factory_root / REGISTRY_BUILD_PATH),
            "build_pack_count": len(source_build_pack_ids),
            "active_build_pack_count": len(active_build_pack_ids),
            "retired_build_pack_count": len(retired_build_pack_ids),
            "template_parity_report_count": len(template_parity_reports),
        },
        "notes": [
            "This lineage memory is template-local advisory context, not canonical deployment or promotion truth.",
            "Use build-pack lineage plus proven factory artifacts to decide what this template family has already taught the factory.",
            "Runtime-template parity reports capture whether reusable runtime behavior has actually been backported into the template source.",
            "When a repeated lesson becomes template-agnostic, prefer promoting it into factory-level autonomy memory and distillation artifacts instead of overfitting the template.",
        ],
    }

    memory_path = memory_root / f"{memory_id}.json"
    write_json(memory_path, payload)
    errors = validate_json_document(memory_path, schema_path(factory_root, SCHEMA_NAME))
    if errors:
        raise ValueError("; ".join(errors))

    pointer_payload = {
        "schema_version": "template-lineage-memory-pointer/v1",
        "updated_at": generated_at,
        "template_id": template_id,
        "selected_memory_id": memory_id,
        "selected_generated_at": generated_at,
        "selected_memory_path": relative_path(template.pack_root, memory_path),
        "selected_memory_sha256": _sha256(memory_path),
        "source_kind": "template_lineage_memory_refresh",
        "source_tool": SOURCE_TOOL,
    }
    pointer_path = memory_root / POINTER_NAME
    write_json(pointer_path, pointer_payload)
    pointer_errors = validate_json_document(pointer_path, schema_path(factory_root, POINTER_SCHEMA_NAME))
    if pointer_errors:
        raise ValueError("; ".join(pointer_errors))

    return {
        "status": "completed",
        "template_id": template_id,
        "memory_id": memory_id,
        "memory_path": str(memory_path),
        "pointer_path": str(pointer_path),
        "source_build_pack_count": len(source_build_pack_ids),
        "distilled_lesson_count": len(distilled_lessons),
    }


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Refresh template-local lineage memory from derived build-pack evidence.")
    parser.add_argument("--factory-root", required=True)
    parser.add_argument("--template-id", required=True)
    parser.add_argument("--actor", default="codex")
    parser.add_argument("--output", choices=("json",), default="json")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    result = refresh_template_lineage_memory(
        factory_root=resolve_factory_root(args.factory_root),
        template_id=args.template_id,
        actor=args.actor,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
