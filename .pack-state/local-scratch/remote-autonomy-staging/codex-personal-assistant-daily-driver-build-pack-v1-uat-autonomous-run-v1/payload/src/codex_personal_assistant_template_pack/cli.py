from __future__ import annotations

import argparse
import json
from pathlib import Path

from .alignment import show_alignment
from .benchmark_smoke import benchmark_smoke
from .context_router import route_context
from .doctor import run_doctor
from .memory import read_memory, record_memory
from .profile import show_profile
from .validate_project_pack import validate_project_pack
from .workspace_bootstrap import bootstrap_workspace


def main() -> int:
    parser = argparse.ArgumentParser(prog="codex_personal_assistant_template_pack")
    subparsers = parser.add_subparsers(dest="command")

    validate_parser = subparsers.add_parser("validate-project-pack")
    validate_parser.add_argument("--project-root", default=".")
    validate_parser.add_argument("--output", choices=("json",), default="json")

    benchmark_parser = subparsers.add_parser("benchmark-smoke")
    benchmark_parser.add_argument("--project-root", default=".")
    benchmark_parser.add_argument("--output", choices=("json",), default="json")

    profile_parser = subparsers.add_parser("show-profile")
    profile_parser.add_argument("--project-root", default=".")
    profile_parser.add_argument("--output", choices=("json",), default="json")

    alignment_parser = subparsers.add_parser("show-alignment")
    alignment_parser.add_argument("--project-root", default=".")
    alignment_parser.add_argument("--output", choices=("json",), default="json")

    route_parser = subparsers.add_parser("route-context")
    route_parser.add_argument("--project-root", default=".")
    route_parser.add_argument("--topic", required=True)
    route_parser.add_argument("--output", choices=("json",), default="json")

    memory_write_parser = subparsers.add_parser("record-memory")
    memory_write_parser.add_argument("--project-root", default=".")
    memory_write_parser.add_argument("--memory-id", required=True)
    memory_write_parser.add_argument(
        "--category",
        choices=(
            "note",
            "decision",
            "blocker",
            "preference",
            "goal",
            "communication_pattern",
            "alignment_risk",
        ),
        required=True,
    )
    memory_write_parser.add_argument("--summary", required=True)
    memory_write_parser.add_argument("--next-action")
    memory_write_parser.add_argument("--tag", action="append", default=[])
    memory_write_parser.add_argument("--source")
    memory_write_parser.add_argument("--evidence")
    memory_write_parser.add_argument("--confidence", type=float)
    memory_write_parser.add_argument("--replace-existing", action="store_true")
    memory_write_parser.add_argument("--output", choices=("json",), default="json")

    memory_read_parser = subparsers.add_parser("read-memory")
    memory_read_parser.add_argument("--project-root", default=".")
    memory_read_parser.add_argument("--output", choices=("json",), default="json")

    bootstrap_parser = subparsers.add_parser("bootstrap-workspace")
    bootstrap_parser.add_argument("--project-root", default=".")
    bootstrap_parser.add_argument("--target-dir", required=True)
    bootstrap_parser.add_argument("--output", choices=("json",), default="json")

    doctor_parser = subparsers.add_parser("doctor")
    doctor_parser.add_argument("--project-root", default=".")
    doctor_parser.add_argument("--output", choices=("json",), default="json")

    args = parser.parse_args()
    if args.command == "validate-project-pack":
        result = validate_project_pack(Path(args.project_root).resolve())
        print(json.dumps(result, indent=2))
        return 0 if result["status"] == "pass" else 1

    if args.command == "benchmark-smoke":
        result = benchmark_smoke(Path(args.project_root).resolve())
        print(json.dumps(result, indent=2))
        return 0 if result["status"] == "pass" else 1

    if args.command == "show-profile":
        result = show_profile(Path(args.project_root).resolve())
        print(json.dumps(result, indent=2))
        return 0

    if args.command == "show-alignment":
        result = show_alignment(Path(args.project_root).resolve())
        print(json.dumps(result, indent=2))
        return 0

    if args.command == "route-context":
        result = route_context(Path(args.project_root).resolve(), args.topic)
        print(json.dumps(result, indent=2))
        return 0 if result["status"] == "pass" else 1

    if args.command == "record-memory":
        result = record_memory(
            Path(args.project_root).resolve(),
            memory_id=args.memory_id,
            category=args.category,
            summary=args.summary,
            next_action=args.next_action,
            tags=list(args.tag),
            replace_existing=bool(args.replace_existing),
            source=args.source,
            evidence=args.evidence,
            confidence=args.confidence,
        )
        print(json.dumps(result, indent=2))
        return 0 if result["status"] == "pass" else 1

    if args.command == "read-memory":
        result = read_memory(Path(args.project_root).resolve())
        print(json.dumps(result, indent=2))
        return 0

    if args.command == "bootstrap-workspace":
        result = bootstrap_workspace(Path(args.project_root).resolve(), Path(args.target_dir))
        print(json.dumps(result, indent=2))
        return 0 if result["status"] == "pass" else 1

    if args.command == "doctor":
        result = run_doctor(Path(args.project_root).resolve())
        print(json.dumps(result, indent=2))
        return 0 if result["status"] == "pass" else 1

    parser.print_help()
    return 0
