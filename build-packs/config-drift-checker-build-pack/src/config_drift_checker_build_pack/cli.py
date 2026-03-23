from __future__ import annotations

import argparse
import json
from pathlib import Path

from .benchmark_smoke import benchmark_smoke
from .drift_runtime import check_drift
from .validate_project_pack import validate_project_pack


def _add_check_drift_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--rules")
    parser.add_argument("--fail-on", choices=("warning", "blocking"), default="blocking")
    parser.add_argument("--output", choices=("json",), default="json")


def _run_check_drift_command(args: argparse.Namespace) -> int:
    result = check_drift(
        Path(args.baseline),
        Path(args.candidate),
        rules_path=Path(args.rules) if args.rules else None,
        fail_on=args.fail_on,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "pass" else 2 if result["status"] == "review_required" else 1


def main() -> int:
    parser = argparse.ArgumentParser(prog="config-drift-checker-build-pack")
    subparsers = parser.add_subparsers(dest="command")

    drift_parser = subparsers.add_parser("check-drift")
    _add_check_drift_arguments(drift_parser)

    validate_parser = subparsers.add_parser("validate-project-pack")
    validate_parser.add_argument("--project-root", default=".")
    validate_parser.add_argument("--output", choices=("json",), default="json")

    benchmark_parser = subparsers.add_parser("benchmark-smoke")
    benchmark_parser.add_argument("--project-root", default=".")
    benchmark_parser.add_argument("--output", choices=("json",), default="json")

    args = parser.parse_args()
    if args.command == "check-drift":
        return _run_check_drift_command(args)

    if args.command == "validate-project-pack":
        result = validate_project_pack(Path(args.project_root).resolve())
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["status"] == "pass" else 1

    if args.command == "benchmark-smoke":
        result = benchmark_smoke(Path(args.project_root).resolve())
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["status"] == "pass" else 1

    parser.print_help()
    return 0


def main_check_drift() -> int:
    parser = argparse.ArgumentParser(prog="check-drift")
    _add_check_drift_arguments(parser)
    args = parser.parse_args()
    return _run_check_drift_command(args)
