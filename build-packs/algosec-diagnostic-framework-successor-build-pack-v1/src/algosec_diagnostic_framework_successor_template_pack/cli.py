from __future__ import annotations

import argparse
import json
from pathlib import Path

from .backup_job import create_backup_snapshot, install_backup_cron
from .benchmark_smoke import benchmark_smoke
from .docpack_hints import import_docpack_hints
from .idea_log import list_idea_notes, record_idea_note, update_idea_note
from .serve_generated_content import describe_generated_content_server, serve_generated_content
from .shallow_surface_map import generate_shallow_surface_map
from .starlight_site import generate_starlight_site
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

    starlight_parser = subparsers.add_parser("generate-starlight-review-shell")
    starlight_parser.add_argument("--project-root", default=".")
    starlight_parser.add_argument("--artifact-root", default=None)
    starlight_parser.add_argument("--site-root", default=None)
    starlight_parser.add_argument("--output", choices=("json",), default="json")

    describe_server_parser = subparsers.add_parser("describe-starlight-review-shell-server")
    describe_server_parser.add_argument("--project-root", default=".")
    describe_server_parser.add_argument("--artifact-root", default=None)
    describe_server_parser.add_argument("--site-root", default=None)
    describe_server_parser.add_argument("--host", default="127.0.0.1")
    describe_server_parser.add_argument("--port", type=int, default=18083)
    describe_server_parser.add_argument("--output", choices=("json",), default="json")

    serve_parser = subparsers.add_parser("serve-starlight-review-shell")
    serve_parser.add_argument("--project-root", default=".")
    serve_parser.add_argument("--artifact-root", default=None)
    serve_parser.add_argument("--site-root", default=None)
    serve_parser.add_argument("--host", default="127.0.0.1")
    serve_parser.add_argument("--port", type=int, default=18083)
    serve_parser.add_argument("--dry-run", action="store_true")
    serve_parser.add_argument("--output", choices=("json",), default="json")

    idea_record_parser = subparsers.add_parser("record-idea-note")
    idea_record_parser.add_argument("--project-root", default=".")
    idea_record_parser.add_argument("--title", required=True)
    idea_record_parser.add_argument("--summary", required=True)
    idea_record_parser.add_argument("--detail", dest="details", action="append", default=[])
    idea_record_parser.add_argument("--tag", dest="tags", action="append", default=[])
    idea_record_parser.add_argument("--related-path", dest="related_paths", action="append", default=[])
    idea_record_parser.add_argument("--related-task-id", dest="related_task_ids", action="append", default=[])
    idea_record_parser.add_argument("--related-topic", dest="related_topics", action="append", default=[])
    idea_record_parser.add_argument("--captured-by", default="operator")
    idea_record_parser.add_argument(
        "--source-kind",
        choices=("operator_chat", "agent_inference", "runtime_observation", "imported_evidence", "doc_review"),
        default="operator_chat",
    )
    idea_record_parser.add_argument(
        "--note-kind",
        choices=("behavioral_note", "product_idea", "operator_theory", "workflow_note", "cookbook_note"),
        default="behavioral_note",
    )
    idea_record_parser.add_argument(
        "--evidence-state",
        choices=("open_question", "operator_theory", "observed_practice", "validated_behavior"),
        default="operator_theory",
    )
    idea_record_parser.add_argument(
        "--review-state",
        choices=("unreviewed", "in_review", "reviewed", "converted_to_task"),
        default="unreviewed",
    )
    idea_record_parser.add_argument("--status", choices=("active", "archived"), default="active")
    idea_record_parser.add_argument("--output", choices=("json",), default="json")

    idea_list_parser = subparsers.add_parser("list-idea-notes")
    idea_list_parser.add_argument("--project-root", default=".")
    idea_list_parser.add_argument("--status", choices=("active", "archived"), default=None)
    idea_list_parser.add_argument(
        "--review-state",
        choices=("unreviewed", "in_review", "reviewed", "converted_to_task"),
        default=None,
    )
    idea_list_parser.add_argument("--limit", type=int, default=20)
    idea_list_parser.add_argument("--output", choices=("json",), default="json")

    idea_update_parser = subparsers.add_parser("update-idea-note")
    idea_update_parser.add_argument("--project-root", default=".")
    idea_update_parser.add_argument("--note-id", required=True)
    idea_update_parser.add_argument("--title", default=None)
    idea_update_parser.add_argument("--summary", default=None)
    idea_update_parser.add_argument(
        "--review-state",
        choices=("unreviewed", "in_review", "reviewed", "converted_to_task"),
        default=None,
    )
    idea_update_parser.add_argument("--status", choices=("active", "archived"), default=None)
    idea_update_parser.add_argument(
        "--evidence-state",
        choices=("open_question", "operator_theory", "observed_practice", "validated_behavior"),
        default=None,
    )
    idea_update_parser.add_argument(
        "--note-kind",
        choices=("behavioral_note", "product_idea", "operator_theory", "workflow_note", "cookbook_note"),
        default=None,
    )
    idea_update_parser.add_argument("--add-detail", dest="add_details", action="append", default=[])
    idea_update_parser.add_argument("--add-tag", dest="add_tags", action="append", default=[])
    idea_update_parser.add_argument("--add-related-path", dest="add_related_paths", action="append", default=[])
    idea_update_parser.add_argument("--add-related-task-id", dest="add_related_task_ids", action="append", default=[])
    idea_update_parser.add_argument("--add-related-topic", dest="add_related_topics", action="append", default=[])
    idea_update_parser.add_argument("--output", choices=("json",), default="json")

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

    if args.command == "generate-starlight-review-shell":
        result = generate_starlight_site(
            project_root=Path(args.project_root).resolve(),
            artifact_root=args.artifact_root,
            site_root=args.site_root,
        )
        print(json.dumps(result, indent=2))
        return 0 if result["status"] == "pass" else 1

    if args.command == "describe-starlight-review-shell-server":
        result = describe_generated_content_server(
            project_root=Path(args.project_root).resolve(),
            artifact_root=args.artifact_root,
            site_root=args.site_root,
            host=args.host,
            port=args.port,
        )
        print(json.dumps(result, indent=2))
        return 0 if result["status"] == "pass" else 1

    if args.command == "serve-starlight-review-shell":
        result = serve_generated_content(
            project_root=Path(args.project_root).resolve(),
            artifact_root=args.artifact_root,
            site_root=args.site_root,
            host=args.host,
            port=args.port,
            dry_run=args.dry_run,
        )
        if args.dry_run:
            print(json.dumps(result, indent=2))
        return 0 if result["status"] == "pass" else 1

    if args.command == "record-idea-note":
        result = record_idea_note(
            project_root=Path(args.project_root).resolve(),
            title=args.title,
            summary=args.summary,
            details=list(args.details),
            tags=list(args.tags),
            related_paths=list(args.related_paths),
            related_task_ids=list(args.related_task_ids),
            related_topics=list(args.related_topics),
            captured_by=args.captured_by,
            source_kind=args.source_kind,
            note_kind=args.note_kind,
            evidence_state=args.evidence_state,
            review_state=args.review_state,
            status=args.status,
        )
        print(json.dumps(result, indent=2))
        return 0 if result["status"] == "pass" else 1

    if args.command == "list-idea-notes":
        result = list_idea_notes(
            project_root=Path(args.project_root).resolve(),
            status=args.status,
            review_state=args.review_state,
            limit=args.limit,
        )
        print(json.dumps(result, indent=2))
        return 0 if result["status"] == "pass" else 1

    if args.command == "update-idea-note":
        result = update_idea_note(
            project_root=Path(args.project_root).resolve(),
            note_id=args.note_id,
            title=args.title,
            summary=args.summary,
            review_state=args.review_state,
            status=args.status,
            evidence_state=args.evidence_state,
            note_kind=args.note_kind,
            add_details=list(args.add_details),
            add_tags=list(args.add_tags),
            add_related_paths=list(args.add_related_paths),
            add_related_task_ids=list(args.add_related_task_ids),
            add_related_topics=list(args.add_related_topics),
        )
        print(json.dumps(result, indent=2))
        return 0 if result["status"] == "pass" else 1

    parser.print_help()
    return 0
