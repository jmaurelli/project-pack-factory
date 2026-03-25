from __future__ import annotations

import hashlib
import json
import posixpath
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Final

from factory_ops import load_json, relative_path, resolve_factory_root, schema_path, validate_json_document, write_json


REQUEST_SCHEMA_NAME: Final[str] = "remote-autonomy-run-request.schema.json"
REQUEST_SCHEMA_VERSION: Final[str] = "remote-autonomy-run-request/v1"
PAYLOAD_MANIFEST_SCHEMA_NAME: Final[str] = "remote-execution-payload-manifest.schema.json"
PAYLOAD_MANIFEST_SCHEMA_VERSION: Final[str] = "remote-execution-payload-manifest/v1"
PAYLOAD_POLICY_VERSION: Final[str] = "fresh-staging/v1"
REMOTE_PARENT_TEMPLATE: Final[str] = "~/packfactory-source__{remote_target_label}__autonomous-build-packs"
REMOTE_EXPORT_DIR_SUFFIX: Final[str] = "dist/exports/runtime-evidence"
SLUG_PATTERN: Final[re.Pattern[str]] = re.compile(r"^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$")
MAX_SLUG_LENGTH: Final[int] = 128
REMOTE_METADATA_DIR: Final[str] = ".packfactory-remote"
REMOTE_REQUEST_FILENAME: Final[str] = "request.json"
REMOTE_TARGET_MANIFEST_FILENAME: Final[str] = "target-manifest.json"
LOCAL_STAGING_ROOT: Final[Path] = Path(".pack-state") / "remote-autonomy-staging"
EXCLUDED_EXACT_RELATIVE_PATHS: Final[frozenset[str]] = frozenset(
    {
        ".packfactory-remote",
        ".pack-state/autonomy-runs",
        "eval/history",
        "dist/exports/runtime-evidence",
    }
)
EXCLUDED_BASENAMES: Final[frozenset[str]] = frozenset(
    {
        ".venv",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
    }
)


@dataclass(frozen=True)
class RemoteAutonomyRunRequest:
    factory_root: Path
    request_path: Path
    source_factory_root: Path
    source_build_pack_id: str
    source_build_pack_root: Path
    run_id: str
    remote_host: str
    remote_user: str
    remote_target_label: str
    remote_parent_dir: str
    remote_pack_dir: str
    remote_run_dir: str
    remote_export_dir: str
    remote_reason: str
    staged_by: str
    remote_runner: str
    raw_payload: dict[str, Any]

    @property
    def remote_address(self) -> str:
        return f"{self.remote_user}@{self.remote_host}"


def canonical_remote_parent_dir(remote_target_label: str) -> str:
    return REMOTE_PARENT_TEMPLATE.format(remote_target_label=remote_target_label)


def canonical_remote_pack_dir(remote_parent_dir: str, source_build_pack_id: str) -> str:
    return f"{remote_parent_dir}/{source_build_pack_id}"


def canonical_remote_run_dir(remote_pack_dir: str, run_id: str) -> str:
    return f"{remote_pack_dir}/runs/{run_id}"


def canonical_remote_export_dir(remote_pack_dir: str) -> str:
    return f"{remote_pack_dir}/{REMOTE_EXPORT_DIR_SUFFIX}"


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


def _require_slug(value: str, *, field_name: str) -> str:
    if len(value) > MAX_SLUG_LENGTH:
        raise ValueError(f"{field_name} must be at most {MAX_SLUG_LENGTH} characters")
    if not SLUG_PATTERN.fullmatch(value):
        raise ValueError(
            f"{field_name} must use lowercase ASCII letters, digits, and internal hyphens only"
        )
    return value


def _normalize_remote_path(value: str, *, field_name: str) -> str:
    candidate = value.strip()
    if not candidate:
        raise ValueError(f"{field_name} must be a non-empty path")
    if "\\" in candidate:
        raise ValueError(f"{field_name} must use POSIX-style path separators only")

    prefix = ""
    remainder = candidate
    if candidate == "~":
        return "~"
    if candidate.startswith("~/"):
        prefix = "~"
        remainder = candidate[1:]
    elif candidate.startswith("/"):
        prefix = "/"
        remainder = candidate[1:]

    normalized = posixpath.normpath("/" + remainder.lstrip("/"))
    if normalized in {"/.", "/"}:
        normalized = "/"
    parts = [part for part in PurePosixPath(normalized).parts if part not in {"/"}]
    if any(part in {"..", "."} for part in parts):
        raise ValueError(f"{field_name} must not contain path traversal segments")

    if prefix == "~":
        return "~" if normalized == "/" else f"~{normalized}"
    if prefix == "/":
        return normalized
    return normalized.lstrip("/")


