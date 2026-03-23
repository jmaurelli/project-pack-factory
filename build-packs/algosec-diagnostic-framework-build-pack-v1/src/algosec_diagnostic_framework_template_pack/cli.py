from __future__ import annotations

import argparse
import json
from pathlib import Path

from .benchmark_smoke import benchmark_smoke
from .runtime_baseline import generate_support_baseline
from .validate_project_pack import validate_project_pack


def main() -> int:
    parser = argparse.ArgumentParser(prog="algosec_diagnostic_framework_template_pack")
    subparsers = parser.add_subparsers(dest="command")

    validate_parser = subparsers.add_parser("validate-project-pack")
    validate_parser.add_argument("--project-root", default=".")
    validate_parser.add_argument("--output", choices=("json",), default="json")

    benchmark_parser = subparsers.add_parser("benchmark-smoke")
    benchmark_parser.add_argument("--project-root", default=".")
    benchmark_parser.add_argument("--output", choices=("json",), default="json")

    baseline_parser = subparsers.add_parser("generate-support-baseline")
    baseline_parser.add_argument("--project-root", default=".")
    baseline_parser.add_argument("--target-label", default="algosec-lab")
    baseline_parser.add_argument("--artifact-root", default=None)
    baseline_parser.add_argument("--output", choices=("json",), default="json")

    args = parser.parse_args()
    if args.command == "validate-project-pack":
        result = validate_project_pack(Path(args.project_root).resolve())
        print(json.dumps(result, indent=2))
        return 0 if result["status"] == "pass" else 1

    if args.command == "benchmark-smoke":
        result = benchmark_smoke(Path(args.project_root).resolve())
        print(json.dumps(result, indent=2))
        return 0 if result["status"] == "pass" else 1

    if args.command == "generate-support-baseline":
        result = generate_support_baseline(
            project_root=Path(args.project_root).resolve(),
            target_label=args.target_label,
            artifact_root=args.artifact_root,
        )
        print(json.dumps(result, indent=2))
        return 0 if result["status"] == "pass" else 1

    parser.print_help()
    return 0
