from __future__ import annotations

import argparse
import json
from pathlib import Path

from .ambiguity import check_ambiguity
from .alignment import show_alignment
from .benchmark_smoke import benchmark_smoke
from .context_router import route_context
from .doctor import run_doctor
from .grounding import (
    record_business_review,
    run_grounding_check,
    show_business_review,
    show_grounding_cadence,
)
from .memory import (
    delete_memory,
    distill_session_memory,
    read_memory,
    record_memory,
    show_memory_distillation,
)
from .operator_intake import record_operator_intake, show_operator_intake
from .profile import show_profile
from .relationship_state import show_relationship_state
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

    grounding_parser = subparsers.add_parser("show-grounding-cadence")
    grounding_parser.add_argument("--project-root", default=".")
    grounding_parser.add_argument("--output", choices=("json",), default="json")

    business_review_parser = subparsers.add_parser("show-business-review")
    business_review_parser.add_argument("--project-root", default=".")
    business_review_parser.add_argument("--output", choices=("json",), default="json")

    operator_intake_parser = subparsers.add_parser("show-operator-intake")
    operator_intake_parser.add_argument("--project-root", default=".")
    operator_intake_parser.add_argument("--output", choices=("json",), default="json")

    relationship_state_parser = subparsers.add_parser("show-relationship-state")
    relationship_state_parser.add_argument("--project-root", default=".")
    relationship_state_parser.add_argument("--output", choices=("json",), default="json")

    distillation_show_parser = subparsers.add_parser("show-memory-distillation")
    distillation_show_parser.add_argument("--project-root", default=".")
    distillation_show_parser.add_argument("--output", choices=("json",), default="json")

    grounding_check_parser = subparsers.add_parser("run-grounding-check")
    grounding_check_parser.add_argument("--project-root", default=".")
    grounding_check_parser.add_argument("--current-work-summary", required=True)
    grounding_check_parser.add_argument("--intended-outcome")
    grounding_check_parser.add_argument("--output", choices=("json",), default="json")

    ambiguity_parser = subparsers.add_parser("check-ambiguity")
    ambiguity_parser.add_argument("--project-root", default=".")
    ambiguity_parser.add_argument("--scenario", required=True)
    ambiguity_parser.add_argument("--output", choices=("json",), default="json")

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

    distillation_parser = subparsers.add_parser("distill-session-memory")
    distillation_parser.add_argument("--project-root", default=".")
    distillation_parser.add_argument("--distillation-id", required=True)
    distillation_parser.add_argument("--summary", required=True)
    distillation_parser.add_argument("--stable-signal-reason", required=True)
    distillation_parser.add_argument("--source-memory-id", action="append", default=[], required=True)
    distillation_parser.add_argument(
        "--promote-category",
        choices=("preference", "goal", "communication_pattern", "alignment_risk"),
    )
    distillation_parser.add_argument("--promoted-memory-id")
    distillation_parser.add_argument("--next-action")
    distillation_parser.add_argument("--tag", action="append", default=[])
    distillation_parser.add_argument("--source")
    distillation_parser.add_argument("--evidence")
    distillation_parser.add_argument("--confidence", type=float)
    distillation_parser.add_argument("--replace-existing", action="store_true")
    distillation_parser.add_argument("--output", choices=("json",), default="json")

    operator_intake_write_parser = subparsers.add_parser("record-operator-intake")
    operator_intake_write_parser.add_argument("--project-root", default=".")
    operator_intake_write_parser.add_argument("--intake-id", required=True)
    operator_intake_write_parser.add_argument(
        "--category",
        choices=("goal", "preference", "communication_pattern", "alignment_risk"),
        required=True,
    )
    operator_intake_write_parser.add_argument("--summary", required=True)
    operator_intake_write_parser.add_argument("--next-action")
    operator_intake_write_parser.add_argument("--tag", action="append", default=[])
    operator_intake_write_parser.add_argument("--source")
    operator_intake_write_parser.add_argument("--evidence")
    operator_intake_write_parser.add_argument("--confidence", type=float)
    operator_intake_write_parser.add_argument("--replace-existing", action="store_true")
    operator_intake_write_parser.add_argument(
        "--refine-profile-json",
        help="Explicit JSON object used for bounded profile refinement.",
    )
    operator_intake_write_parser.add_argument(
        "--memory-category",
        choices=("goal", "preference", "communication_pattern", "alignment_risk"),
        help="Override the memory category used for the relationship signal.",
    )
    operator_intake_write_parser.add_argument("--output", choices=("json",), default="json")

    business_review_write_parser = subparsers.add_parser("record-business-review")
    business_review_write_parser.add_argument("--project-root", default=".")
    business_review_write_parser.add_argument("--review-id", required=True)
    business_review_write_parser.add_argument("--summary", required=True)
    business_review_write_parser.add_argument("--current-focus", required=True)
    business_review_write_parser.add_argument("--grounded-next-step", required=True)
    business_review_write_parser.add_argument(
        "--assessment",
        choices=("aligned", "unclear", "drift_risk"),
        required=True,
    )
    business_review_write_parser.add_argument("--tag", action="append", default=[])
    business_review_write_parser.add_argument("--source")
    business_review_write_parser.add_argument("--evidence")
    business_review_write_parser.add_argument("--confidence", type=float)
    business_review_write_parser.add_argument("--replace-existing", action="store_true")
    business_review_write_parser.add_argument("--output", choices=("json",), default="json")

    memory_read_parser = subparsers.add_parser("read-memory")
    memory_read_parser.add_argument("--project-root", default=".")
    memory_read_parser.add_argument("--output", choices=("json",), default="json")

    memory_delete_parser = subparsers.add_parser("delete-memory")
    memory_delete_parser.add_argument("--project-root", default=".")
    memory_delete_parser.add_argument("--memory-id", required=True)
    memory_delete_parser.add_argument("--output", choices=("json",), default="json")

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

    if args.command == "show-grounding-cadence":
        result = show_grounding_cadence(Path(args.project_root).resolve())
        print(json.dumps(result, indent=2))
        return 0

    if args.command == "show-business-review":
        result = show_business_review(Path(args.project_root).resolve())
        print(json.dumps(result, indent=2))
        return 0

    if args.command == "show-operator-intake":
        result = show_operator_intake(Path(args.project_root).resolve())
        print(json.dumps(result, indent=2))
        return 0

    if args.command == "show-relationship-state":
        result = show_relationship_state(Path(args.project_root).resolve())
        print(json.dumps(result, indent=2))
        return 0

    if args.command == "show-memory-distillation":
        result = show_memory_distillation(Path(args.project_root).resolve())
        print(json.dumps(result, indent=2))
        return 0

    if args.command == "run-grounding-check":
        result = run_grounding_check(
            Path(args.project_root).resolve(),
            current_work_summary=args.current_work_summary,
            intended_outcome=args.intended_outcome,
        )
        print(json.dumps(result, indent=2))
        return 0 if result["status"] == "pass" else 1

    if args.command == "check-ambiguity":
        result = check_ambiguity(Path(args.project_root).resolve(), args.scenario)
        print(json.dumps(result, indent=2))
        return 0 if result["status"] == "pass" else 1

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

    if args.command == "distill-session-memory":
        result = distill_session_memory(
            Path(args.project_root).resolve(),
            distillation_id=args.distillation_id,
            summary=args.summary,
            stable_signal_reason=args.stable_signal_reason,
            source_memory_ids=list(args.source_memory_id),
            replace_existing=bool(args.replace_existing),
            promote_category=args.promote_category,
            promoted_memory_id=args.promoted_memory_id,
            next_action=args.next_action,
            tags=list(args.tag),
            source=args.source,
            evidence=args.evidence,
            confidence=args.confidence,
        )
        print(json.dumps(result, indent=2))
        return 0 if result["status"] == "pass" else 1

    if args.command == "record-operator-intake":
        result = record_operator_intake(
            Path(args.project_root).resolve(),
            intake_id=args.intake_id,
            category=args.category,
            summary=args.summary,
            next_action=args.next_action,
            tags=list(args.tag),
            replace_existing=bool(args.replace_existing),
            source=args.source,
            evidence=args.evidence,
            confidence=args.confidence,
            refine_profile_json=args.refine_profile_json,
            memory_category=args.memory_category,
        )
        print(json.dumps(result, indent=2))
        return 0 if result["status"] == "pass" else 1

    if args.command == "read-memory":
        result = read_memory(Path(args.project_root).resolve())
        print(json.dumps(result, indent=2))
        return 0

    if args.command == "record-business-review":
        result = record_business_review(
            Path(args.project_root).resolve(),
            review_id=args.review_id,
            summary=args.summary,
            current_focus=args.current_focus,
            grounded_next_step=args.grounded_next_step,
            assessment=args.assessment,
            tags=list(args.tag),
            replace_existing=bool(args.replace_existing),
            source=args.source,
            evidence=args.evidence,
            confidence=args.confidence,
        )
        print(json.dumps(result, indent=2))
        return 0

    if args.command == "delete-memory":
        result = delete_memory(Path(args.project_root).resolve(), memory_id=args.memory_id)
        print(json.dumps(result, indent=2))
        return 0 if result["status"] == "pass" else 1

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
