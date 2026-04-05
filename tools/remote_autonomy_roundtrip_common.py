from __future__ import annotations

import hashlib
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

from factory_ops import dump_json, load_json, resolve_factory_root, schema_path, validate_json_document, write_json
from remote_autonomy_staging_common import (
    canonical_local_roundtrip_artifacts_dir,
    canonical_local_roundtrip_incoming_dir,
    canonical_local_roundtrip_root,
    load_remote_autonomy_request,
    resolve_local_scratch_root,
)


REMOTE_AUTONOMY_TEST_REQUEST_SCHEMA_NAME: Final[str] = "remote-autonomy-test-request.schema.json"
REMOTE_AUTONOMY_TEST_REQUEST_SCHEMA_VERSION: Final[str] = "remote-autonomy-test-request/v1"
REMOTE_ROUNDTRIP_MANIFEST_SCHEMA_NAME: Final[str] = "remote-roundtrip-manifest.schema.json"
REMOTE_ROUNDTRIP_MANIFEST_SCHEMA_VERSION: Final[str] = "remote-roundtrip-manifest/v1"
LOCAL_ROUNDTRIP_ROOT: Final[Path] = Path(".pack-state") / "remote-autonomy-roundtrips"
DURABLE_AUDIT_FILENAMES: Final[tuple[str, ...]] = (
    "target-manifest.json",
    "execution-manifest.json",
    "recovery-remote-state.json",
    "portable-runtime-helper-manifest.json",
    "scratch-lifecycle.json",
)
DURABLE_AUDIT_DIRNAMES: Final[tuple[str, ...]] = (
    "checkpoint-artifacts",
)


@dataclass(frozen=True)
class RemoteAutonomyTestRequest:
    factory_root: Path
    request_path: Path
    remote_run_request_path: Path
    remote_run_request: Any
    local_scratch_root: Path
    local_bundle_staging_dir: Path
    pull_bundle: bool
    import_bundle: bool
    imported_by: str
    import_reason: str
    test_reason: str
    raw_payload: dict[str, Any]


def _load_object(path: Path) -> dict[str, Any]:
    payload = load_json(path)
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: JSON document must contain an object")
    return payload


def _validate_schema(factory_root: Path, path: Path, schema_name: str) -> dict[str, Any]:
    errors = validate_json_document(path, schema_path(factory_root, schema_name))
    if errors:
        raise ValueError("; ".join(errors))
    return _load_object(path)


def canonical_local_bundle_staging_dir(
    *,
    factory_root: Path,
    remote_target_label: str,
    build_pack_id: str,
    run_id: str,
    local_scratch_root: Path | None = None,
) -> Path:
    selected_scratch_root = (
        resolve_local_scratch_root(factory_root) if local_scratch_root is None else local_scratch_root.resolve()
    )
    return canonical_local_roundtrip_incoming_dir(
        selected_scratch_root,
        remote_target_label,
        build_pack_id,
        run_id,
    )


def canonical_local_roundtrip_artifacts_root(
    *,
    factory_root: Path,
    remote_target_label: str,
    build_pack_id: str,
    run_id: str,
) -> Path:
    return canonical_local_roundtrip_artifacts_dir(
        factory_root,
        remote_target_label,
        build_pack_id,
        run_id,
    ).parent


def resolve_local_bundle_staging_dir(*, selected_scratch_root: Path, value: str) -> Path:
    candidate = Path(value).expanduser()
    if not candidate.is_absolute():
        candidate = selected_scratch_root / candidate
    resolved = candidate.resolve()
    try:
        resolved.relative_to(selected_scratch_root)
    except ValueError as exc:
        raise ValueError("local_bundle_staging_dir must resolve under the selected PackFactory scratch root") from exc
    return resolved


