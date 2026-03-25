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

from factory_ops import discover_pack, isoformat_z, read_now, relative_path, resolve_factory_root, write_json
from import_external_runtime_evidence import (
    LATEST_MEMORY_POINTER_NAME,
    LIVE_MEMORY_ROOT,
    _select_active_memory_candidate,
    _validate_pointer_payload,
)


def refresh_local_feedback_memory_pointer(
    *,
    factory_root: Path,
    build_pack_id: str,
    updated_at: str | None = None,
) -> dict[str, Any]:
    target_pack = discover_pack(factory_root, build_pack_id)
    if target_pack.pack_kind != "build_pack":
        raise ValueError(f"{build_pack_id} is not a build_pack")

    selected = _select_active_memory_candidate(target_pack.pack_root, target_pack.pack_id)
    pointer_path = target_pack.pack_root / LIVE_MEMORY_ROOT / LATEST_MEMORY_POINTER_NAME
    if selected is None:
        pointer_path.unlink(missing_ok=True)
        return {
            "status": "no_compatible_memory",
            "build_pack_id": build_pack_id,
            "pointer_path": str(pointer_path),
            "selected_memory_path": None,
            "selected_run_id": None,
        }

    selected_path, selected_payload, selected_sha256 = selected
    timestamp = updated_at or isoformat_z(read_now())
    pointer_payload = {
        "schema_version": "autonomy-feedback-memory-pointer/v1",
        "updated_at": timestamp,
        "pack_id": target_pack.pack_id,
        "selected_memory_id": selected_payload.get("memory_id"),
        "selected_run_id": selected_payload.get("run_id"),
        "selected_generated_at": selected_payload.get("generated_at"),
        "selected_memory_path": relative_path(target_pack.pack_root, selected_path),
        "selected_memory_sha256": selected_sha256,
        "source_kind": "local_autonomy_run",
        "source_import_id": None,
        "source_artifact_path": relative_path(target_pack.pack_root, selected_path),
        "source_import_report_path": None,
    }
    _validate_pointer_payload(factory_root, pointer_payload)
    write_json(pointer_path, pointer_payload)
    return {
        "status": "activated",
        "build_pack_id": build_pack_id,
        "pointer_path": str(pointer_path),
        "selected_memory_path": str(selected_path),
        "selected_run_id": selected_payload.get("run_id"),
    }


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Refresh latest-memory.json from compatible local feedback memory.")
    parser.add_argument("--factory-root", required=True)
    parser.add_argument("--build-pack-id", required=True)
    parser.add_argument("--output", choices=("json",), default="json")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    factory_root = resolve_factory_root(args.factory_root)
    result = refresh_local_feedback_memory_pointer(
        factory_root=factory_root,
        build_pack_id=args.build_pack_id,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
