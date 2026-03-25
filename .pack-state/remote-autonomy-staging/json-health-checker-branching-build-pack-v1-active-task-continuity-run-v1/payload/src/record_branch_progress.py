#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_object(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit(f"{path} did not contain a JSON object")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Record a bounded branching continuity checkpoint artifact.")
    parser.add_argument("--pack-root", required=True)
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--branch-lane", required=True)
    parser.add_argument("--output", choices=("json",), default="json")
    args = parser.parse_args()

    pack_root = Path(args.pack_root).resolve()
    work_state = load_object(pack_root / "status/work-state.json")
    readiness = load_object(pack_root / "status/readiness.json")
    pointer_path = pack_root / ".pack-state" / "agent-memory" / "latest-memory.json"
    pointer_payload = load_object(pointer_path) if pointer_path.exists() else None

    timestamp = now()
    artifact_dir = pack_root / "eval" / "history" / f"{args.task_id}-{timestamp.replace(':', '').replace('-', '').lower()}"
    artifact_dir.mkdir(parents=True, exist_ok=False)
    artifact_path = artifact_dir / "branch-checkpoint-result.json"
    artifact_payload = {
        "schema_version": "branch-checkpoint-result/v1",
        "generated_at": timestamp,
        "task_id": args.task_id,
        "branch_lane": args.branch_lane,
        "active_task_id": work_state.get("active_task_id"),
        "next_recommended_task_id": work_state.get("next_recommended_task_id"),
        "ready_for_deployment": readiness.get("ready_for_deployment"),
        "readiness_state": readiness.get("readiness_state"),
        "memory_pointer_present": pointer_payload is not None,
        "memory_pointer_run_id": None if pointer_payload is None else pointer_payload.get("selected_run_id"),
        "summary": "Recorded a bounded branching checkpoint artifact without mutating canonical readiness state.",
    }
    artifact_path.write_text(json.dumps(artifact_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "status": "completed",
                "generated_at": timestamp,
                "evidence_paths": [artifact_path.relative_to(pack_root).as_posix()],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