def load_remote_autonomy_test_request(*, factory_root: Path, request_path: Path) -> RemoteAutonomyTestRequest:
    payload = _validate_schema(factory_root, request_path, REMOTE_AUTONOMY_TEST_REQUEST_SCHEMA_NAME)
    if payload.get("schema_version") != REMOTE_AUTONOMY_TEST_REQUEST_SCHEMA_VERSION:
        raise ValueError(
            f"wrapper request schema_version must be `{REMOTE_AUTONOMY_TEST_REQUEST_SCHEMA_VERSION}`"
        )
    remote_run_request_path = Path(str(payload["remote_run_request_path"])).expanduser()
    if not remote_run_request_path.is_absolute():
        remote_run_request_path = (request_path.parent / remote_run_request_path).resolve()
    else:
        remote_run_request_path = remote_run_request_path.resolve()
    if not remote_run_request_path.exists():
        raise FileNotFoundError(f"remote_run_request_path does not exist: {remote_run_request_path}")

    remote_run_request = load_remote_autonomy_request(
        factory_root=factory_root,
        request_path=remote_run_request_path,
    )
    local_scratch_root = resolve_local_scratch_root(factory_root, str(payload["local_scratch_root"]))
    current_local_scratch_root = resolve_local_scratch_root(factory_root)
    if current_local_scratch_root != local_scratch_root:
        raise ValueError(
            "local_scratch_root in the request does not match the currently selected PackFactory scratch root"
        )
    local_bundle_staging_dir = resolve_local_bundle_staging_dir(
        selected_scratch_root=local_scratch_root,
        value=str(payload["local_bundle_staging_dir"]),
    )
    expected_local_bundle_staging_dir = canonical_local_bundle_staging_dir(
        factory_root=factory_root,
        remote_target_label=remote_run_request.remote_target_label,
        build_pack_id=remote_run_request.source_build_pack_id,
        run_id=remote_run_request.run_id,
        local_scratch_root=local_scratch_root,
    )
    if local_bundle_staging_dir != expected_local_bundle_staging_dir:
        raise ValueError(
            "local_bundle_staging_dir must match the deterministic roundtrip staging path "
            f"`{expected_local_bundle_staging_dir}`"
        )

    return RemoteAutonomyTestRequest(
        factory_root=resolve_factory_root(factory_root),
        request_path=request_path.resolve(),
        remote_run_request_path=remote_run_request_path,
        remote_run_request=remote_run_request,
        local_scratch_root=local_scratch_root,
        local_bundle_staging_dir=local_bundle_staging_dir,
        pull_bundle=bool(payload["pull_bundle"]),
        import_bundle=bool(payload["import_bundle"]),
        imported_by=str(payload["imported_by"]).strip(),
        import_reason=str(payload["import_reason"]).strip(),
        test_reason=str(payload["test_reason"]).strip(),
        raw_payload=payload,
    )


def canonical_json_text(payload: dict[str, Any]) -> str:
    return dump_json(payload)


def sha256_text(text: str) -> str:
    digest = hashlib.sha256()
    digest.update(text.encode("utf-8"))
    return digest.hexdigest()


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_tree(root: Path) -> str:
    if not root.exists():
        raise FileNotFoundError(f"tree root does not exist: {root}")
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        relative_path = path.relative_to(root).as_posix().encode("utf-8")
        digest.update(relative_path)
        digest.update(b"\0")
        digest.update(sha256_path(path).encode("utf-8"))
        digest.update(b"\n")
    return digest.hexdigest()


def write_validated_roundtrip_manifest(*, factory_root: Path, path: Path, payload: dict[str, Any]) -> None:
    write_json(path, payload)
    errors = validate_json_document(path, schema_path(factory_root, REMOTE_ROUNDTRIP_MANIFEST_SCHEMA_NAME))
    if errors:
        raise ValueError("; ".join(errors))


def promote_roundtrip_audit_artifacts(*, local_stage_dir: Path, durable_artifacts_dir: Path) -> dict[str, str]:
    durable_artifacts_dir.mkdir(parents=True, exist_ok=True)
    promoted: dict[str, str] = {}
    for filename in DURABLE_AUDIT_FILENAMES:
        source_path = local_stage_dir / filename
        if not source_path.exists() or not source_path.is_file():
            continue
        target_path = durable_artifacts_dir / filename
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, target_path)
        promoted[filename] = str(target_path)
    for dirname in DURABLE_AUDIT_DIRNAMES:
        source_dir = local_stage_dir / dirname
        if not source_dir.exists() or not source_dir.is_dir():
            continue
        target_dir = durable_artifacts_dir / dirname
        if target_dir.exists():
            shutil.rmtree(target_dir)
        shutil.copytree(source_dir, target_dir)
        promoted[dirname] = str(target_dir)
    return promoted