def _join_remote_path(parent: str, child: str) -> str:
    if parent == "~":
        return f"~/{child}"
    if parent.startswith("~/"):
        return f"{parent.rstrip('/')}/{child}"
    if parent.startswith("/"):
        return posixpath.join(parent, child)
    return posixpath.join(parent, child)


def _ensure_remote_child(*, parent: str, child: str, field_name: str) -> str:
    expected = _normalize_remote_path(_join_remote_path(parent, child), field_name=field_name)
    return expected


def _validate_request_paths(
    *,
    source_build_pack_id: str,
    run_id: str,
    remote_parent_dir: str,
    remote_pack_dir: str,
    remote_run_dir: str,
    remote_export_dir: str,
) -> tuple[str, str, str, str]:
    parent = _normalize_remote_path(remote_parent_dir, field_name="remote_parent_dir")
    pack = _normalize_remote_path(remote_pack_dir, field_name="remote_pack_dir")
    run = _normalize_remote_path(remote_run_dir, field_name="remote_run_dir")
    export_dir = _normalize_remote_path(remote_export_dir, field_name="remote_export_dir")

    expected_pack = _ensure_remote_child(
        parent=parent,
        child=source_build_pack_id,
        field_name="remote_pack_dir",
    )
    if pack != expected_pack:
        raise ValueError("remote_pack_dir must match the deterministic pack path for the request")

    expected_run = _ensure_remote_child(
        parent=pack,
        child=posixpath.join("runs", run_id),
        field_name="remote_run_dir",
    )
    if run != expected_run:
        raise ValueError("remote_run_dir must match the deterministic run path for the request")

    expected_export = _ensure_remote_child(
        parent=pack,
        child=posixpath.join("dist", "exports", "runtime-evidence"),
        field_name="remote_export_dir",
    )
    if export_dir != expected_export:
        raise ValueError("remote_export_dir must match the deterministic export path for the request")

    return parent, pack, run, export_dir


def load_remote_autonomy_request(*, factory_root: Path, request_path: Path) -> RemoteAutonomyRunRequest:
    payload = _validate_schema(factory_root, request_path, REQUEST_SCHEMA_NAME)
    if payload.get("schema_version") != REQUEST_SCHEMA_VERSION:
        raise ValueError(f"request schema_version must be `{REQUEST_SCHEMA_VERSION}`")

    source_factory_root = resolve_factory_root(str(payload["source_factory_root"]))
    source_build_pack_root = Path(str(payload["source_build_pack_root"])).expanduser().resolve()
    request_factory_root = resolve_factory_root(factory_root)
    if source_factory_root != request_factory_root:
        raise ValueError("source_factory_root must match the selected factory_root")
    if not source_build_pack_root.exists():
        raise ValueError(f"source_build_pack_root does not exist: {source_build_pack_root}")

    source_build_pack_id = _require_slug(str(payload["source_build_pack_id"]), field_name="source_build_pack_id")
    run_id = _require_slug(str(payload["run_id"]), field_name="run_id")
    remote_target_label = _require_slug(str(payload["remote_target_label"]), field_name="remote_target_label")
    if source_build_pack_root.name != source_build_pack_id:
        raise ValueError("source_build_pack_root must end with the selected source_build_pack_id")

    parent, pack, run, export_dir = _validate_request_paths(
        source_build_pack_id=source_build_pack_id,
        run_id=run_id,
        remote_parent_dir=str(payload["remote_parent_dir"]),
        remote_pack_dir=str(payload["remote_pack_dir"]),
        remote_run_dir=str(payload["remote_run_dir"]),
        remote_export_dir=str(payload["remote_export_dir"]),
    )

    return RemoteAutonomyRunRequest(
        factory_root=request_factory_root,
        request_path=request_path.resolve(),
        source_factory_root=source_factory_root,
        source_build_pack_id=source_build_pack_id,
        source_build_pack_root=source_build_pack_root,
        run_id=run_id,
        remote_host=str(payload["remote_host"]).strip(),
        remote_user=str(payload["remote_user"]).strip(),
        remote_target_label=remote_target_label,
        remote_parent_dir=parent,
        remote_pack_dir=pack,
        remote_run_dir=run,
        remote_export_dir=export_dir,
        remote_reason=str(payload["remote_reason"]).strip(),
        staged_by=str(payload["staged_by"]).strip(),
        remote_runner=str(payload["remote_runner"]).strip(),
        raw_payload=payload,
    )


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def should_exclude_relative_path(relative_path: str, *, is_dir: bool) -> bool:
    normalized = relative_path.strip("./")
    if not normalized:
        return False
    if normalized in EXCLUDED_EXACT_RELATIVE_PATHS:
        return True
    if any(
        normalized.startswith(f"{excluded}/")
        for excluded in EXCLUDED_EXACT_RELATIVE_PATHS
    ):
        return True
    path = PurePosixPath(normalized)
    if any(part in EXCLUDED_BASENAMES for part in path.parts):
        return True
    if is_dir and path.name.endswith(".egg-info"):
        return True
    return False


