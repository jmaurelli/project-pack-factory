from __future__ import annotations

import hashlib
import json
import os
import shlex
import subprocess
import tarfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_BACKUP_SCHEDULE = "17 3 * * *"
DEFAULT_RETENTION_COUNT = 7
DEFAULT_BACKUP_BASEDIR = Path.home() / ".local" / "share" / "packfactory-backups"
CRON_BLOCK_LABEL_TEMPLATE = "PACKFACTORY BACKUP {pack_id}"
EXCLUDED_BASENAMES = {
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
}


def create_backup_snapshot(
    *,
    project_root: Path,
    backup_root: str | Path | None = None,
    retain_count: int = DEFAULT_RETENTION_COUNT,
) -> dict[str, Any]:
    if retain_count < 1:
        raise ValueError("retain_count must be at least 1")

    root = project_root.resolve()
    pack_manifest = _load_pack_manifest(root)
    pack_id = str(pack_manifest.get("pack_id") or root.name)
    resolved_backup_root = _resolve_backup_root(pack_id=pack_id, backup_root=backup_root)
    archives_dir = resolved_backup_root / "archives"
    manifests_dir = resolved_backup_root / "manifests"
    logs_dir = resolved_backup_root / "logs"
    archives_dir.mkdir(parents=True, exist_ok=True)
    manifests_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)

    timestamp_token = _timestamp_token()
    archive_name = f"{pack_id}-backup-{timestamp_token}.tar.gz"
    manifest_name = f"{pack_id}-backup-{timestamp_token}.json"
    archive_path = archives_dir / archive_name
    manifest_path = manifests_dir / manifest_name

    skipped_prefix = _backup_root_relative_prefix(project_root=root, backup_root=resolved_backup_root)
    archived_members = 0
    with tarfile.open(archive_path, "w:gz") as archive:
        for path in sorted(root.rglob("*")):
            if _should_skip_path(root=root, path=path, skipped_prefix=skipped_prefix):
                continue
            archive.add(path, arcname=str(Path(pack_id) / path.relative_to(root)), recursive=False)
            archived_members += 1

    archive_sha256 = _sha256_path(archive_path)
    manifest_payload = {
        "schema_version": "pack-backup-snapshot/v1",
        "created_at": _isoformat_z(),
        "pack_id": pack_id,
        "project_root": str(root),
        "backup_root": str(resolved_backup_root),
        "archive_relative_path": str(archive_path.relative_to(resolved_backup_root)),
        "archive_sha256": archive_sha256,
        "archive_size_bytes": archive_path.stat().st_size,
        "archived_member_count": archived_members,
        "retention_count": retain_count,
    }
    manifest_path.write_text(json.dumps(manifest_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    pruned_files = _prune_backups(
        pack_id=pack_id,
        backup_root=resolved_backup_root,
        manifests_dir=manifests_dir,
        retain_count=retain_count,
    )
    return {
        "status": "pass",
        "pack_id": pack_id,
        "backup_root": str(resolved_backup_root),
        "generated_files": [
            str(archive_path),
            str(manifest_path),
        ],
        "summary": {
            "archive_sha256": archive_sha256,
            "archive_size_bytes": archive_path.stat().st_size,
            "archived_member_count": archived_members,
            "retention_count": retain_count,
            "pruned_file_count": len(pruned_files),
        },
        "pruned_files": pruned_files,
    }


def install_backup_cron(
    *,
    project_root: Path,
    schedule: str = DEFAULT_BACKUP_SCHEDULE,
    backup_root: str | Path | None = None,
    retain_count: int = DEFAULT_RETENTION_COUNT,
    install_root: str | Path | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    _validate_cron_schedule(schedule)
    root = project_root.resolve()
    pack_manifest = _load_pack_manifest(root)
    pack_id = str(pack_manifest.get("pack_id") or root.name)
    resolved_backup_root = _resolve_backup_root(pack_id=pack_id, backup_root=backup_root)
    resolved_install_root = (
        Path(install_root).expanduser().resolve()
        if install_root
        else resolved_backup_root / "job"
    )
    resolved_install_root.mkdir(parents=True, exist_ok=True)
    (resolved_backup_root / "logs").mkdir(parents=True, exist_ok=True)
    script_path = resolved_install_root / "run-pack-backup.sh"
    log_path = resolved_backup_root / "logs" / "backup.log"

    script_path.write_text(
        _backup_script_text(
            project_root=root,
            backup_root=resolved_backup_root,
            retain_count=retain_count,
            log_path=log_path,
        ),
        encoding="utf-8",
    )
    script_path.chmod(0o755)

    cron_block = _cron_block(
        pack_id=pack_id,
        schedule=schedule,
        script_path=script_path,
    )
    existing_crontab = _read_crontab()
    updated_crontab = _upsert_cron_block(existing_crontab, cron_block, pack_id)
    if not dry_run:
        _write_crontab(updated_crontab)

    return {
        "status": "pass",
        "pack_id": pack_id,
        "project_root": str(root),
        "backup_root": str(resolved_backup_root),
        "install_root": str(resolved_install_root),
        "script_path": str(script_path),
        "schedule": schedule,
        "retain_count": retain_count,
        "dry_run": dry_run,
        "cron_block_preview": cron_block,
        "log_path": str(log_path),
    }


def _load_pack_manifest(project_root: Path) -> dict[str, Any]:
    pack_manifest_path = project_root / "pack.json"
    payload = json.loads(pack_manifest_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{pack_manifest_path}: expected a JSON object")
    return payload


def _resolve_backup_root(*, pack_id: str, backup_root: str | Path | None) -> Path:
    if backup_root is None:
        return (DEFAULT_BACKUP_BASEDIR / pack_id).expanduser().resolve()
    return Path(backup_root).expanduser().resolve()


def _backup_root_relative_prefix(*, project_root: Path, backup_root: Path) -> Path | None:
    try:
        return backup_root.relative_to(project_root)
    except ValueError:
        return None


def _should_skip_path(*, root: Path, path: Path, skipped_prefix: Path | None) -> bool:
    relative = path.relative_to(root)
    if any(part in EXCLUDED_BASENAMES for part in relative.parts):
        return True
    if skipped_prefix is not None and (relative == skipped_prefix or skipped_prefix in relative.parents):
        return True
    return False


def _sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _prune_backups(
    *,
    pack_id: str,
    backup_root: Path,
    manifests_dir: Path,
    retain_count: int,
) -> list[str]:
    manifest_paths = sorted(manifests_dir.glob(f"{pack_id}-backup-*.json"))
    if len(manifest_paths) <= retain_count:
        return []

    pruned: list[str] = []
    for manifest_path in manifest_paths[:-retain_count]:
        archive_path = None
        try:
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
            archive_relpath = payload.get("archive_relative_path")
            if isinstance(archive_relpath, str) and archive_relpath:
                archive_path = backup_root / archive_relpath
        except json.JSONDecodeError:
            archive_path = None
        if archive_path and archive_path.exists():
            archive_path.unlink()
            pruned.append(str(archive_path))
        if manifest_path.exists():
            manifest_path.unlink()
            pruned.append(str(manifest_path))
    return pruned


def _validate_cron_schedule(schedule: str) -> None:
    if len(schedule.split()) != 5:
        raise ValueError("schedule must contain five cron fields")


def _backup_script_text(
    *,
    project_root: Path,
    backup_root: Path,
    retain_count: int,
    log_path: Path,
) -> str:
    log_dir = log_path.parent
    return "\n".join(
        [
            "#!/usr/bin/env bash",
            "set -euo pipefail",
            f"mkdir -p {shlex.quote(str(log_dir))}",
            f"cd {shlex.quote(str(project_root))}",
            "export PYTHONPATH=src",
            (
                "python3 -m algosec_diagnostic_framework_successor_template_pack "
                "create-backup-snapshot "
                f"--project-root {shlex.quote(str(project_root))} "
                f"--backup-root {shlex.quote(str(backup_root))} "
                f"--retain-count {retain_count} "
                f"--output json >> {shlex.quote(str(log_path))} 2>&1"
            ),
            "",
        ]
    )


def _cron_block(*, pack_id: str, schedule: str, script_path: Path) -> str:
    label = CRON_BLOCK_LABEL_TEMPLATE.format(pack_id=pack_id)
    return "\n".join(
        [
            f"# BEGIN {label}",
            f"{schedule} {shlex.quote(str(script_path))}",
            f"# END {label}",
        ]
    )


def _read_crontab() -> str:
    completed = subprocess.run(
        ["crontab", "-l"],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if completed.returncode == 0:
        return completed.stdout
    return ""


def _write_crontab(content: str) -> None:
    completed = subprocess.run(
        ["crontab", "-"],
        input=content,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if completed.returncode != 0:
        stderr = completed.stderr.strip() or completed.stdout.strip()
        raise RuntimeError(f"failed to install crontab: {stderr}")


def _upsert_cron_block(existing_crontab: str, cron_block: str, pack_id: str) -> str:
    begin_marker = f"# BEGIN {CRON_BLOCK_LABEL_TEMPLATE.format(pack_id=pack_id)}"
    end_marker = f"# END {CRON_BLOCK_LABEL_TEMPLATE.format(pack_id=pack_id)}"
    lines = existing_crontab.splitlines()
    kept_lines: list[str] = []
    in_block = False
    for line in lines:
        if line == begin_marker:
            in_block = True
            continue
        if in_block and line == end_marker:
            in_block = False
            continue
        if not in_block:
            kept_lines.append(line)
    while kept_lines and kept_lines[-1] == "":
        kept_lines.pop()
    if kept_lines:
        kept_lines.append("")
    kept_lines.extend(cron_block.splitlines())
    return "\n".join(kept_lines) + "\n"


def _timestamp_token() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dt%H%M%Sz").lower()


def _isoformat_z() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
