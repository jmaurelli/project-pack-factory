from __future__ import annotations

import argparse
import json
from pathlib import Path

from ..task_goal import VALIDATOR_EXIT_CODES, validate_task_goal


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate a task record for lightweight goal-loop use.")
    parser.add_argument("--task-record", required=True, help="Path to the canonical task-record YAML or JSON file.")
    parser.add_argument("--task-record-schema", default=None, help="Optional explicit task-record schema path override.")
    parser.add_argument("--output", choices=("text", "json"), default="text")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    payload = validate_task_goal(
        task_record_path=Path(args.task_record),
        schema_path=Path(args.task_record_schema) if args.task_record_schema is not None else None,
    )
    if args.output == "json":
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"Task-goal validation result={payload['result']}")
        for error in payload["errors"]:
            print(json.dumps(error, sort_keys=True))
    return VALIDATOR_EXIT_CODES[payload["result"]]


if __name__ == "__main__":
    raise SystemExit(main())