def materialize_payload_snapshot(*, request: RemoteAutonomyRunRequest, destination_root: Path) -> tuple[list[str], list[dict[str, Any]]]:
    if destination_root.exists():
        shutil.rmtree(destination_root)
    destination_root.mkdir(parents=True, exist_ok=True)

    excluded_paths: list[str] = []
    payload_entries: list[dict[str, Any]] = []

    source_root = request.source_build_pack_root
    for source_path in sorted(source_root.rglob("*")):
        relative = relative_path(source_root, source_path).replace("\\", "/")
        is_dir = source_path.is_dir()
        if should_exclude_relative_path(relative, is_dir=is_dir):
            excluded_paths.append(relative)
            if is_dir:
                # Prevent descending into excluded directories by relying on rglob order only.
                continue
            continue
        if is_dir:
            (destination_root / relative).mkdir(parents=True, exist_ok=True)
            continue

        target_path = destination_root / relative
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, target_path)
        payload_entries.append(
            {
                "relative_path": relative,
                "sha256": sha256_path(target_path),
                "size_bytes": target_path.stat().st_size,
            }
        )

    excluded_paths = sorted(set(excluded_paths))
    payload_entries.sort(key=lambda entry: str(entry["relative_path"]))
    return excluded_paths, payload_entries


def write_validated_json(
    *,
    factory_root: Path,
    path: Path,
    payload: dict[str, Any],
    schema_name: str,
) -> None:
    write_json(path, payload)
    errors = validate_json_document(path, schema_path(factory_root, schema_name))
    if errors:
        raise ValueError("; ".join(errors))


def build_control_plane_mutations() -> dict[str, bool]:
    return {
        "registry_updated": False,
        "deployment_updated": False,
        "promotion_updated": False,
        "readiness_updated": False,
        "work_state_updated": False,
        "eval_latest_updated": False,
        "release_artifacts_updated": False,
    }


def ssh_command(request: RemoteAutonomyRunRequest, remote_command: str) -> list[str]:
    return ["ssh", request.remote_address, remote_command]


def run_checked(command: list[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        text=True,
        capture_output=True,
        check=True,
    )


def push_file_via_scp(*, request: RemoteAutonomyRunRequest, local_path: Path, remote_path: str) -> None:
    run_checked(["scp", str(local_path), f"{request.remote_address}:{remote_path}"])


def push_directory_via_rsync(*, request: RemoteAutonomyRunRequest, local_dir: Path, remote_dir: str) -> None:
    run_checked(["rsync", "-a", f"{local_dir}/", f"{request.remote_address}:{remote_dir}/"])


def write_remote_json_via_tempfile(
    *,
    request: RemoteAutonomyRunRequest,
    remote_path: str,
    payload: dict[str, Any],
) -> None:
    with tempfile.TemporaryDirectory(prefix="remote-autonomy-json-") as temp_dir:
        temp_path = Path(temp_dir) / Path(remote_path).name
        temp_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        push_file_via_scp(request=request, local_path=temp_path, remote_path=remote_path)
