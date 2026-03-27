#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from factory_ops import isoformat_z, load_json, read_now, relative_path, resolve_factory_root, timestamp_token, write_json


MEMORY_ROOT = Path(".pack-state") / "agent-memory"
POINTER_NAME = "latest-memory.json"
ROOT_PROJECT_OBJECTIVE = Path("contracts/project-objective.json")
ROOT_TASK_BACKLOG = Path("tasks/active-backlog.json")
ROOT_WORK_STATE = Path("status/work-state.json")
PLANNING_LIST = Path("docs/specs/project-pack-factory/PROJECT-PACK-FACTORY-AUTONOMY-PLANNING-LIST.md")
OPERATIONS_NOTE = Path("docs/specs/project-pack-factory/PROJECT-PACK-FACTORY-AUTONOMY-OPERATIONS-NOTE.md")
STATE_BRIEF = Path("docs/specs/project-pack-factory/PROJECT-PACK-FACTORY-AUTONOMY-STATE-BRIEF.md")
DISTILLATION_ROOT = Path(".pack-state") / "autonomy-memory-distillations"
SOURCE_TOOL = "tools/refresh_factory_autonomy_memory.py"
CHECKLIST_PATTERN = re.compile(r"^- \[(?P<done>[ xX])\] (?P<text>.+)$")


def _load_object(path: Path) -> dict[str, Any]:
    payload = load_json(path)
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: JSON document must contain an object")
    return payload


def _find_latest_rehearsal_report(factory_root: Path) -> str | None:
    rehearsal_root = factory_root / ".pack-state" / "multi-hop-autonomy-rehearsals"
    if not rehearsal_root.exists():
        return None
    candidates: list[tuple[str, str]] = []
    for report_path in rehearsal_root.glob("*/rehearsal-report.json"):
        try:
            report = _load_object(report_path)
        except Exception:
            continue
        generated_at = report.get("generated_at")
        if isinstance(generated_at, str):
            candidates.append((generated_at, relative_path(factory_root, report_path)))
    if not candidates:
        return None
    candidates.sort(key=lambda item: item[0])
    return candidates[-1][1]


def _find_latest_promotion_report(factory_root: Path) -> str | None:
    promotion_log_path = factory_root / "registry/promotion-log.json"
    if not promotion_log_path.exists():
        return None
    promotion_log = _load_object(promotion_log_path)
    events = promotion_log.get("events", [])
    if not isinstance(events, list):
        return None
    latest_report_path: str | None = None
    for event in events:
        if not isinstance(event, dict) or event.get("event_type") != "promoted":
            continue
        report_path = event.get("promotion_report_path")
        if isinstance(report_path, str):
            latest_report_path = report_path
    return latest_report_path


def _find_testing_pointer(factory_root: Path) -> str | None:
    testing_dir = factory_root / "deployments" / "testing"
    if not testing_dir.exists():
        return None
    pointers = sorted(path for path in testing_dir.glob("*.json") if path.name != ".gitkeep")
    if not pointers:
        return None
    return relative_path(factory_root, pointers[0])


def _find_latest_distillation_report(factory_root: Path) -> str | None:
    distillation_root = factory_root / DISTILLATION_ROOT
    if not distillation_root.exists():
        return None
    candidates: list[tuple[str, str]] = []
    for report_path in distillation_root.glob("*/distillation-report.json"):
        try:
            report = _load_object(report_path)
        except Exception:
            continue
        generated_at = report.get("generated_at")
        if isinstance(generated_at, str):
            candidates.append((generated_at, relative_path(factory_root, report_path)))
    if not candidates:
        return None
    candidates.sort(key=lambda item: item[0])
    return candidates[-1][1]


