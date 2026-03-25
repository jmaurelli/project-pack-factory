#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from datetime import timedelta
from pathlib import Path
from typing import Any, Final, cast

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from factory_ops import (
    discover_pack,
    isoformat_z,
    load_json,
    remove_file,
    read_now,
    relative_path,
    resolve_factory_root,
    schema_path,
    timestamp_token,
    validate_json_document,
    write_json,
)

REQUEST_SCHEMA_NAME: Final[str] = "external-runtime-evidence-import-request.schema.json"
REPORT_SCHEMA_NAME: Final[str] = "external-runtime-evidence-import-report.schema.json"
BUNDLE_SCHEMA_NAME: Final[str] = "external-runtime-evidence-bundle.schema.json"
POINTER_SCHEMA_NAME: Final[str] = "autonomy-feedback-memory-pointer.schema.json"
REQUEST_SCHEMA_VERSION: Final[str] = "external-runtime-evidence-import-request/v1"
REPORT_SCHEMA_VERSION: Final[str] = "external-runtime-evidence-import-report/v1"
BUNDLE_SCHEMA_VERSION: Final[str] = "external-runtime-evidence-bundle/v1"
AUTHORITY_CLASS: Final[str] = "supplementary_runtime_evidence"
ALLOWED_ARTIFACT_ROOT: Final[str] = "artifacts"
RUN_SUMMARY_NAME: Final[str] = "run-summary.json"
LOOP_EVENTS_NAME: Final[str] = "loop-events.jsonl"
FEEDBACK_MEMORY_DIRNAME: Final[str] = "agent-memory"
LIVE_MEMORY_ROOT: Final[Path] = Path(".pack-state") / "agent-memory"
LATEST_MEMORY_POINTER_NAME: Final[str] = "latest-memory.json"
IMPORT_RUN_PREFIX: Final[str] = "import-external-runtime-evidence"


def _load_object(path: Path) -> dict[str, Any]:
    payload = load_json(path)
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: JSON document must contain an object")
    return cast(dict[str, Any], payload)


def _manual_validate_request(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required_keys = {
        "schema_version",
        "build_pack_id",
        "bundle_manifest_path",
        "import_reason",
        "imported_by",
    }
    extra_keys = sorted(set(payload) - required_keys)
    missing_keys = sorted(required_keys - set(payload))
    if missing_keys:
        errors.append(f"request is missing required keys: {', '.join(missing_keys)}")
    if extra_keys:
        errors.append(f"request contains unexpected keys: {', '.join(extra_keys)}")
    if payload.get("schema_version") != REQUEST_SCHEMA_VERSION:
        errors.append(
            f"request schema_version must be `{REQUEST_SCHEMA_VERSION}`"
        )
    for key in ("build_pack_id", "bundle_manifest_path", "import_reason", "imported_by"):
        value = payload.get(key)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"request field `{key}` must be a non-empty string")
    return errors


