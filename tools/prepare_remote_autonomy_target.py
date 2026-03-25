#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import re
import shlex
import subprocess
import sys
import textwrap
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from factory_ops import dump_json, load_json, resolve_factory_root, schema_path, validate_json_document
from remote_autonomy_staging_common import (
    canonical_remote_export_dir,
    canonical_remote_pack_dir,
    canonical_remote_parent_dir,
    canonical_remote_run_dir,
)

REQUEST_SCHEMA_NAME = "remote-autonomy-run-request.schema.json"
REQUEST_SCHEMA_VERSION = "remote-autonomy-run-request/v1"
REMOTE_REQUEST_RELATIVE_PATH = ".packfactory-remote/request.json"
SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def _load_object(path: Path) -> dict[str, Any]:
    payload = load_json(path)
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: JSON document must contain an object")
    return payload


def _path_is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _sha256_text(text: str) -> str:
    digest = hashlib.sha256()
    digest.update(text.encode("utf-8"))
    return digest.hexdigest()


def _validate_slug(field_name: str, value: Any) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"`{field_name}` must be a non-empty string")
    if not SLUG_PATTERN.fullmatch(value):
        raise ValueError(
            f"`{field_name}` must contain only lowercase ASCII letters, digits, and hyphens"
        )
    return value


def _validate_request_schema(factory_root: Path, request_path: Path) -> dict[str, Any]:
    errors = validate_json_document(request_path, schema_path(factory_root, REQUEST_SCHEMA_NAME))
    if errors:
        raise ValueError("; ".join(errors))
    return _load_object(request_path)


def _validate_request_contract(factory_root: Path, request_payload: dict[str, Any]) -> dict[str, Any]:
    schema_version = request_payload.get("schema_version")
    if schema_version != REQUEST_SCHEMA_VERSION:
        raise ValueError(f"`schema_version` must be `{REQUEST_SCHEMA_VERSION}`")

    source_factory_root_value = request_payload.get("source_factory_root")
    if not isinstance(source_factory_root_value, str) or not source_factory_root_value.strip():
        raise ValueError("`source_factory_root` must be a non-empty string")
    source_factory_root = resolve_factory_root(source_factory_root_value)
    if source_factory_root != factory_root:
        raise ValueError("`source_factory_root` must match `--factory-root`")

    source_build_pack_id = _validate_slug("source_build_pack_id", request_payload.get("source_build_pack_id"))
    run_id = _validate_slug("run_id", request_payload.get("run_id"))
    remote_target_label = _validate_slug("remote_target_label", request_payload.get("remote_target_label"))

    source_build_pack_root_value = request_payload.get("source_build_pack_root")
    if not isinstance(source_build_pack_root_value, str) or not source_build_pack_root_value.strip():
        raise ValueError("`source_build_pack_root` must be a non-empty string")
    source_build_pack_root = Path(source_build_pack_root_value).expanduser().resolve()
    if not source_build_pack_root.is_absolute():
        raise ValueError("`source_build_pack_root` must resolve to an absolute path")
    if not source_build_pack_root.exists():
        raise FileNotFoundError(f"`source_build_pack_root` does not exist: {source_build_pack_root}")
    if not _path_is_relative_to(source_build_pack_root, factory_root):
        raise ValueError("`source_build_pack_root` must live under `source_factory_root`")

    pack_manifest_path = source_build_pack_root / "pack.json"
    if not pack_manifest_path.exists():
        raise FileNotFoundError(f"missing pack manifest: {pack_manifest_path}")
    pack_manifest = _load_object(pack_manifest_path)
    if pack_manifest.get("pack_kind") != "build_pack":
        raise ValueError("`source_build_pack_root` must point to a build_pack")
    if pack_manifest.get("pack_id") != source_build_pack_id:
        raise ValueError("`source_build_pack_id` must match the source pack manifest")

    if source_build_pack_root.name != source_build_pack_id:
        raise ValueError("`source_build_pack_root` must end with the source build-pack id")

    remote_parent_dir = str(request_payload.get("remote_parent_dir", ""))
    remote_pack_dir = str(request_payload.get("remote_pack_dir", ""))
    remote_run_dir = str(request_payload.get("remote_run_dir", ""))
    remote_export_dir = str(request_payload.get("remote_export_dir", ""))

    expected_remote_parent_dir = canonical_remote_parent_dir(remote_target_label)
    expected_remote_pack_dir = canonical_remote_pack_dir(expected_remote_parent_dir, source_build_pack_id)
    expected_remote_run_dir = canonical_remote_run_dir(expected_remote_pack_dir, run_id)
    expected_remote_export_dir = canonical_remote_export_dir(expected_remote_pack_dir)

    if remote_parent_dir != expected_remote_parent_dir:
        raise ValueError(
            "`remote_parent_dir` must equal the canonical PackFactory-to-remote target root "
            f"`{expected_remote_parent_dir}`"
        )
    if remote_pack_dir != expected_remote_pack_dir:
        raise ValueError(
            "`remote_pack_dir` must equal the canonical pack directory "
            f"`{expected_remote_pack_dir}`"
        )
    if remote_run_dir != expected_remote_run_dir:
        raise ValueError(
            "`remote_run_dir` must equal the canonical run directory "
            f"`{expected_remote_run_dir}`"
        )
    if remote_export_dir != expected_remote_export_dir:
        raise ValueError(
            "`remote_export_dir` must equal the canonical runtime-evidence export directory "
            f"`{expected_remote_export_dir}`"
        )

    remote_reason = request_payload.get("remote_reason")
    staged_by = request_payload.get("staged_by")
    remote_runner = request_payload.get("remote_runner")
    remote_host = request_payload.get("remote_host")
    remote_user = request_payload.get("remote_user")

    for field_name, value in (
        ("remote_reason", remote_reason),
        ("staged_by", staged_by),
        ("remote_runner", remote_runner),
        ("remote_host", remote_host),
        ("remote_user", remote_user),
    ):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"`{field_name}` must be a non-empty string")

    return {
        "source_factory_root": str(source_factory_root),
        "source_build_pack_id": source_build_pack_id,
        "source_build_pack_root": str(source_build_pack_root),
        "source_build_pack_manifest": pack_manifest,
        "run_id": run_id,
        "remote_host": str(remote_host),
        "remote_user": str(remote_user),
        "remote_target_label": remote_target_label,
        "remote_parent_dir": remote_parent_dir,
        "remote_pack_dir": remote_pack_dir,
        "remote_run_dir": remote_run_dir,
        "remote_export_dir": remote_export_dir,
        "remote_reason": str(remote_reason),
        "staged_by": str(staged_by),
        "remote_runner": str(remote_runner),
    }