def _parse_planning_list(factory_root: Path) -> dict[str, Any]:
    planning_path = factory_root / PLANNING_LIST
    if not planning_path.exists():
        return {
            "sections": {},
            "checklist_items": [],
        }

    sections: dict[str, list[str]] = {}
    checklist_items: list[dict[str, Any]] = []
    current_section: str | None = None
    active_entry: dict[str, Any] | None = None

    def flush_active_entry() -> None:
        nonlocal active_entry
        if active_entry is None:
            return
        text = " ".join(active_entry["parts"]).strip()
        if not text:
            active_entry = None
            return
        if active_entry["kind"] == "checklist":
            checklist_items.append(
                {
                    "section": active_entry["section"],
                    "text": text,
                    "done": active_entry["done"],
                    "overdue": "(overdue)" in text.lower() or "[overdue]" in text.lower(),
                }
            )
        else:
            sections.setdefault(active_entry["section"], []).append(text)
        active_entry = None

    for raw_line in planning_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.rstrip()
        if line.startswith("## "):
            flush_active_entry()
            current_section = line[3:].strip()
            sections.setdefault(current_section, [])
            continue
        if current_section is None:
            continue
        stripped = line.strip()
        if not stripped:
            flush_active_entry()
            continue
        if stripped.startswith("- ") and not CHECKLIST_PATTERN.match(stripped):
            flush_active_entry()
            active_entry = {
                "kind": "bullet",
                "section": current_section,
                "parts": [stripped[2:].strip()],
            }
            continue
        match = CHECKLIST_PATTERN.match(stripped)
        if match is not None:
            flush_active_entry()
            active_entry = {
                "kind": "checklist",
                "section": current_section,
                "done": match.group("done").lower() == "x",
                "parts": [match.group("text").strip()],
            }
            continue
        if active_entry is not None:
            active_entry["parts"].append(stripped)
    flush_active_entry()
    return {
        "sections": sections,
        "checklist_items": checklist_items,
    }


def _format_checklist_item(item: dict[str, Any]) -> str:
    return f"{item['section']}: {item['text']}"


def _load_root_task_tracker(factory_root: Path) -> dict[str, Any] | None:
    objective_path = factory_root / ROOT_PROJECT_OBJECTIVE
    backlog_path = factory_root / ROOT_TASK_BACKLOG
    work_state_path = factory_root / ROOT_WORK_STATE
    if not (objective_path.exists() and backlog_path.exists() and work_state_path.exists()):
        return None
    return {
        "objective": _load_object(objective_path),
        "task_backlog": _load_object(backlog_path),
        "work_state": _load_object(work_state_path),
    }


def _ordered_open_root_tasks(root_tracker: dict[str, Any]) -> list[dict[str, Any]]:
    task_backlog = root_tracker["task_backlog"]
    work_state = root_tracker["work_state"]
    tasks = task_backlog.get("tasks", [])
    if not isinstance(tasks, list):
        return []
    pending_ids = work_state.get("pending_task_ids", [])
    blocked_ids = set(work_state.get("blocked_task_ids", []))
    next_task_id = work_state.get("next_recommended_task_id")
    ordered: list[tuple[tuple[int, float, str], dict[str, Any]]] = []
    for task in tasks:
        if not isinstance(task, dict):
            continue
        task_id = task.get("task_id")
        summary = task.get("summary")
        if not isinstance(task_id, str) or not isinstance(summary, str):
            continue
        if task_id not in pending_ids and task_id not in blocked_ids:
            continue
        status = task.get("status")
        if status not in {"pending", "in_progress", "blocked", "escalated"}:
            continue
        priority = task.get("selection_priority")
        if not isinstance(priority, (int, float)):
            priority = 9999
        ordered.append(
            (
                (
                    0 if task_id == next_task_id else 1,
                    float(priority),
                    task_id,
                ),
                task,
            )
        )
    ordered.sort(key=lambda item: item[0])
    return [item[1] for item in ordered]


def _root_task_items(root_tracker: dict[str, Any]) -> dict[str, list[str]]:
    ordered_open_tasks = _ordered_open_root_tasks(root_tracker)
    open_summaries = [str(task["summary"]) for task in ordered_open_tasks]
    blocked = [str(task["summary"]) for task in ordered_open_tasks if task.get("status") == "blocked"]
    return {
        "next_action_items": open_summaries[:3],
        "pending_items": open_summaries,
        "blocked_items": blocked,
    }


def _default_recommended_next_steps() -> list[str]:
    return [
        "Run the post-autonomy-change maintenance workflow after major autonomy tooling, promotion, or documentation updates.",
        "Refresh template lineage memory when a template family meaningfully changes.",
        "Keep this root-level memory and the factory startup surfaces aligned before ending the session.",
    ]


def _latest_autonomy_proof_summary(
    *,
    latest_rehearsal: str | None,
    latest_promotion: str | None,
) -> str:
    if latest_rehearsal and latest_promotion:
        return (
            "Latest autonomy proof includes a completed multi-hop rehearsal and a"
            f" promotion-backed follow-through: {latest_rehearsal}; {latest_promotion}."
        )
    if latest_rehearsal:
        return f"Latest autonomy proof is the completed multi-hop rehearsal at {latest_rehearsal}."
    if latest_promotion:
        return f"Latest autonomy proof is the promotion-linked evidence at {latest_promotion}."
    return "No autonomy proof artifact has been recorded yet at the factory root."