def _manual_validate_report(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required_keys = {
        "schema_version",
        "import_id",
        "generated_at",
        "status",
        "build_pack_id",
        "build_pack_root",
        "bundle_manifest_path",
        "import_reason",
        "imported_by",
        "hash_verification_status",
        "copied_artifact_paths",
        "warnings",
        "control_plane_mutations",
    }
    extra_keys = sorted(set(payload) - required_keys)
    missing_keys = sorted(required_keys - set(payload))
    if missing_keys:
        errors.append(f"report is missing required keys: {', '.join(missing_keys)}")
    if extra_keys:
        errors.append(f"report contains unexpected keys: {', '.join(extra_keys)}")
    if payload.get("schema_version") != REPORT_SCHEMA_VERSION:
        errors.append(
            f"report schema_version must be `{REPORT_SCHEMA_VERSION}`"
        )
    for key in (
        "import_id",
        "generated_at",
        "status",
        "build_pack_id",
        "build_pack_root",
        "bundle_manifest_path",
        "import_reason",
        "imported_by",
        "hash_verification_status",
    ):
        value = payload.get(key)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"report field `{key}` must be a non-empty string")
    copied_paths = payload.get("copied_artifact_paths")
    if not isinstance(copied_paths, list) or not copied_paths:
        errors.append("report field `copied_artifact_paths` must be a non-empty array")
    elif not all(isinstance(path, str) and path for path in copied_paths):
        errors.append("report field `copied_artifact_paths` must contain only non-empty strings")
    warnings = payload.get("warnings")
    if not isinstance(warnings, list):
        errors.append("report field `warnings` must be an array")
    elif not all(isinstance(item, str) for item in warnings):
        errors.append("report field `warnings` must contain only strings")
    mutations = payload.get("control_plane_mutations")
    if not isinstance(mutations, dict):
        errors.append("report field `control_plane_mutations` must be an object")
    else:
        expected_mutation_keys = {
            "eval_history_written",
            "readiness_updated",
            "work_state_updated",
            "eval_latest_updated",
            "deployment_updated",
            "registry_updated",
            "release_artifacts_updated",
        }
        extra_mutation_keys = sorted(set(mutations) - expected_mutation_keys)
        missing_mutation_keys = sorted(expected_mutation_keys - set(mutations))
        if missing_mutation_keys:
            errors.append(
                f"report field `control_plane_mutations` is missing keys: {', '.join(missing_mutation_keys)}"
            )
        if extra_mutation_keys:
            errors.append(
                f"report field `control_plane_mutations` contains unexpected keys: {', '.join(extra_mutation_keys)}"
            )
        for key in expected_mutation_keys:
            if key == "eval_history_written":
                if mutations.get(key) is not True:
                    errors.append("report field `control_plane_mutations.eval_history_written` must be true")
            elif mutations.get(key) is not False:
                errors.append(f"report field `control_plane_mutations.{key}` must be false")
    memory_intake = payload.get("memory_intake")
    if memory_intake is not None:
        if not isinstance(memory_intake, dict):
            errors.append("report field `memory_intake` must be an object when present")
        else:
            required_memory_keys = {
                "status",
                "promoted_memory_path",
                "latest_pointer_path",
                "selected_memory_id",
                "selected_run_id",
                "selected_memory_sha256",
                "source_bundle_path",
                "block_summary",
            }
            extra_memory_keys = sorted(set(memory_intake) - required_memory_keys)
            missing_memory_keys = sorted(required_memory_keys - set(memory_intake))
            if missing_memory_keys:
                errors.append(
                    f"report field `memory_intake` is missing keys: {', '.join(missing_memory_keys)}"
                )
            if extra_memory_keys:
                errors.append(
                    f"report field `memory_intake` contains unexpected keys: {', '.join(extra_memory_keys)}"
                )
            if memory_intake.get("status") not in {"activated", "promoted_only", "promoted", "not_present"}:
                errors.append(
                    "report field `memory_intake.status` must be `activated`, `promoted_only`, `promoted`, or `not_present`"
                )
            for key in (
                "promoted_memory_path",
                "latest_pointer_path",
                "selected_memory_id",
                "selected_run_id",
                "selected_memory_sha256",
                "source_bundle_path",
            ):
                value = memory_intake.get(key)
                if value is not None and (not isinstance(value, str) or not value):
                    errors.append(f"report field `memory_intake.{key}` must be null or a non-empty string")
            block_summary = memory_intake.get("block_summary")
            if block_summary is not None and not isinstance(block_summary, dict):
                errors.append("report field `memory_intake.block_summary` must be null or an object")
    return errors