def _remote_command() -> str:
    return textwrap.dedent(
        """
        from __future__ import annotations

        import base64
        import hashlib
        import json
        import sys
        from pathlib import Path


        def _sha256_text(text: str) -> str:
            digest = hashlib.sha256()
            digest.update(text.encode("utf-8"))
            return digest.hexdigest()


        def _write_text(path: Path, content: str) -> None:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")


        def main() -> None:
            raw_pack_dir = sys.argv[1]
            raw_run_dir = sys.argv[2]
            raw_request_path = sys.argv[3]
            raw_request_dir = raw_request_path.rsplit("/", 1)[0]
            pack_dir = Path(raw_pack_dir).expanduser()
            run_dir = Path(raw_run_dir).expanduser()
            request_path = Path(raw_request_path).expanduser()
            request_text = base64.b64decode(sys.argv[4]).decode("utf-8")

            payload = json.loads(request_text)
            if not isinstance(payload, dict):
                raise ValueError("request payload must be a JSON object")

            expected_request_path = pack_dir / ".packfactory-remote" / "request.json"
            if request_path != expected_request_path:
                raise ValueError(
                    f"request path must equal {expected_request_path}"
                )

            pack_dir.mkdir(parents=True, exist_ok=True)
            run_dir.mkdir(parents=True, exist_ok=True)
            request_path.parent.mkdir(parents=True, exist_ok=True)
            _write_text(request_path, request_text)

            result = {
                "status": "prepared",
                "remote_pack_dir": raw_pack_dir,
                "remote_run_dir": raw_run_dir,
                "remote_request_path": raw_request_path,
                "ensured_paths": [
                    raw_pack_dir,
                    raw_run_dir,
                    raw_request_dir,
                ],
                "request_sha256": _sha256_text(request_text),
            }
            sys.stdout.write(json.dumps(result, sort_keys=True) + "\\n")


        if __name__ == "__main__":
            main()
        """
    ).strip()