def _memory_payload(*, factory_root: Path, actor: str, generated_at: str, memory_id: str) -> dict[str, Any]:
    latest_rehearsal = _find_latest_rehearsal_report(factory_root)
    latest_promotion = _find_latest_promotion_report(factory_root)
    testing_pointer = _find_testing_pointer(factory_root)
    latest_distillation = _find_latest_distillation_report(factory_root)
    planning = _parse_planning_list(factory_root)
    root_tracker = _load_root_task_tracker(factory_root)
    checklist_items = planning["checklist_items"]
    fallback_pending_items = [_format_checklist_item(item) for item in checklist_items if item["done"] is False]
    overdue_items = [_format_checklist_item(item) for item in checklist_items if item["done"] is False and item["overdue"]]
    tracker_task_items = _root_task_items(root_tracker) if root_tracker is not None else None
    pending_items = tracker_task_items["pending_items"] if tracker_task_items is not None else fallback_pending_items
    next_action_items = tracker_task_items["next_action_items"] if tracker_task_items is not None else pending_items[:3]
    known_limits = planning["sections"].get("Current Limits", [])
    recommended_next_steps = next_action_items[:]
    maintenance_step = (
        "Run the post-autonomy-change maintenance workflow after major autonomy tooling, promotion, or documentation updates."
    )
    if maintenance_step not in recommended_next_steps:
        recommended_next_steps.append(maintenance_step)
    if not recommended_next_steps:
        recommended_next_steps = _default_recommended_next_steps()
    blocked_items = tracker_task_items["blocked_items"] if tracker_task_items is not None else []
    blockers = [known_limits[0] if known_limits else None]
    if blocked_items:
        blockers.append(blocked_items[0])
    elif pending_items:
        blockers.append(pending_items[0])
    else:
        blockers.append("No open autonomy planning items are currently recorded.")
    blockers = [item for item in blockers if item]

    key_artifacts = [
        str(ROOT_PROJECT_OBJECTIVE),
        str(ROOT_TASK_BACKLOG),
        str(ROOT_WORK_STATE),
        str(PLANNING_LIST),
        str(OPERATIONS_NOTE),
        str(STATE_BRIEF),
        "AGENTS.md",
        "README.md",
    ]
    for candidate in (latest_rehearsal, latest_promotion, testing_pointer, latest_distillation):
        if isinstance(candidate, str):
            key_artifacts.append(candidate)

    return {
        "schema_version": "factory-autonomy-memory/v1",
        "generated_at": generated_at,
        "memory_id": memory_id,
        "memory_tier": {
            "status": "active",
            "tier": "promoted_factory_memory",
            "summary": "Promoted factory-level operating memory for PackFactory root continuation work.",
        },
        "producer": actor,
        "factory_root": str(factory_root),
        "summary": (
            "PackFactory now has factory-default multi-hop autonomy rehearsal, root-level discoverability notes, "
            "promotion gating through compatible autonomy rehearsal evidence, and a built-in canonical readiness "
            "refresh at the end of rehearsal. It can also stop honestly at ambiguous branch boundaries, honor "
            "explicit operator branch-selection hints, including preferred-task and avoid-task guidance, and use "
            "bounded semantic tie-breaking when objective, resume context, and task selection signals make one "
            "candidate clearly stronger. It now has a proven conflict ladder for that broader operator-support "
            "surface plus bounded hint lifetime through `remaining_applications`, and it can distill repeated "
            "autonomy lessons across multiple build-packs into one factory-level memory artifact instead of "
            "leaving those lessons scattered across proving-ground reports."
        ),
        "current_focus": (
            [
                "Track PackFactory root work through canonical objective, backlog, and work-state files.",
                *next_action_items[:2],
            ]
            if root_tracker is not None
            else [
                "Keep factory-level autonomy discoverable from the root startup surfaces.",
                "Keep root-level restart memory current so the next agent can recover the current autonomy toolset quickly.",
                "Promote repeated autonomy lessons from multiple build-packs into one reusable factory-level memory layer.",
            ]
        ),
        "next_action_items": next_action_items,
        "pending_items": pending_items,
        "overdue_items": overdue_items,
        "blockers": blockers,
        "current_capabilities": [
            "Materialize fresh proving-ground build-packs that inherit feedback-memory and autonomy guidance by default.",
            "Run local mid-backlog checkpoints and activate pack-local latest-memory pointers.",
            "Run remote active-task continuity and ready-boundary continuity against a remote target.",
            "Import, compatibility-gate, and activate returned feedback memory automatically when it still matches canonical state.",
            "Run a multi-hop autonomy rehearsal and use that rehearsal as real promotion evidence.",
            "Promote a build-pack only when compatible autonomy rehearsal evidence still matches its current canonical state.",
            "Stop fail-closed when multiple next tasks remain ambiguous after priority and bounded semantic comparison.",
            "Honor explicit operator branch-selection hints from canonical work-state before falling back to semantic tie-breaking.",
            "Apply operator avoid-task guidance to narrow tied candidates before semantic tie-breaking runs.",
            "Resolve conflicting operator hints deterministically with the current ladder of priority, avoid-task guidance, preferred-task guidance, bounded semantic alignment, and fail-closed operator review.",
            "Consume one-shot operator hints through `remaining_applications` so bounded guidance can expire automatically after first use.",
            "Audit active, exhausted, and cleanup-candidate hints through a bounded operator-facing report and prune exhausted inactive hints when requested.",
            "Use bounded semantic alignment to break a next-task tie when the project objective, resume instructions, and task selection signals make one candidate clearly stronger.",
            "Distill repeated strong autonomy lessons across multiple build-packs into one factory-level memory artifact.",
        ],
        "known_limits": known_limits or [
            "A completed multi-hop rehearsal can still require a local canonical readiness refresh before promotion succeeds cleanly in one pass.",
            "Autonomy is strongest in bounded PackFactory workflows rather than broad unscripted project work.",
            "Longer branching backlogs and degraded-connectivity recovery are still planned exercises rather than proven defaults.",
        ],
        "latest_autonomy_proof": _latest_autonomy_proof_summary(
            latest_rehearsal=latest_rehearsal,
            latest_promotion=latest_promotion,
        ),
        "recommended_next_step": recommended_next_steps[0],
        "recommended_next_steps": recommended_next_steps,
        "relevant_commands": [
            "python3 tools/run_multi_hop_autonomy_rehearsal.py --factory-root /home/orchadmin/project-pack-factory --target-build-pack-id <pack-id> --target-display-name \"<name>\" --remote-target-label <target> --remote-host <host> --remote-user <user> --output json",
            "python3 tools/run_local_mid_backlog_checkpoint.py --factory-root /home/orchadmin/project-pack-factory --build-pack-id <pack-id> --run-id <run-id>",
            "python3 tools/run_remote_active_task_continuity_test.py --factory-root /home/orchadmin/project-pack-factory --build-pack-id <pack-id> --remote-target-label <target> --remote-host <host> --remote-user <user> --output json",
            "python3 tools/run_remote_memory_continuity_test.py --factory-root /home/orchadmin/project-pack-factory --build-pack-id <pack-id> --remote-target-label <target> --remote-host <host> --remote-user <user> --output json",
            "python3 tools/apply_branch_selection_hint.py --factory-root /home/orchadmin/project-pack-factory --build-pack-id <pack-id> --hint-id <hint-id> --summary \"<summary>\" --preferred-task-id <task-id> --output json",
            "python3 tools/run_semantic_branch_choice_exercise.py --factory-root /home/orchadmin/project-pack-factory --target-build-pack-id <pack-id> --target-display-name \"<name>\" --remote-target-label <target> --remote-host <host> --remote-user <user> --output json",
            "python3 tools/run_operator_hint_branch_choice_exercise.py --factory-root /home/orchadmin/project-pack-factory --target-build-pack-id <pack-id> --target-display-name \"<name>\" --remote-target-label <target> --remote-host <host> --remote-user <user> --output json",
            "python3 tools/run_operator_avoid_branch_choice_exercise.py --factory-root /home/orchadmin/project-pack-factory --target-build-pack-id <pack-id> --target-display-name \"<name>\" --remote-target-label <target> --remote-host <host> --remote-user <user> --output json",
            "python3 tools/run_operator_hint_conflict_exercise.py --factory-root /home/orchadmin/project-pack-factory --target-build-pack-id <pack-id> --target-display-name \"<name>\" --remote-target-label <target> --remote-host <host> --remote-user <user> --output json",
            "python3 tools/run_ordered_hint_lifecycle_exercise.py --factory-root /home/orchadmin/project-pack-factory --target-build-pack-id <pack-id> --target-display-name \"<name>\" --output json",
            "python3 tools/audit_branch_selection_hints.py --factory-root /home/orchadmin/project-pack-factory --build-pack-id <pack-id> --cleanup-exhausted --output json",
            "python3 tools/run_operator_hint_audit_cleanup_exercise.py --factory-root /home/orchadmin/project-pack-factory --target-build-pack-id <pack-id> --target-display-name \"<name>\" --output json",
            "python3 tools/promote_build_pack.py --factory-root /home/orchadmin/project-pack-factory --request-file <request.json> --output json",
            "python3 tools/distill_autonomy_memory_across_build_packs.py --factory-root /home/orchadmin/project-pack-factory --output json",
            "python3 tools/run_post_autonomy_change_maintenance.py --factory-root /home/orchadmin/project-pack-factory --actor <actor> --output json",
            "python3 tools/refresh_factory_autonomy_memory.py --factory-root /home/orchadmin/project-pack-factory --actor <actor> --output json",
        ],
        "discovery_entrypoints": [
            "AGENTS.md",
            "README.md",
            str(ROOT_PROJECT_OBJECTIVE),
            str(ROOT_TASK_BACKLOG),
            str(ROOT_WORK_STATE),
            str(STATE_BRIEF),
            str(OPERATIONS_NOTE),
            str(PLANNING_LIST),
            ".pack-state/agent-memory/latest-memory.json",
            ".pack-state/autonomy-memory-distillations/",
        ],
        "status_snapshot": {
            "latest_rehearsal_report_path": latest_rehearsal,
            "latest_promotion_report_path": latest_promotion,
            "latest_testing_pointer_path": testing_pointer,
            "latest_distillation_report_path": latest_distillation,
            "current_state_brief_path": str(STATE_BRIEF),
            "planning_list_path": str(PLANNING_LIST),
            "operations_note_path": str(OPERATIONS_NOTE),
        },
        "key_artifact_paths": key_artifacts,
        "notes": [
            "This root memory is advisory restart context for the PackFactory repo itself; registry, deployment, readiness, and promotion surfaces remain canonical.",
            "When the root objective, backlog, and work-state files exist, they are the canonical PackFactory work tracker for factory-level continuation work.",
            "The strongest current proof path is the JSON health checker proving-ground line, especially the promotion-gate pack promoted into testing on 2026-03-25.",
            "Use the autonomy state brief when you need one stable repo-level snapshot of the current memory, restart, branch-choice, and proof baseline.",
            "Pending and next-action items are derived from the root backlog and work-state files when present; the autonomy planning list remains the broader planning surface and overdue fallback.",
            "Priority-driven choice, explicit operator hint overrides, operator avoid-task guidance, bounded semantic branch choice, operator-hint conflict resolution, bounded hint lifetime through `remaining_applications`, operator-hint audit plus cleanup, and factory-level autonomy lesson distillation are now proven capabilities.",
            "After major autonomy changes, run the post-autonomy-change maintenance workflow so root memory, template lineage memory, distilled lessons, and filtered validation all refresh together.",
        ],
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def refresh_factory_autonomy_memory(*, factory_root: Path, actor: str) -> dict[str, Any]:
    now = read_now()
    generated_at = isoformat_z(now)
    memory_id = f"factory-autonomy-memory-{timestamp_token(now)}"
    memory_root = factory_root / MEMORY_ROOT
    memory_root.mkdir(parents=True, exist_ok=True)

    payload = _memory_payload(
        factory_root=factory_root,
        actor=actor,
        generated_at=generated_at,
        memory_id=memory_id,
    )
    memory_path = memory_root / f"{memory_id}.json"
    write_json(memory_path, payload)
    memory_sha256 = _sha256(memory_path)

    pointer_payload = {
        "schema_version": "factory-autonomy-memory-pointer/v1",
        "updated_at": generated_at,
        "selected_memory_id": memory_id,
        "selected_generated_at": generated_at,
        "selected_memory_path": relative_path(factory_root, memory_path),
        "selected_memory_tier": "promoted_factory_memory",
        "selected_memory_sha256": memory_sha256,
        "source_kind": "factory_memory_refresh",
        "source_tool": SOURCE_TOOL,
    }
    pointer_path = memory_root / POINTER_NAME
    write_json(pointer_path, pointer_payload)
    return {
        "status": "completed",
        "memory_id": memory_id,
        "memory_path": str(memory_path),
        "pointer_path": str(pointer_path),
        "generated_at": generated_at,
    }


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Refresh the PackFactory root autonomy memory handoff.")
    parser.add_argument("--factory-root", required=True)
    parser.add_argument("--actor", default="codex")
    parser.add_argument("--output", choices=("json",), default="json")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    result = refresh_factory_autonomy_memory(
        factory_root=resolve_factory_root(args.factory_root),
        actor=args.actor,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
