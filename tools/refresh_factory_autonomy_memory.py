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
PLANNING_LIST = Path("docs/specs/project-pack-factory/PROJECT-PACK-FACTORY-AUTONOMY-PLANNING-LIST.md")
OPERATIONS_NOTE = Path("docs/specs/project-pack-factory/PROJECT-PACK-FACTORY-AUTONOMY-OPERATIONS-NOTE.md")
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


def _default_recommended_next_steps() -> list[str]:
    return [
        "Add a single autonomy-to-promotion factory workflow.",
        "Improve autonomy block reporting.",
        "Keep this root-level memory updated after major autonomy workflow or promotion changes.",
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
    planning = _parse_planning_list(factory_root)
    checklist_items = planning["checklist_items"]
    pending_items = [_format_checklist_item(item) for item in checklist_items if item["done"] is False]
    overdue_items = [_format_checklist_item(item) for item in checklist_items if item["done"] is False and item["overdue"]]
    next_action_items = pending_items[:3]
    known_limits = planning["sections"].get("Current Limits", [])
    recommended_next_steps = next_action_items[:]
    if "Keep this root-level memory updated after major autonomy workflow or promotion changes." not in recommended_next_steps:
        recommended_next_steps.append("Keep this root-level memory updated after major autonomy workflow or promotion changes.")
    if not recommended_next_steps:
        recommended_next_steps = _default_recommended_next_steps()
    blockers = [
        known_limits[0],
        pending_items[0] if pending_items else "No open autonomy planning items are currently recorded.",
    ]
    blockers = [item for item in blockers if item]

    key_artifacts = [
        str(PLANNING_LIST),
        str(OPERATIONS_NOTE),
        "AGENTS.md",
        "README.md",
    ]
    for candidate in (latest_rehearsal, latest_promotion, testing_pointer):
        if isinstance(candidate, str):
            key_artifacts.append(candidate)

    return {
        "schema_version": "factory-autonomy-memory/v1",
        "generated_at": generated_at,
        "memory_id": memory_id,
        "producer": actor,
        "factory_root": str(factory_root),
        "summary": (
            "PackFactory now has factory-default multi-hop autonomy rehearsal, root-level discoverability notes, "
            "promotion gating through compatible autonomy rehearsal evidence, and a built-in canonical readiness "
            "refresh at the end of rehearsal. The next highest-value work is to compress the remaining operator "
            "steps into a tighter autonomy-to-promotion path and keep the factory root memory current."
        ),
        "current_focus": [
            "Keep factory-level autonomy discoverable from the root startup surfaces.",
            "Keep root-level restart memory current so the next agent can recover the current autonomy toolset quickly.",
            "Turn the validated rehearsal-plus-promotion path into a smaller operator workflow.",
        ],
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
            "python3 tools/promote_build_pack.py --factory-root /home/orchadmin/project-pack-factory --request-file <request.json> --output json",
            "python3 tools/refresh_factory_autonomy_memory.py --factory-root /home/orchadmin/project-pack-factory --actor <actor> --output json",
        ],
        "discovery_entrypoints": [
            "AGENTS.md",
            "README.md",
            str(OPERATIONS_NOTE),
            str(PLANNING_LIST),
            ".pack-state/agent-memory/latest-memory.json",
        ],
        "status_snapshot": {
            "latest_rehearsal_report_path": latest_rehearsal,
            "latest_promotion_report_path": latest_promotion,
            "latest_testing_pointer_path": testing_pointer,
            "planning_list_path": str(PLANNING_LIST),
            "operations_note_path": str(OPERATIONS_NOTE),
        },
        "key_artifact_paths": key_artifacts,
        "notes": [
            "This root memory is advisory restart context for the PackFactory repo itself; registry, deployment, readiness, and promotion surfaces remain canonical.",
            "The strongest current proof path is the JSON health checker proving-ground line, especially the promotion-gate pack promoted into testing on 2026-03-25.",
            "Pending and overdue items are derived from the autonomy planning list so executive-summary memory stays tied to an explicit planning surface.",
            "Refresh this memory after significant autonomy tooling, rehearsal, or promotion-gate changes so the next agent inherits current factory capabilities and limits.",
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