def _validate_payload_or_schema(
    factory_root: Path,
    schema_name: str,
    payload: dict[str, Any],
    *,
    label: str,
    manual_validator,
) -> None:
    schema_file = schema_path(factory_root, schema_name)
    if schema_file.exists():
        temp_root = factory_root / ".pack-state" / "import-runtime-evidence-schema-validation"
        temp_path = temp_root / f"{label}.json"
        write_json(temp_path, payload)
        errors = validate_json_document(temp_path, schema_file)
        temp_path.unlink(missing_ok=True)
        if temp_path.parent.exists() and not any(temp_path.parent.iterdir()):
            temp_path.parent.rmdir()
        if errors:
            raise ValueError("; ".join(errors))
        return

    errors = manual_validator(payload)
    if errors:
        raise ValueError("; ".join(errors))


def _resolve_path_reference(base: Path, value: str, *, label: str) -> Path:
    candidate = Path(value).expanduser()
    if candidate.is_absolute():
        return candidate.resolve()
    resolved = (base / candidate).resolve()
    return resolved


def _validate_bundle_path(bundle_path: str) -> None:
    candidate = Path(bundle_path)
    if candidate.is_absolute():
        raise ValueError(f"{bundle_path}: absolute bundle paths are not allowed")
    parts = candidate.parts
    if not parts or parts[0] != ALLOWED_ARTIFACT_ROOT:
        raise ValueError(
            f"{bundle_path}: v1 export/import only allows artifacts under `{ALLOWED_ARTIFACT_ROOT}/`"
        )
    if any(part in {"..", "."} for part in parts):
        raise ValueError(f"{bundle_path}: path traversal is not allowed")
    if len(parts) == 2 and parts[1] in {RUN_SUMMARY_NAME, LOOP_EVENTS_NAME}:
        return
    if len(parts) == 3 and parts[1] == FEEDBACK_MEMORY_DIRNAME and parts[2].endswith(".json"):
        return
    if len(parts) >= 3 and parts[1] == "logs":
        return
    raise ValueError(
        f"{bundle_path}: v1 allows only `{ALLOWED_ARTIFACT_ROOT}/{RUN_SUMMARY_NAME}`, "
        f"`{ALLOWED_ARTIFACT_ROOT}/{LOOP_EVENTS_NAME}`, "
        f"`{ALLOWED_ARTIFACT_ROOT}/{FEEDBACK_MEMORY_DIRNAME}/*.json`, and `{ALLOWED_ARTIFACT_ROOT}/logs/*`"
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _validate_loop_events(path: Path, run_id: str) -> None:
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        payload = json.loads(line)
        if not isinstance(payload, dict):
            raise ValueError(f"{path}:{line_number}: loop event must be a JSON object")
        if payload.get("run_id") != run_id:
            raise ValueError(f"{path}:{line_number}: loop event run_id does not match selected run")


def _validate_feedback_memory(path: Path, run_id: str, pack_id: str) -> None:
    payload = _load_object(path)
    if payload.get("schema_version") != "autonomy-feedback-memory/v1":
        raise ValueError(f"{path}: feedback memory must set schema_version=autonomy-feedback-memory/v1")
    if payload.get("run_id") != run_id:
        raise ValueError(f"{path}: feedback memory run_id does not match selected run")
    if payload.get("pack_id") != pack_id:
        raise ValueError(f"{path}: feedback memory pack_id does not match target build pack")


def _validate_pointer_payload(factory_root: Path, payload: dict[str, Any]) -> None:
    _validate_payload_or_schema(
        factory_root,
        POINTER_SCHEMA_NAME,
        payload,
        label="autonomy-feedback-memory-pointer",
        manual_validator=lambda pointer_payload: [],
    )


def _promote_feedback_memory(
    *,
    target_pack,
    memory_artifact_path: Path,
    source_bundle_path: str,
) -> dict[str, Any]:
    memory_payload = _load_object(memory_artifact_path)
    memory_filename = memory_artifact_path.name
    live_memory_root = target_pack.pack_root / LIVE_MEMORY_ROOT
    live_memory_root.mkdir(parents=True, exist_ok=True)
    promoted_memory_path = live_memory_root / memory_filename
    shutil.copy2(memory_artifact_path, promoted_memory_path)
    promoted_memory_sha256 = _sha256(promoted_memory_path)
    promoted_memory_relpath = f"{LIVE_MEMORY_ROOT.as_posix()}/{memory_filename}"
    return {
        "status": "promoted",
        "promoted_memory_path": promoted_memory_relpath,
        "latest_pointer_path": None,
        "selected_memory_id": memory_payload.get("memory_id"),
        "selected_run_id": memory_payload.get("run_id"),
        "selected_memory_sha256": promoted_memory_sha256,
        "source_bundle_path": source_bundle_path,
        "block_summary": None,
    }


def _canonical_memory_alignment(pack_root: Path) -> dict[str, Any]:
    work_state = _load_object(pack_root / "status/work-state.json")
    readiness = _load_object(pack_root / "status/readiness.json")
    return {
        "active_task_id": work_state.get("active_task_id"),
        "next_recommended_task_id": work_state.get("next_recommended_task_id"),
        "final_readiness_state": readiness.get("readiness_state"),
        "ready_for_deployment": readiness.get("ready_for_deployment"),
    }


def _memory_matches_canonical(memory_payload: dict[str, Any], canonical_alignment: dict[str, Any]) -> bool:
    return (
        memory_payload.get("active_task_id") == canonical_alignment.get("active_task_id")
        and memory_payload.get("next_recommended_task_id") == canonical_alignment.get("next_recommended_task_id")
        and memory_payload.get("final_readiness_state") == canonical_alignment.get("final_readiness_state")
        and memory_payload.get("ready_for_deployment") == canonical_alignment.get("ready_for_deployment")
    )


def _memory_mismatch_details(memory_payload: dict[str, Any], canonical_alignment: dict[str, Any]) -> list[str]:
    details: list[str] = []
    for key in (
        "active_task_id",
        "next_recommended_task_id",
        "final_readiness_state",
        "ready_for_deployment",
    ):
        if memory_payload.get(key) == canonical_alignment.get(key):
            continue
        details.append(
            f"{key}: imported={memory_payload.get(key)!r} canonical={canonical_alignment.get(key)!r}"
        )
    return details


def _memory_block_summary(
    *,
    memory_payload: dict[str, Any],
    canonical_alignment: dict[str, Any],
) -> dict[str, Any] | None:
    if _memory_matches_canonical(memory_payload, canonical_alignment):
        return None
    mismatch_details = _memory_mismatch_details(memory_payload, canonical_alignment)
    if any(detail.startswith("active_task_id") or detail.startswith("next_recommended_task_id") for detail in mismatch_details):
        artifact_kind = "work_state"
        artifact_path = "status/work-state.json"
    else:
        artifact_kind = "readiness"
        artifact_path = "status/readiness.json"
    return {
        "status": "blocked",
        "reason": "memory_not_activated_due_to_canonical_mismatch",
        "summary": "Imported feedback memory was preserved but not activated because it no longer matched the pack's canonical local state.",
        "blocking_artifact_kind": artifact_kind,
        "blocking_artifact_path": artifact_path,
        "recommended_recovery_action": "Run the imported runtime-state reconcile workflow if you want to adopt the returned remote state; otherwise continue from the current active latest-memory pointer.",
        "details": mismatch_details,
    }


def _select_active_memory_candidate(pack_root: Path, pack_id: str) -> tuple[Path, dict[str, Any], str] | None:
    memory_root = pack_root / LIVE_MEMORY_ROOT
    canonical_alignment = _canonical_memory_alignment(pack_root)
    candidates: list[tuple[str, str, Path, dict[str, Any], str]] = []
    for path in sorted(memory_root.glob("autonomy-feedback-*.json")):
        payload = _load_object(path)
        if payload.get("schema_version") != "autonomy-feedback-memory/v1":
            continue
        if payload.get("pack_id") != pack_id:
            continue
        if not _memory_matches_canonical(payload, canonical_alignment):
            continue
        generated_at = payload.get("generated_at")
        if not isinstance(generated_at, str) or not generated_at:
            continue
        candidates.append((generated_at, path.name, path, payload, _sha256(path)))
    if not candidates:
        return None
    _generated_at, _name, selected_path, selected_payload, selected_sha256 = max(candidates)
    return selected_path, selected_payload, selected_sha256


def _refresh_latest_memory_pointer(
    *,
    factory_root: Path,
    target_pack,
    import_generated_at: str,
    import_id: str,
    promoted_memory_path: Path,
    source_bundle_path: str,
) -> dict[str, Any]:
    pointer_path = target_pack.pack_root / LIVE_MEMORY_ROOT / LATEST_MEMORY_POINTER_NAME
    selected = _select_active_memory_candidate(target_pack.pack_root, target_pack.pack_id)
    if selected is None:
        remove_file(pointer_path)
        return {
            "status": "promoted_only",
            "latest_pointer_path": None,
        }

    selected_path, selected_payload, selected_sha256 = selected
    selected_memory_relpath = relative_path(target_pack.pack_root, selected_path)
    pointer_payload = {
        "schema_version": "autonomy-feedback-memory-pointer/v1",
        "updated_at": import_generated_at,
        "pack_id": target_pack.pack_id,
        "selected_memory_id": selected_payload.get("memory_id"),
        "selected_run_id": selected_payload.get("run_id"),
        "selected_generated_at": selected_payload.get("generated_at"),
        "selected_memory_path": selected_memory_relpath,
        "selected_memory_sha256": selected_sha256,
        "source_kind": "imported_external_runtime_evidence" if selected_path == promoted_memory_path else "local_autonomy_run",
        "source_import_id": import_id if selected_path == promoted_memory_path else None,
        "source_artifact_path": source_bundle_path if selected_path == promoted_memory_path else None,
        "source_import_report_path": f"eval/history/{import_id}/import-report.json" if selected_path == promoted_memory_path else None,
    }
    _validate_pointer_payload(factory_root, pointer_payload)
    write_json(pointer_path, pointer_payload)
    return {
        "status": "activated" if selected_path == promoted_memory_path else "promoted_only",
        "latest_pointer_path": f"{LIVE_MEMORY_ROOT.as_posix()}/{LATEST_MEMORY_POINTER_NAME}",
    }


def _validate_artifact_manifest(
    *,
    bundle_manifest: dict[str, Any],
    bundle_root: Path,
    run_id: str,
    pack_id: str,
) -> list[tuple[Path, Path, bool]]:
    artifact_manifest = bundle_manifest.get("artifact_manifest", [])
    if not isinstance(artifact_manifest, list) or not artifact_manifest:
        raise ValueError("bundle.json artifact_manifest must be a non-empty array")

    selected: list[tuple[Path, Path, bool]] = []
    seen_bundle_paths: set[str] = set()
    required_run_summary_found = False
    feedback_memory_count = 0

    for entry in artifact_manifest:
        if not isinstance(entry, dict):
            raise ValueError("bundle.json artifact_manifest entries must be objects")
        required_keys = {"bundle_path", "source_pack_path", "sha256", "media_type", "required"}
        extra_keys = sorted(set(entry) - required_keys)
        missing_keys = sorted(required_keys - set(entry))
        if missing_keys:
            raise ValueError(
                f"bundle.json artifact_manifest entry missing keys: {', '.join(missing_keys)}"
            )
        if extra_keys:
            raise ValueError(
                f"bundle.json artifact_manifest entry contains unexpected keys: {', '.join(extra_keys)}"
            )

        bundle_path = entry["bundle_path"]
        source_pack_path = entry["source_pack_path"]
        sha256 = entry["sha256"]
        media_type = entry["media_type"]
        required = entry["required"]
        if not all(isinstance(value, str) and value for value in (bundle_path, source_pack_path, sha256, media_type)):
            raise ValueError("bundle.json artifact_manifest path and hash fields must be non-empty strings")
        if not isinstance(required, bool):
            raise ValueError("bundle.json artifact_manifest required field must be boolean")
        if bundle_path in seen_bundle_paths:
            raise ValueError(f"bundle.json artifact_manifest has duplicate bundle_path `{bundle_path}`")
        seen_bundle_paths.add(bundle_path)

        _validate_bundle_path(bundle_path)
        source_path = (bundle_root / bundle_path).resolve()
        try:
            source_path.relative_to(bundle_root.resolve())
        except ValueError as exc:
            raise ValueError(f"{bundle_path}: bundle path escapes the bundle root") from exc
        if not source_path.exists():
            raise ValueError(f"{bundle_path}: declared artifact does not exist in the bundle")
        if source_path.is_dir():
            raise ValueError(f"{bundle_path}: directory copies are not allowed")
        if _sha256(source_path) != sha256:
            raise ValueError(f"{bundle_path}: sha256 hash does not match the declared artifact")
        if bundle_path == f"{ALLOWED_ARTIFACT_ROOT}/{RUN_SUMMARY_NAME}":
            required_run_summary_found = True
            if required is not True:
                raise ValueError("run-summary artifact must be marked required=true")
        elif required:
            raise ValueError("only run-summary.json may be required in v1")

        if bundle_path == f"{ALLOWED_ARTIFACT_ROOT}/{LOOP_EVENTS_NAME}":
            _validate_loop_events(source_path, run_id)
        elif Path(bundle_path).parts[1] == FEEDBACK_MEMORY_DIRNAME:
            feedback_memory_count += 1
            _validate_feedback_memory(source_path, run_id, pack_id)

        selected.append((source_path, Path(bundle_path), required))

    if not required_run_summary_found:
        raise ValueError("bundle.json must include required artifacts/run-summary.json")
    if feedback_memory_count > 1:
        raise ValueError("bundle.json may include at most one feedback-memory artifact")

    run_summary_entry = next(
        (entry for entry in artifact_manifest if entry.get("bundle_path") == f"{ALLOWED_ARTIFACT_ROOT}/{RUN_SUMMARY_NAME}"),
        None,
    )
    if run_summary_entry is None:
        raise ValueError("bundle.json must include artifacts/run-summary.json")
    if run_summary_entry.get("required") is not True:
        raise ValueError("artifacts/run-summary.json must be required")

    return selected


def _make_import_id(moment: Any) -> str:
    return f"{IMPORT_RUN_PREFIX}-{timestamp_token(moment)}"


def _write_import_report_schema_validated(
    *,
    factory_root: Path,
    report_path: Path,
    report_payload: dict[str, Any],
) -> None:
    _validate_payload_or_schema(
        factory_root,
        REPORT_SCHEMA_NAME,
        report_payload,
        label="import-report",
        manual_validator=_manual_validate_report,
    )
    write_json(report_path, report_payload)


def import_external_runtime_evidence(
    factory_root: Path,
    request: dict[str, Any],
    *,
    request_file_dir: Path,
) -> dict[str, Any]:
    build_pack_id = str(request["build_pack_id"])
    bundle_manifest_path = _resolve_path_reference(
        request_file_dir,
        str(request["bundle_manifest_path"]),
        label="bundle_manifest_path",
    )
    import_reason = str(request["import_reason"])
    imported_by = str(request["imported_by"])

    if bundle_manifest_path.name != "bundle.json":
        raise ValueError("bundle_manifest_path must point to bundle.json")
    if not bundle_manifest_path.exists():
        raise FileNotFoundError(f"bundle manifest does not exist: {bundle_manifest_path}")

    target_pack = discover_pack(factory_root, build_pack_id)
    if target_pack.pack_kind != "build_pack":
        raise ValueError(f"{build_pack_id} is not a build_pack")

    bundle_manifest = _load_object(bundle_manifest_path)
    _validate_payload_or_schema(
        factory_root,
        BUNDLE_SCHEMA_NAME,
        bundle_manifest,
        label="bundle",
        manual_validator=lambda payload: [],
    )

    if bundle_manifest.get("schema_version") != BUNDLE_SCHEMA_VERSION:
        raise ValueError(f"bundle.json schema_version must be `{BUNDLE_SCHEMA_VERSION}`")
    if bundle_manifest.get("pack_kind") != "build_pack":
        raise ValueError("bundle.json pack_kind must be build_pack")
    if bundle_manifest.get("authority_class") != AUTHORITY_CLASS:
        raise ValueError(
            "bundle.json authority_class must be supplementary_runtime_evidence"
        )

    control_plane_mutations = bundle_manifest.get("control_plane_mutations", {})
    if not isinstance(control_plane_mutations, dict):
        raise ValueError("bundle.json control_plane_mutations must be an object")
    for key in (
        "readiness_updated",
        "work_state_updated",
        "eval_latest_updated",
        "deployment_updated",
        "registry_updated",
        "release_artifacts_updated",
    ):
        if control_plane_mutations.get(key) is not False:
            raise ValueError(f"bundle.json control_plane_mutations.{key} must be false")

    if bundle_manifest.get("pack_id") != build_pack_id:
        raise ValueError("bundle.json pack_id does not match the target build pack")
    if bundle_manifest.get("run_id") is None or not isinstance(bundle_manifest.get("run_id"), str):
        raise ValueError("bundle.json run_id must be a string")

    run_id = str(bundle_manifest["run_id"])
    bundle_root = bundle_manifest_path.parent.resolve()
    if not bundle_root.exists():
        raise FileNotFoundError(f"bundle root does not exist: {bundle_root}")

    if not isinstance(bundle_manifest.get("bundle_root"), str) or not bundle_manifest["bundle_root"]:
        raise ValueError("bundle.json bundle_root must be a non-empty string")
    if not isinstance(bundle_manifest.get("exported_by"), str) or not bundle_manifest["exported_by"]:
        raise ValueError("bundle.json exported_by must be a non-empty string")

    artifact_entries = _validate_artifact_manifest(
        bundle_manifest=bundle_manifest,
        bundle_root=bundle_root,
        run_id=run_id,
        pack_id=build_pack_id,
    )

    run_summary_path = bundle_root / ALLOWED_ARTIFACT_ROOT / RUN_SUMMARY_NAME
    run_summary = _load_object(run_summary_path)
    if run_summary.get("pack_id") != build_pack_id:
        raise ValueError("run-summary.json pack_id does not match bundle.json")
    if run_summary.get("run_id") != run_id:
        raise ValueError("run-summary.json run_id does not match bundle.json")

    now = read_now()
    generated_at = isoformat_z(now)
    import_id = _make_import_id(now)
    import_root = target_pack.pack_root / "eval/history" / import_id
    if import_root.exists():
        current = now
        while import_root.exists():
            current += timedelta(seconds=1)
            generated_at = isoformat_z(current)
            import_id = _make_import_id(current)
            import_root = target_pack.pack_root / "eval/history" / import_id
    external_root = import_root / "external-runtime-evidence"
    external_root.mkdir(parents=True, exist_ok=False)

    copied_artifact_paths: list[str] = []
    bundle_copy_path = external_root / "bundle.json"
    shutil.copy2(bundle_manifest_path, bundle_copy_path)
    copied_artifact_paths.append("external-runtime-evidence/bundle.json")

    for source_path, bundle_path, _required in artifact_entries:
        target_path = external_root / bundle_path
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, target_path)
        copied_artifact_paths.append(f"external-runtime-evidence/{bundle_path.as_posix()}")

    memory_artifact_entry = next(
        (
            (source_path, bundle_path)
            for source_path, bundle_path, _required in artifact_entries
            if bundle_path.parts[1] == FEEDBACK_MEMORY_DIRNAME
        ),
        None,
    )
    import_report_relpath = f"eval/history/{import_id}/import-report.json"
    memory_intake = {
        "status": "not_present",
        "promoted_memory_path": None,
        "latest_pointer_path": None,
        "selected_memory_id": None,
        "selected_run_id": None,
        "selected_memory_sha256": None,
        "source_bundle_path": None,
        "block_summary": None,
    }
    if memory_artifact_entry is not None:
        _source_path, bundle_path = memory_artifact_entry
        imported_memory_artifact_path = external_root / bundle_path
        memory_intake = _promote_feedback_memory(
            target_pack=target_pack,
            memory_artifact_path=imported_memory_artifact_path,
            source_bundle_path=f"external-runtime-evidence/{bundle_path.as_posix()}",
        )
        memory_payload = _load_object(imported_memory_artifact_path)
        canonical_alignment = _canonical_memory_alignment(target_pack.pack_root)
        pointer_refresh = _refresh_latest_memory_pointer(
            factory_root=factory_root,
            target_pack=target_pack,
            import_generated_at=generated_at,
            import_id=import_id,
            promoted_memory_path=target_pack.pack_root / cast(str, memory_intake["promoted_memory_path"]),
            source_bundle_path=cast(str, memory_intake["source_bundle_path"]),
        )
        memory_intake["status"] = pointer_refresh["status"]
        memory_intake["latest_pointer_path"] = pointer_refresh["latest_pointer_path"]
        if pointer_refresh["status"] == "promoted_only":
            memory_intake["block_summary"] = _memory_block_summary(
                memory_payload=memory_payload,
                canonical_alignment=canonical_alignment,
            )

    report_payload = {
        "schema_version": REPORT_SCHEMA_VERSION,
        "import_id": import_id,
        "generated_at": generated_at,
        "status": "completed",
        "build_pack_id": build_pack_id,
        "build_pack_root": relative_path(factory_root, target_pack.pack_root),
        "bundle_manifest_path": str(bundle_manifest_path),
        "import_reason": import_reason,
        "imported_by": imported_by,
        "hash_verification_status": "pass",
        "copied_artifact_paths": copied_artifact_paths,
        "warnings": [],
        "control_plane_mutations": {
            "eval_history_written": True,
            "readiness_updated": False,
            "work_state_updated": False,
            "eval_latest_updated": False,
            "deployment_updated": False,
            "registry_updated": False,
            "release_artifacts_updated": False,
        },
        "memory_intake": memory_intake,
    }
    report_path = import_root / "import-report.json"
    _write_import_report_schema_validated(
        factory_root=factory_root,
        report_path=report_path,
        report_payload=report_payload,
    )

    return {
        "status": "completed",
        "import_id": import_id,
        "generated_at": generated_at,
        "build_pack_id": build_pack_id,
        "build_pack_root": relative_path(factory_root, target_pack.pack_root),
        "import_report_path": str(report_path),
        "copied_artifact_paths": copied_artifact_paths,
        "memory_intake": memory_intake,
    }


def _load_request(request_path: Path, factory_root: Path) -> dict[str, Any]:
    request = _load_object(request_path)
    _validate_payload_or_schema(
        factory_root,
        REQUEST_SCHEMA_NAME,
        request,
        label="request",
        manual_validator=_manual_validate_request,
    )
    return request


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Import bounded external runtime evidence into a build pack.")
    parser.add_argument("--factory-root", required=True)
    parser.add_argument("--request-file", required=True)
    parser.add_argument("--output", choices=("json",), default="json")
    args = parser.parse_args(argv)

    factory_root = resolve_factory_root(args.factory_root)
    request_path = Path(args.request_file).expanduser().resolve()
    if not request_path.exists():
        raise FileNotFoundError(f"request file does not exist: {request_path}")

    request = _load_request(request_path, factory_root)
    result = import_external_runtime_evidence(
        factory_root,
        request,
        request_file_dir=request_path.parent.resolve(),
    )

    if args.output == "json":
        print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
