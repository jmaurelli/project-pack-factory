#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def main() -> int:
    parser = argparse.ArgumentParser(description="Record a bounded ordered-hint lifecycle checkpoint artifact.")
    parser.add_argument("--pack-root", required=True)
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--lane", required=True)
    parser.add_argument("--output", choices=("json",), default="json")
    args = parser.parse_args()

    pack_root = Path(args.pack_root).resolve()
    timestamp = now()
    artifact_dir = pack_root / "eval" / "history" / f"{args.task_id}-{timestamp.replace(':', '').replace('-', '').lower()}"
    artifact_dir.mkdir(parents=True, exist_ok=False)
    artifact_path = artifact_dir / "ordered-hint-lifecycle-checkpoint-result.json"
    artifact_payload = {
        "schema_version": "ordered-hint-lifecycle-checkpoint-result/v1",
        "generated_at": timestamp,
        "task_id": args.task_id,
        "lane": args.lane,
        "summary": "Recorded a bounded ordered-hint lifecycle checkpoint artifact without mutating canonical readiness state.",
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
