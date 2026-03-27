#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ALLOWED_RUN_ROOT = Path(".pack-state") / "autonomy-runs"
EXPORT_ROOT = Path("dist") / "exports" / "runtime-evidence"
RUN_SUMMARY_NAME = "run-summary.json"
LOOP_EVENTS_NAME = "loop-events.jsonl"
SUPPLEMENTARY_MEMORY_ROOT = Path(".pack-state") / "agent-memory"


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: JSON document must contain an object")
    return payload


def _dump_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"{json.dumps(payload, indent=2, sort_keys=True)}\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _isoformat_z() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _resolve_under(base: Path, candidate: str | Path) -> Path:
    path = Path(candidate)
    if path.is_absolute():
        raise ValueError(f"{candidate}: absolute paths are not allowed")
    resolved = (base / path).resolve()
    try:
        resolved.relative_to(base.resolve())
    except ValueError as exc:
        raise ValueError(f"{candidate}: path escapes the allowed base root") from exc
    return resolved


def _media_type(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".json":
        return "application/json"
    if suffix == ".jsonl":
        return "application/jsonl"
    return "text/plain; charset=utf-8"


def _select_run_files(pack_root: Path, run_id: str, include_logs: list[str]) -> tuple[Path, list[Path]]:
    run_root = (pack_root / ALLOWED_RUN_ROOT / run_id).resolve()
    if not run_root.exists():
        raise ValueError(f"{run_root}: run directory does not exist")
    try:
        run_root.relative_to((pack_root / ALLOWED_RUN_ROOT).resolve())
    except ValueError as exc:
        raise ValueError("run directory must stay inside .pack-state/autonomy-runs") from exc

    selected: list[Path] = []
    summary_path = run_root / RUN_SUMMARY_NAME
    if not summary_path.exists():
        raise ValueError(f"{summary_path}: selected run is missing run-summary.json")
    selected.append(summary_path)

    loop_events_path = run_root / LOOP_EVENTS_NAME
    if loop_events_path.exists():
        selected.append(loop_events_path)

    for include in include_logs:
        include_path = _resolve_under(run_root, include)
        if include_path.is_dir():
            raise ValueError(f"{include}: directory copies are not allowed")
        if not include_path.exists():
            raise ValueError(f"{include}: included log does not exist")
        selected.append(include_path)

    return run_root, selected


def _validate_loop_events(path: Path, run_id: str) -> None:
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        payload = json.loads(line)
        if not isinstance(payload, dict):
            raise ValueError(f"{path}:{line_number}: loop event must be a JSON object")
        if payload.get("run_id") != run_id:
            raise ValueError(f"{path}:{line_number}: loop event run_id does not match selected run")


def _copy_selected_artifacts(
    *,
    pack_root: Path,
    bundle_root: Path,
    run_root: Path,
    selected_files: list[Path],
) -> list[dict[str, Any]]:
    manifest: list[dict[str, Any]] = []
    for source_path in sorted({path.resolve() for path in selected_files}):
        if SUPPLEMENTARY_MEMORY_ROOT in source_path.parents:
            raise ValueError("runtime-memory artifacts are not exportable in v1")
        try:
            source_path.relative_to(run_root)
        except ValueError as exc:
            raise ValueError(f"{source_path}: v1 export allows only files under the selected run root") from exc

        relative_source = source_path.relative_to(pack_root).as_posix()
        relative_bundle = Path("artifacts") / Path(relative_source).relative_to(Path(".pack-state") / "autonomy-runs" / run_root.name)
        target_path = bundle_root / relative_bundle
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, target_path)
        manifest.append(
            {
                "bundle_path": relative_bundle.as_posix(),
                "source_pack_path": relative_source,
                "sha256": _sha256(target_path),
                "media_type": _media_type(source_path),
                "required": source_path.name == RUN_SUMMARY_NAME,
            }
        )
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Export bounded runtime evidence from a build pack.")
    parser.add_argument("--pack-root", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--exported-by", required=True)
    parser.add_argument("--output-dir", default=str(EXPORT_ROOT))
    parser.add_argument("--output", choices=("json",), default="json")
    parser.add_argument("--include-log", action="append", default=[])
    args = parser.parse_args(argv)

    pack_root = Path(args.pack_root).expanduser().resolve()
    if not pack_root.is_absolute():
        raise ValueError("--pack-root must resolve to an absolute path")
    output_dir = Path(args.output_dir)
    if output_dir.is_absolute():
        raise ValueError("--output-dir must be a relative path")

    pack_manifest = _load_json(pack_root / "pack.json")
    if pack_manifest.get("pack_kind") != "build_pack":
        raise ValueError("runtime evidence export only supports build packs")

    run_root, selected_files = _select_run_files(pack_root, args.run_id, args.include_log)
    run_summary = _load_json(run_root / RUN_SUMMARY_NAME)
    if run_summary.get("pack_id") != pack_manifest.get("pack_id"):
        raise ValueError("selected run pack_id does not match pack.json")
    if run_summary.get("run_id") != args.run_id:
        raise ValueError("selected run_id does not match run-summary.json")

    export_id = f"external-runtime-evidence-{args.run_id}-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    bundle_root = (pack_root / output_dir / export_id).resolve()
    try:
        bundle_root.relative_to(pack_root)
    except ValueError as exc:
        raise ValueError("--output-dir must stay under the pack root") from exc
    bundle_root.mkdir(parents=True, exist_ok=False)

    artifact_manifest = _copy_selected_artifacts(
        pack_root=pack_root,
        bundle_root=bundle_root,
        run_root=run_root,
        selected_files=selected_files,
    )
    loop_events_path = run_root / LOOP_EVENTS_NAME
    if loop_events_path.exists():
        _validate_loop_events(loop_events_path, args.run_id)
    final_snapshot = run_summary.get("final_snapshot", {})
    if not isinstance(final_snapshot, dict):
        final_snapshot = {}

    control_plane_mutations = {
        "readiness_updated": False,
        "work_state_updated": False,
        "eval_latest_updated": False,
        "deployment_updated": False,
        "registry_updated": False,
        "release_artifacts_updated": False,
    }
    bundle = {
        "schema_version": "external-runtime-evidence-bundle/v1",
        "export_id": export_id,
        "generated_at": _isoformat_z(),
        "pack_id": pack_manifest.get("pack_id"),
        "pack_kind": "build_pack",
        "run_id": args.run_id,
        "exported_by": args.exported_by,
        "bundle_root": str(bundle_root.relative_to(pack_root)),
        "source_runtime_roots": [str(run_root.relative_to(pack_root))],
        "authority_class": "supplementary_runtime_evidence",
        "control_plane_mutations": control_plane_mutations,
        "artifact_manifest": artifact_manifest,
        "summary": {
            "stop_reason": run_summary.get("stop_reason"),
            "started_at": run_summary.get("started_at"),
            "ended_at": run_summary.get("ended_at"),
            "resume_count": run_summary.get("resume_count"),
            "escalation_count": run_summary.get("escalation_count"),
            "task_completion_rate": run_summary.get("metrics", {}).get("task_completion_rate") if isinstance(run_summary.get("metrics"), dict) else None,
            "readiness_state_in_selected_run": final_snapshot.get("readiness_state"),
            "ready_for_deployment_in_selected_run": final_snapshot.get("ready_for_deployment"),
        },
    }
    _dump_json(bundle_root / "bundle.json", bundle)

    result = {
        "status": "completed",
        "generated_at": bundle["generated_at"],
        "export_id": export_id,
        "bundle_root": str(bundle_root.relative_to(pack_root)),
        "copied_artifact_paths": [entry["bundle_path"] for entry in artifact_manifest],
    }
    if args.output == "json":
        print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
