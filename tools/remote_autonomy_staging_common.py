from __future__ import annotations

import hashlib
import json
import os
import posixpath
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Final

from factory_ops import (
    isoformat_z,
    load_json,
    read_now,
    relative_path,
    resolve_factory_root,
    schema_path,
    validate_json_document,
    write_json,
)


REQUEST_SCHEMA_NAME: Final[str] = "remote-autonomy-run-request.schema.json"
REQUEST_SCHEMA_VERSION: Final[str] = "remote-autonomy-run-request/v1"
PAYLOAD_MANIFEST_SCHEMA_NAME: Final[str] = "remote-execution-payload-manifest.schema.json"
PAYLOAD_MANIFEST_SCHEMA_VERSION: Final[str] = "remote-execution-payload-manifest/v1"
SCRATCH_LIFECYCLE_SCHEMA_NAME: Final[str] = "scratch-lifecycle.schema.json"
SCRATCH_LIFECYCLE_SCHEMA_VERSION: Final[str] = "scratch-lifecycle/v1"
LOCAL_SCRATCH_SELECTION_SCHEMA_NAME: Final[str] = "local-scratch-root-selection.schema.json"
LOCAL_SCRATCH_SELECTION_SCHEMA_VERSION: Final[str] = "local-scratch-root-selection/v1"
PAYLOAD_POLICY_VERSION: Final[str] = "fresh-staging/v2"
REMOTE_PARENT_TEMPLATE: Final[str] = "~/packfactory-source__{remote_target_label}__autonomous-build-packs"
REMOTE_EXPORT_DIR_SUFFIX: Final[str] = "dist/exports/runtime-evidence"
LOCAL_SCRATCH_ROOT_ENV: Final[str] = "PACKFACTORY_LOCAL_SCRATCH_ROOT"
DEFAULT_LOCAL_SCRATCH_ROOT: Final[Path] = Path(".pack-state") / "local-scratch"
LOCAL_SCRATCH_SELECTION_STATE_PATH: Final[Path] = Path(".pack-state") / "local-scratch-root-selection.json"
AGENT_MANAGED_SCRATCH_DIRNAME: Final[str] = "project-pack-factory-local-scratch"
AUTO_SCRATCH_CANDIDATE_PREFIXES: Final[tuple[str, ...]] = (
    "/mnt",
    "/media",
    "/run/media",
    "/srv",
    "/data",
    "/scratch",
)
LOCAL_SCRATCH_SELECTION_BY: Final[str] = "packfactory-local-scratch-resolver"
SLUG_PATTERN: Final[re.Pattern[str]] = re.compile(r"^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$")
MAX_SLUG_LENGTH: Final[int] = 128
REMOTE_METADATA_DIR: Final[str] = ".packfactory-remote"
REMOTE_REQUEST_FILENAME: Final[str] = "request.json"
REMOTE_TARGET_MANIFEST_FILENAME: Final[str] = "target-manifest.json"
LOCAL_STAGING_ROOT: Final[Path] = Path(".pack-state") / "remote-autonomy-staging"
LOCAL_ROUNDTRIP_ROOT: Final[Path] = Path(".pack-state") / "remote-autonomy-roundtrips"
SCRATCH_LIFECYCLE_FILENAME: Final[str] = "scratch-lifecycle.json"
EXCLUDED_EXACT_RELATIVE_PATHS: Final[frozenset[str]] = frozenset(
    {
        ".packfactory-remote",
        ".pack-state/autonomy-runs",
        "dist/candidates/algosec-lab-baseline",
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
    local_scratch_root: Path
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


def local_scratch_selection_state_path(factory_root: Path) -> Path:
    return resolve_factory_root(factory_root) / LOCAL_SCRATCH_SELECTION_STATE_PATH


def _normalize_local_scratch_root(factory_root: Path, value: str) -> Path:
    candidate = Path(str(value)).expanduser()
    if not candidate.is_absolute():
        candidate = resolve_factory_root(factory_root) / candidate
    return candidate.resolve()


def _load_validated_local_scratch_selection_state(factory_root: Path) -> dict[str, Any] | None:
    state_path = local_scratch_selection_state_path(factory_root)
    if not state_path.exists():
        return None
    errors = validate_json_document(state_path, schema_path(factory_root, LOCAL_SCRATCH_SELECTION_SCHEMA_NAME))
    if errors:
        return None
    payload = _load_object(state_path)
    if payload.get("schema_version") != LOCAL_SCRATCH_SELECTION_SCHEMA_VERSION:
        return None
    if payload.get("factory_root") != str(resolve_factory_root(factory_root)):
        return None
    selected_root = payload.get("selected_root")
    if not isinstance(selected_root, str) or not selected_root.strip():
        return None
    return payload


def _existing_parent(path: Path) -> Path | None:
    current = path
    while True:
        if current.exists():
            return current
        if current.parent == current:
            return None
        current = current.parent


def _can_materialize_directory(path: Path) -> bool:
    parent = _existing_parent(path)
    if parent is None:
        return False
    return os.access(parent, os.W_OK | os.X_OK)


def _mounted_prefix_candidates() -> list[Path]:
    mounts_path = Path("/proc/mounts")
    if not mounts_path.exists():
        return []
    candidates: list[Path] = []
    seen: set[Path] = set()
    for line in mounts_path.read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if len(parts) < 2:
            continue
        mount_point = Path(parts[1].replace("\\040", " ")).resolve()
        mount_text = str(mount_point)
        if not any(
            mount_text == prefix or mount_text.startswith(prefix + os.sep)
            for prefix in AUTO_SCRATCH_CANDIDATE_PREFIXES
        ):
            continue
        if not mount_point.exists() or not mount_point.is_dir():
            continue
        if mount_point in seen:
            continue
        seen.add(mount_point)
        candidates.append(mount_point)
    return sorted(candidates)


def _select_agent_managed_local_scratch_root(factory_root: Path) -> tuple[Path, str, str]:
    resolved_factory_root = resolve_factory_root(factory_root)
    factory_device = resolved_factory_root.stat().st_dev
    ranked_candidates: list[tuple[int, int, str, Path]] = []
    for mount_point in _mounted_prefix_candidates():
        try:
            if mount_point.stat().st_dev == factory_device:
                continue
        except OSError:
            continue
        candidate_root = mount_point / AGENT_MANAGED_SCRATCH_DIRNAME / resolved_factory_root.name
        if not _can_materialize_directory(candidate_root):
            continue
        try:
            free_bytes = shutil.disk_usage(mount_point).free
        except OSError:
            continue
        ranked_candidates.append((-free_bytes, len(mount_point.parts), str(mount_point), candidate_root))
    if ranked_candidates:
        ranked_candidates.sort()
        selected_root = ranked_candidates[0][3].resolve()
        return selected_root, "agent_auto_selected", f"alternate_mount:{ranked_candidates[0][2]}"
    return (resolved_factory_root / DEFAULT_LOCAL_SCRATCH_ROOT).resolve(), "repo_fallback", "repo_local_fallback"


def _persist_local_scratch_selection_state(
    *,
    factory_root: Path,
    selected_root: Path,
    selection_mode: str,
    selection_basis: str,
) -> None:
    resolved_factory_root = resolve_factory_root(factory_root)
    state_path = local_scratch_selection_state_path(resolved_factory_root)
    selected_root.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": LOCAL_SCRATCH_SELECTION_SCHEMA_VERSION,
        "factory_root": str(resolved_factory_root),
        "selected_root": str(selected_root),
        "selection_mode": selection_mode,
        "selection_basis": selection_basis,
        "selected_by": LOCAL_SCRATCH_SELECTION_BY,
        "selected_at": isoformat_z(read_now()),
        "same_filesystem_as_factory_root": selected_root.stat().st_dev == resolved_factory_root.stat().st_dev,
        "filesystem_free_bytes": shutil.disk_usage(selected_root).free,
    }
    write_json(state_path, payload)
    errors = validate_json_document(state_path, schema_path(resolved_factory_root, LOCAL_SCRATCH_SELECTION_SCHEMA_NAME))
    if errors:
        raise ValueError("; ".join(errors))


def resolve_local_scratch_root(factory_root: Path, value: str | None = None) -> Path:
    resolved_factory_root = resolve_factory_root(factory_root)
    candidate_value = value if value is not None and value.strip() else None
    if candidate_value is not None:
        candidate = _normalize_local_scratch_root(resolved_factory_root, str(candidate_value))
        candidate.mkdir(parents=True, exist_ok=True)
        return candidate

    persisted_state = _load_validated_local_scratch_selection_state(resolved_factory_root)
    if persisted_state is not None:
        candidate = _normalize_local_scratch_root(resolved_factory_root, str(persisted_state["selected_root"]))
        candidate.mkdir(parents=True, exist_ok=True)
        return candidate

    env_value = os.environ.get(LOCAL_SCRATCH_ROOT_ENV)
    if env_value is not None and env_value.strip():
        candidate = _normalize_local_scratch_root(resolved_factory_root, env_value)
        _persist_local_scratch_selection_state(
            factory_root=resolved_factory_root,
            selected_root=candidate,
            selection_mode="env_seeded",
            selection_basis=f"environment:{LOCAL_SCRATCH_ROOT_ENV}",
        )
        return candidate

    candidate, selection_mode, selection_basis = _select_agent_managed_local_scratch_root(resolved_factory_root)
    _persist_local_scratch_selection_state(
        factory_root=resolved_factory_root,
        selected_root=candidate,
        selection_mode=selection_mode,
        selection_basis=selection_basis,
    )
    return candidate


def canonical_local_remote_autonomy_staging_root(local_scratch_root: Path, run_id: str) -> Path:
    return (local_scratch_root / "remote-autonomy-staging" / run_id).resolve()


def canonical_local_roundtrip_root(
    local_scratch_root: Path,
    remote_target_label: str,
    build_pack_id: str,
    run_id: str,
) -> Path:
    return (local_scratch_root / "remote-autonomy-roundtrips" / remote_target_label / build_pack_id / run_id).resolve()


def canonical_local_roundtrip_incoming_dir(
    local_scratch_root: Path,
    remote_target_label: str,
    build_pack_id: str,
    run_id: str,
) -> Path:
    return canonical_local_roundtrip_root(local_scratch_root, remote_target_label, build_pack_id, run_id) / "incoming"


def canonical_local_roundtrip_artifacts_dir(
    factory_root: Path,
    remote_target_label: str,
    build_pack_id: str,
    run_id: str,
) -> Path:
    return (
        resolve_factory_root(factory_root)
        / LOCAL_ROUNDTRIP_ROOT
        / remote_target_label
        / build_pack_id
        / run_id
        / "artifacts"
    ).resolve()


def scratch_lifecycle_path(root: Path) -> Path:
    return root / SCRATCH_LIFECYCLE_FILENAME


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
    local_scratch_root: Path,
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
    local_scratch_root = resolve_local_scratch_root(factory_root, str(payload["local_scratch_root"]))
    current_local_scratch_root = resolve_local_scratch_root(factory_root)
    if current_local_scratch_root != local_scratch_root:
        raise ValueError(
            "local_scratch_root in the request does not match the currently selected PackFactory scratch root"
        )

    parent, pack, run, export_dir = _validate_request_paths(
        local_scratch_root=local_scratch_root,
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
        local_scratch_root=local_scratch_root,
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


def write_validated_scratch_lifecycle_manifest(*, factory_root: Path, path: Path, payload: dict[str, Any]) -> None:
    write_json(path, payload)
    errors = validate_json_document(path, schema_path(factory_root, SCRATCH_LIFECYCLE_SCHEMA_NAME))
    if errors:
        raise ValueError("; ".join(errors))


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def should_exclude_relative_path(relative_path: str, *, is_dir: bool) -> bool:
    normalized = relative_path.replace("\\", "/").strip()
    while normalized.startswith("./"):
        normalized = normalized[2:]
    while normalized.startswith("/"):
        normalized = normalized[1:]
    normalized = normalized.rstrip("/")
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


def expand_remote_home_for_scp(path: str, remote_user: str) -> str:
    if path == "~":
        return f"/home/{remote_user}"
    if path.startswith("~/"):
        return f"/home/{remote_user}/{path[2:]}"
    return path


def run_checked(command: list[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        text=True,
        capture_output=True,
        check=True,
    )


def push_file_via_scp(*, request: RemoteAutonomyRunRequest, local_path: Path, remote_path: str) -> None:
    resolved_remote_path = expand_remote_home_for_scp(remote_path, request.remote_user)
    run_checked(["scp", str(local_path), f"{request.remote_address}:{resolved_remote_path}"])


def push_directory_via_rsync(*, request: RemoteAutonomyRunRequest, local_dir: Path, remote_dir: str) -> None:
    resolved_remote_dir = expand_remote_home_for_scp(remote_dir, request.remote_user)
    run_checked(["rsync", "-a", f"{local_dir}/", f"{request.remote_address}:{resolved_remote_dir}/"])


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
