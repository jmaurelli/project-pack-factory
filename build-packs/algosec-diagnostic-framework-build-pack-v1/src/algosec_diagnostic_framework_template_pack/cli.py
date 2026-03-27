from __future__ import annotations

import argparse
import json
from pathlib import Path

from .benchmark_smoke import benchmark_smoke
from .delegated_codex import (
    launch_target_local_codex,
    pull_delegated_result_bundle,
    record_delegated_review,
    write_delegated_task_request,
)
from .runtime_baseline import generate_support_baseline
from .serve_generated_content import serve_generated_content
from .starlight_site import generate_starlight_site
from .starlight_prototypes import generate_starlight_prototypes
from .target_connection import target_heartbeat, target_preflight, target_shell_command
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

    starlight_parser = subparsers.add_parser("generate-starlight-site")
    starlight_parser.add_argument("--project-root", default=".")
    starlight_parser.add_argument("--artifact-root", default=None)
    starlight_parser.add_argument("--site-root", default=None)
    starlight_parser.add_argument("--output", choices=("json",), default="json")

    prototype_parser = subparsers.add_parser("generate-starlight-prototypes")
    prototype_parser.add_argument("--project-root", default=".")
    prototype_parser.add_argument("--output-root", default=None)
    prototype_parser.add_argument("--output", choices=("json",), default="json")

    serve_parser = subparsers.add_parser("serve-generated-content")
    serve_parser.add_argument("--project-root", default=".")
    serve_parser.add_argument("--artifact-root", default=None)
    serve_parser.add_argument("--site-root", default=None)
    serve_parser.add_argument("--host", default="0.0.0.0")
    serve_parser.add_argument("--port", type=int, default=18082)
    serve_parser.add_argument("--dry-run", action="store_true")
    serve_parser.add_argument("--output", choices=("json",), default="json")

    target_preflight_parser = subparsers.add_parser("target-preflight")
    target_preflight_parser.add_argument("--project-root", default=".")
    target_preflight_parser.add_argument("--profile-path", default=None)
    target_preflight_parser.add_argument("--dry-run", action="store_true")
    target_preflight_parser.add_argument("--output", choices=("json",), default="json")

    target_heartbeat_parser = subparsers.add_parser("target-heartbeat")
    target_heartbeat_parser.add_argument("--project-root", default=".")
    target_heartbeat_parser.add_argument("--profile-path", default=None)
    target_heartbeat_parser.add_argument("--dry-run", action="store_true")
    target_heartbeat_parser.add_argument("--output", choices=("json",), default="json")

    target_shell_parser = subparsers.add_parser("target-shell-command")
    target_shell_parser.add_argument("--project-root", default=".")
    target_shell_parser.add_argument("--profile-path", default=None)
    target_shell_parser.add_argument("--command", dest="target_command", required=True)
    target_shell_parser.add_argument("--timeout-seconds", type=int, default=None)
    target_shell_parser.add_argument("--retry-count", type=int, default=0)
    target_shell_parser.add_argument("--dry-run", action="store_true")
    target_shell_parser.add_argument("--output", choices=("json",), default="json")

    delegation_request_parser = subparsers.add_parser("target-delegation-request")
    delegation_request_parser.add_argument("--project-root", default=".")
    delegation_request_parser.add_argument("--run-id", required=True)
    delegation_request_parser.add_argument("--task-id", required=True)
    delegation_request_parser.add_argument("--delegation-tier", choices=("observe_only", "guided_change_lab"), required=True)
    delegation_request_parser.add_argument("--scope-summary", required=True)
    delegation_request_parser.add_argument("--allowed-target", action="append", default=[])
    delegation_request_parser.add_argument("--expected-output", action="append", default=[])
    delegation_request_parser.add_argument("--time-budget-seconds", type=int, default=900)
    delegation_request_parser.add_argument("--generated-by", default="adf-dev")
    delegation_request_parser.add_argument("--delegation-run-id", default=None)
    delegation_request_parser.add_argument("--profile-path", default=None)
    delegation_request_parser.add_argument("--skip-target-push", action="store_true")
    delegation_request_parser.add_argument("--dry-run", action="store_true")
    delegation_request_parser.add_argument("--output", choices=("json",), default="json")

    delegation_pull_parser = subparsers.add_parser("target-delegation-pull")
    delegation_pull_parser.add_argument("--project-root", default=".")
    delegation_pull_parser.add_argument("--run-id", required=True)
    delegation_pull_parser.add_argument("--delegation-run-id", required=True)
    delegation_pull_parser.add_argument("--profile-path", default=None)
    delegation_pull_parser.add_argument("--dry-run", action="store_true")
    delegation_pull_parser.add_argument("--output", choices=("json",), default="json")

    delegation_launch_parser = subparsers.add_parser("target-delegation-launch-codex")
    delegation_launch_parser.add_argument("--project-root", default=".")
    delegation_launch_parser.add_argument("--run-id", required=True)
    delegation_launch_parser.add_argument("--delegation-run-id", required=True)
    delegation_launch_parser.add_argument("--profile-path", default=None)
    delegation_launch_parser.add_argument("--timeout-seconds", type=int, default=900)
    delegation_launch_parser.add_argument("--dry-run", action="store_true")
    delegation_launch_parser.add_argument("--output", choices=("json",), default="json")

    delegation_review_parser = subparsers.add_parser("target-delegation-review")
    delegation_review_parser.add_argument("--project-root", default=".")
    delegation_review_parser.add_argument("--run-id", required=True)
    delegation_review_parser.add_argument("--delegation-run-id", required=True)
    delegation_review_parser.add_argument(
        "--checkpoint-reason",
        choices=("paused_for_review", "task_slice_complete", "evidence_ready", "blocked_boundary", "recovery_snapshot"),
        default="task_slice_complete",
    )
    delegation_review_parser.add_argument(
        "--review-outcome",
        choices=("accepted", "partial", "rejected", "deferred"),
        default="accepted",
    )
    delegation_review_parser.add_argument("--generated-by", default="adf-dev")
    delegation_review_parser.add_argument("--profile-path", default=None)
    delegation_review_parser.add_argument("--output", choices=("json",), default="json")

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

    if args.command == "generate-starlight-site":
        result = generate_starlight_site(
            project_root=Path(args.project_root).resolve(),
            artifact_root=args.artifact_root,
            site_root=args.site_root,
        )
        print(json.dumps(result, indent=2))
        return 0 if result["status"] == "pass" else 1

    if args.command == "generate-starlight-prototypes":
        result = generate_starlight_prototypes(
            project_root=Path(args.project_root).resolve(),
            output_root=args.output_root,
        )
        print(json.dumps(result, indent=2))
        return 0 if result["status"] == "pass" else 1

    if args.command == "serve-generated-content":
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
        return 0

    if args.command == "target-preflight":
        result = target_preflight(
            project_root=Path(args.project_root).resolve(),
            profile_path=args.profile_path,
            dry_run=args.dry_run,
        )
        print(json.dumps(result, indent=2))
        return 0 if result["status"] == "pass" else 1

    if args.command == "target-heartbeat":
        result = target_heartbeat(
            project_root=Path(args.project_root).resolve(),
            profile_path=args.profile_path,
            dry_run=args.dry_run,
        )
        print(json.dumps(result, indent=2))
        return 0 if result["status"] == "pass" else 1

    if args.command == "target-shell-command":
        result = target_shell_command(
            project_root=Path(args.project_root).resolve(),
            profile_path=args.profile_path,
            command=args.target_command,
            timeout_seconds=args.timeout_seconds,
            retry_count=args.retry_count,
            dry_run=args.dry_run,
        )
        print(json.dumps(result, indent=2))
        return 0 if result["status"] == "pass" else 1

    if args.command == "target-delegation-request":
        result = write_delegated_task_request(
            project_root=Path(args.project_root).resolve(),
            run_id=args.run_id,
            task_id=args.task_id,
            delegation_tier=args.delegation_tier,
            scope_summary=args.scope_summary,
            allowed_targets=args.allowed_target,
            expected_outputs=args.expected_output,
            time_budget_seconds=args.time_budget_seconds,
            generated_by=args.generated_by,
            delegation_run_id=args.delegation_run_id,
            profile_path=args.profile_path,
            push_to_target=not args.skip_target_push,
            dry_run=args.dry_run,
        )
        print(json.dumps(result, indent=2))
        return 0 if result["status"] == "pass" else 1

    if args.command == "target-delegation-pull":
        result = pull_delegated_result_bundle(
            project_root=Path(args.project_root).resolve(),
            run_id=args.run_id,
            delegation_run_id=args.delegation_run_id,
            profile_path=args.profile_path,
            dry_run=args.dry_run,
        )
        print(json.dumps(result, indent=2))
        return 0 if result["status"] == "pass" else 1

    if args.command == "target-delegation-launch-codex":
        result = launch_target_local_codex(
            project_root=Path(args.project_root).resolve(),
            run_id=args.run_id,
            delegation_run_id=args.delegation_run_id,
            profile_path=args.profile_path,
            timeout_seconds=args.timeout_seconds,
            dry_run=args.dry_run,
        )
        print(json.dumps(result, indent=2))
        return 0 if result["status"] == "pass" else 1

    if args.command == "target-delegation-review":
        result = record_delegated_review(
            project_root=Path(args.project_root).resolve(),
            run_id=args.run_id,
            delegation_run_id=args.delegation_run_id,
            checkpoint_reason=args.checkpoint_reason,
            review_outcome=args.review_outcome,
            generated_by=args.generated_by,
            profile_path=args.profile_path,
        )
        print(json.dumps(result, indent=2))
        return 0 if result["status"] == "pass" else 1

    parser.print_help()
    return 0