def _build_remote_preparation_result(
    *,
    validated: dict[str, Any],
    remote_result: dict[str, Any],
    canonical_request_sha256: str,
) -> dict[str, Any]:
    return {
        "schema_version": "remote-autonomy-target-preparation-result/v1",
        "status": remote_result["status"],
        "factory_root": validated["source_factory_root"],
        "source_build_pack_id": validated["source_build_pack_id"],
        "source_build_pack_root": validated["source_build_pack_root"],
        "remote_host": validated["remote_host"],
        "remote_user": validated["remote_user"],
        "remote_target_label": validated["remote_target_label"],
        "remote_parent_dir": validated["remote_parent_dir"],
        "remote_pack_dir": validated["remote_pack_dir"],
        "remote_run_dir": validated["remote_run_dir"],
        "remote_export_dir": validated["remote_export_dir"],
        "remote_request_path": remote_result["remote_request_path"],
        "ensured_paths": remote_result["ensured_paths"],
        "request_sha256": canonical_request_sha256,
        "remote_request_sha256": remote_result["request_sha256"],
        "ssh_target": f"{validated['remote_user']}@{validated['remote_host']}",
        "remote_runner": validated["remote_runner"],
        "remote_reason": validated["remote_reason"],
        "staged_by": validated["staged_by"],
        "run_id": validated["run_id"],
    }


def prepare_remote_autonomy_target(factory_root: Path, request_path: Path) -> dict[str, Any]:
    request_payload = _validate_request_schema(factory_root, request_path)
    validated = _validate_request_contract(factory_root, request_payload)

    canonical_request_text = dump_json(request_payload)
    canonical_request_sha256 = _sha256_text(canonical_request_text)
    request_payload_b64 = base64.b64encode(canonical_request_text.encode("utf-8")).decode("ascii")
    remote_request_path = f"{validated['remote_pack_dir']}/{REMOTE_REQUEST_RELATIVE_PATH}"

    remote_command = " ".join(
        [
            "python3",
            "-c",
            shlex.quote(_remote_command()),
            shlex.quote(validated["remote_pack_dir"]),
            shlex.quote(validated["remote_run_dir"]),
            shlex.quote(remote_request_path),
            shlex.quote(request_payload_b64),
        ]
    )

    ssh_target = f"{validated['remote_user']}@{validated['remote_host']}"
    completed = subprocess.run(
        [
            "ssh",
            "-o",
            "BatchMode=yes",
            "-o",
            "ConnectTimeout=15",
            ssh_target,
            remote_command,
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        stderr = completed.stderr.strip()
        stdout = completed.stdout.strip()
        message = [
            f"remote target preparation failed for {ssh_target}",
            f"exit_code={completed.returncode}",
        ]
        if stdout:
            message.append(f"stdout: {stdout}")
        if stderr:
            message.append(f"stderr: {stderr}")
        raise RuntimeError("; ".join(message))

    remote_output = completed.stdout.strip()
    if not remote_output:
        raise RuntimeError("remote target preparation returned no JSON result")
    remote_result = json.loads(remote_output)
    if not isinstance(remote_result, dict):
        raise RuntimeError("remote target preparation must return a JSON object")

    if remote_result.get("request_sha256") != canonical_request_sha256:
        raise RuntimeError("remote request SHA-256 does not match the local canonical request payload")
    if remote_result.get("remote_request_path") != remote_request_path:
        raise RuntimeError("remote request path does not match the canonical target layout")

    return _build_remote_preparation_result(
        validated=validated,
        remote_result=remote_result,
        canonical_request_sha256=canonical_request_sha256,
    )


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare a remote PackFactory autonomy target workspace.",
    )
    parser.add_argument(
        "--factory-root",
        required=True,
        help="Absolute path to the PackFactory repository root.",
    )
    parser.add_argument(
        "--request-file",
        required=True,
        help="Path to a remote-autonomy-run-request/v1 JSON file.",
    )
    parser.add_argument(
        "--output",
        default="json",
        choices=("json",),
        help="Output format.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    factory_root = resolve_factory_root(args.factory_root)
    request_path = Path(args.request_file).expanduser().resolve()
    result = prepare_remote_autonomy_target(factory_root, request_path)
    sys.stdout.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
