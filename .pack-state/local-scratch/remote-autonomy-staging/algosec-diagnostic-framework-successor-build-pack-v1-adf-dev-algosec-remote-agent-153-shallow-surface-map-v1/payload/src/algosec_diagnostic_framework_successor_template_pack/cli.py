from __future__ import annotations

import argparse
import json
from pathlib import Path

from .backup_job import create_backup_snapshot, install_backup_cron
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

    backup_parser = subparsers.add_parser("create-backup-snapshot")
    backup_parser.add_argument("--project-root", default=".")
    backup_parser.add_argument("--backup-root", default=None)
    backup_parser.add_argument("--retain-count", type=int, default=7)
    backup_parser.add_argument("--output", choices=("json",), default="json")

    backup_install_parser = subparsers.add_parser("install-backup-cron")
    backup_install_parser.add_argument("--project-root", default=".")
    backup_install_parser.add_argument("--schedule", default="17 3 * * *")
    backup_install_parser.add_argument("--backup-root", default=None)
    backup_install_parser.add_argument("--retain-count", type=int, default=7)
    backup_install_parser.add_argument("--install-root", default=None)
    backup_install_parser.add_argument("--dry-run", action="store_true")
    backup_install_parser.add_argument("--output", choices=("json",), default="json")

    docpack_parser = subparsers.add_parser("import-docpack-hints")
    docpack_parser.add_argument("--project-root", default=".")
    docpack_parser.add_argument("--ssh-destination", default="adf-dev")
    docpack_parser.add_argument("--remote-docpack-root", default="/ai-workflow/out/asms/A33.10/asms-docpack")
    docpack_parser.add_argument("--artifact-root", default=None)
    docpack_parser.add_argument("--output", choices=("json",), default="json")

    surface_map_parser = subparsers.add_parser("generate-shallow-surface-map")
    surface_map_parser.add_argument("--project-root", default=".")
    surface_map_parser.add_argument("--target-label", default="local-host")
    surface_map_parser.add_argument("--target-connection-profile", default=None)
    surface_map_parser.add_argument("--artifact-root", default=None)
    surface_map_parser.add_argument("--docpack-hints-path", default=None)
    surface_map_parser.add_argument("--mirror-into-run-id", default=None)
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

    if args.command == "create-backup-snapshot":
        result = create_backup_snapshot(
            project_root=Path(args.project_root).resolve(),
            backup_root=args.backup_root,
            retain_count=args.retain_count,
        )
        print(json.dumps(result, indent=2))
        return 0 if result["status"] == "pass" else 1

    if args.command == "install-backup-cron":
        result = install_backup_cron(
            project_root=Path(args.project_root).resolve(),
            schedule=args.schedule,
            backup_root=args.backup_root,
            retain_count=args.retain_count,
            install_root=args.install_root,
            dry_run=args.dry_run,
        )
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
            target_connection_profile=args.target_connection_profile,
            artifact_root=args.artifact_root,
            docpack_hints_path=args.docpack_hints_path,
            mirror_into_run_id=args.mirror_into_run_id,
        )
        print(json.dumps(result, indent=2))
        return 0 if result["status"] == "pass" else 1

    parser.print_help()
    return 0
