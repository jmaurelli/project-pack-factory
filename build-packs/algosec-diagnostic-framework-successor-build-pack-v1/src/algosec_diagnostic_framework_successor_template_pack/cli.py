from __future__ import annotations

import argparse
import json
from pathlib import Path

from .benchmark_smoke import benchmark_smoke
from .docpack_hints import import_docpack_hints
from .shallow_surface_map import generate_shallow_surface_map
from .validate_project_pack import validate_project_pack


def main() -> int:
    parser = argparse.ArgumentParser(prog="algosec_diagnostic_framework_successor_template_pack")
    subparsers = parser.add_subparsers(dest="command")

    validate_parser = subparsers.add_parser("validate-project-pack")
    validate_parser.add_argument("--project-root", default=".")
    validate_parser.add_argument("--output", choices=("json",), default="json")

    benchmark_parser = subparsers.add_parser("benchmark-smoke")
    benchmark_parser.add_argument("--project-root", default=".")
    benchmark_parser.add_argument("--output", choices=("json",), default="json")

    docpack_parser = subparsers.add_parser("import-docpack-hints")
    docpack_parser.add_argument("--project-root", default=".")
    docpack_parser.add_argument("--ssh-destination", default="adf-dev")
    docpack_parser.add_argument("--remote-docpack-root", default="/ai-workflow/out/asms/A33.10/asms-docpack")
    docpack_parser.add_argument("--artifact-root", default=None)
    docpack_parser.add_argument("--output", choices=("json",), default="json")

    surface_map_parser = subparsers.add_parser("generate-shallow-surface-map")
    surface_map_parser.add_argument("--project-root", default=".")
    surface_map_parser.add_argument("--target-label", default="local-host")
    surface_map_parser.add_argument("--artifact-root", default=None)
    surface_map_parser.add_argument("--docpack-hints-path", default=None)
    surface_map_parser.add_argument("--output", choices=("json",), default="json")

    args = parser.parse_args()
    if args.command == "validate-project-pack":
        result = validate_project_pack(Path(args.project_root).resolve())
        print(json.dumps(result, indent=2))
        return 0 if result["status"] == "pass" else 1

    if args.command == "benchmark-smoke":
        result = benchmark_smoke(Path(args.project_root).resolve())
        print(json.dumps(result, indent=2))
        return 0 if result["status"] == "pass" else 1

    if args.command == "import-docpack-hints":
        result = import_docpack_hints(
            project_root=Path(args.project_root).resolve(),
            ssh_destination=args.ssh_destination,
            remote_docpack_root=args.remote_docpack_root,
            artifact_root=args.artifact_root,
        )
        print(json.dumps(result, indent=2))
        return 0 if result["status"] == "pass" else 1

    if args.command == "generate-shallow-surface-map":
        result = generate_shallow_surface_map(
            project_root=Path(args.project_root).resolve(),
            target_label=args.target_label,
            artifact_root=args.artifact_root,
            docpack_hints_path=args.docpack_hints_path,
        )
        print(json.dumps(result, indent=2))
        return 0 if result["status"] == "pass" else 1

    parser.print_help()
    return 0
