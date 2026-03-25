#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, cast

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from factory_ops import discover_pack, isoformat_z, load_json, read_now, resolve_factory_root, write_json
from record_autonomy_run import append_event, finalize_run, start_run
from refresh_local_feedback_memory_pointer import refresh_local_feedback_memory_pointer

TOKEN_PATTERN = re.compile(r"[a-z0-9]+")
SEMANTIC_STOPWORDS = {
    "and",
    "the",
    "for",
    "with",
    "that",
    "this",
    "from",
    "into",
    "after",
    "before",
    "when",
    "then",
    "than",
    "only",
    "same",
    "shared",
    "through",
    "during",
    "task",
    "tasks",
    "next",
    "pack",
    "build",
    "record",
}


def _load_object(path: Path) -> dict[str, Any]:
    payload = load_json(path)
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: JSON document must contain an object")
    return cast(dict[str, Any], payload)


def _load_matching_memory(pack_root: Path, active_task_id: str) -> tuple[bool, str, list[str]]:
    pointer_path = pack_root / ".pack-state" / "agent-memory" / "latest-memory.json"
    if not pointer_path.exists():
        return False, "canonical_only", ["No active latest-memory pointer was present; selected the active task from canonical state."]
    pointer_payload = _load_object(pointer_path)
    selected_memory_path = pointer_payload.get("selected_memory_path")
    if not isinstance(selected_memory_path, str) or not selected_memory_path:
        return False, "canonical_only", ["The active latest-memory pointer was incomplete; used canonical state only."]
    memory_path = (pack_root / selected_memory_path).resolve()
    if not memory_path.exists():
        return False, "canonical_only", ["The active latest-memory pointer referenced a missing file; used canonical state only."]
    memory_payload = _load_object(memory_path)
    if memory_payload.get("active_task_id") != active_task_id or memory_payload.get("next_recommended_task_id") != active_task_id:
        return False, "canonical_only", ["The active latest-memory pointer did not match the current active task; used canonical state only."]
    return True, "canonical_plus_memory", [
        f"Loaded local feedback memory from {memory_path.as_posix()} and confirmed it matched active task `{active_task_id}`."
    ]


def _find_active_task(backlog: dict[str, Any], active_task_id: str) -> dict[str, Any]:
    for task in cast(list[dict[str, Any]], backlog.get("tasks", [])):
        if isinstance(task, dict) and task.get("task_id") == active_task_id:
            return task
    raise ValueError(f"active task `{active_task_id}` was not found in tasks/active-backlog.json")


def _run_task_command(pack_root: Path, command: str) -> dict[str, Any]:
    completed = subprocess.run(
        command,
        shell=True,
        executable="/bin/bash",
        cwd=pack_root,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or completed.stdout.strip() or f"command failed: {command}")
    stdout = completed.stdout.strip()
    if not stdout:
        return {"status": "completed", "generated_at": isoformat_z(read_now()), "evidence_paths": []}
    payload = json.loads(stdout)
    if not isinstance(payload, dict):
        raise ValueError(f"command output must be a JSON object: {command}")
    return payload


def _merge_validation_results(existing: list[dict[str, Any]], fresh: dict[str, Any]) -> list[dict[str, Any]]:
    merged = [result for result in existing if result.get("validation_id") != fresh.get("validation_id")]
    merged.append(fresh)
    return merged


def _eligible_next_tasks(backlog: dict[str, Any]) -> list[dict[str, Any]]:
    tasks = cast(list[dict[str, Any]], backlog.get("tasks", []))
    completed_task_ids = {
        str(task.get("task_id"))
        for task in tasks
        if isinstance(task, dict) and task.get("status") == "completed" and isinstance(task.get("task_id"), str)
    }
    eligible: list[dict[str, Any]] = []
    for index, task in enumerate(tasks):
        if not isinstance(task, dict):
            continue
        task_id = task.get("task_id")
        if not isinstance(task_id, str) or task.get("status") == "completed":
            continue
        dependencies = task.get("dependencies", [])
        if not isinstance(dependencies, list):
            continue
        if not all(isinstance(dep, str) and dep in completed_task_ids for dep in dependencies):
            continue
        selection_priority = task.get("selection_priority")
        priority_rank = selection_priority if isinstance(selection_priority, (int, float)) else 1000
        eligible.append(
            {
                "task_id": task_id,
                "priority_rank": priority_rank,
                "backlog_index": index,
                "has_explicit_priority": isinstance(selection_priority, (int, float)),
            }
        )
    eligible.sort(key=lambda item: (cast(float, item["priority_rank"]), cast(int, item["backlog_index"])))
    return eligible


def _tokenize_fragments(fragments: list[str]) -> set[str]:
    tokens: set[str] = set()
    for fragment in fragments:
        for token in TOKEN_PATTERN.findall(fragment.lower()):
            if len(token) < 3 or token in SEMANTIC_STOPWORDS:
                continue
            tokens.add(token)
    return tokens


def _selection_context(pack_root: Path) -> dict[str, Any]:
    objective_path = pack_root / "contracts/project-objective.json"
    work_state_path = pack_root / "status/work-state.json"
    fragments: list[str] = []
    source_labels: list[str] = []
    branch_selection_hints: list[dict[str, Any]] = []

    if objective_path.exists():
        objective = _load_object(objective_path)
        for key in ("objective_summary", "problem_statement"):
            value = objective.get(key)
            if isinstance(value, str) and value.strip():
                fragments.append(value)
        for key in ("success_criteria", "completion_definition"):
            values = objective.get(key, [])
            if isinstance(values, list):
                fragments.extend(value for value in values if isinstance(value, str) and value.strip())
        source_labels.append("project_objective")
    if work_state_path.exists():
        work_state = _load_object(work_state_path)
        values = work_state.get("resume_instructions", [])
        if isinstance(values, list):
            fragments.extend(value for value in values if isinstance(value, str) and value.strip())
        source_labels.append("work_state_resume_instructions")
        hints = work_state.get("branch_selection_hints", [])
        if isinstance(hints, list):
            branch_selection_hints = [hint for hint in hints if isinstance(hint, dict)]
            if branch_selection_hints:
                source_labels.append("work_state_branch_selection_hints")

    return {
        "tokens": _tokenize_fragments(fragments),
        "source_labels": source_labels,
        "branch_selection_hints": branch_selection_hints,
    }


def _task_by_id(backlog: dict[str, Any], task_id: str) -> dict[str, Any]:
    for task in cast(list[dict[str, Any]], backlog.get("tasks", [])):
        if isinstance(task, dict) and task.get("task_id") == task_id:
            return task
    raise ValueError(f"task `{task_id}` was not found in tasks/active-backlog.json")


def _task_semantic_score(*, task: dict[str, Any], context_tokens: set[str]) -> dict[str, Any]:
    summary_tokens = _tokenize_fragments([value for value in [task.get("summary")] if isinstance(value, str)])
    acceptance_tokens = _tokenize_fragments(
        [value for value in cast(list[str], task.get("acceptance_criteria", [])) if isinstance(value, str)]
    )
    completion_tokens = _tokenize_fragments(
        [value for value in cast(list[str], task.get("completion_signals", [])) if isinstance(value, str)]
    )
    signal_tokens = _tokenize_fragments(
        [value for value in cast(list[str], task.get("selection_signals", [])) if isinstance(value, str)]
    )

    summary_matches = sorted(summary_tokens & context_tokens)
    acceptance_matches = sorted(acceptance_tokens & context_tokens)
    completion_matches = sorted(completion_tokens & context_tokens)
    signal_matches = sorted(signal_tokens & context_tokens)
    score = (
        2 * len(summary_matches)
        + len(acceptance_matches)
        + len(completion_matches)
        + 3 * len(signal_matches)
    )
    return {
        "task_id": task.get("task_id"),
        "semantic_score": score,
        "matched_terms": sorted(set(summary_matches + acceptance_matches + completion_matches + signal_matches)),
        "matched_signal_terms": signal_matches,
    }


def _hint_preference_decision(*, top_candidates: list[dict[str, Any]], branch_selection_hints: list[dict[str, Any]]) -> dict[str, Any] | None:
    top_candidate_ids = {cast(str, item["task_id"]) for item in top_candidates}
    for hint in branch_selection_hints:
        preferred_task_ids = hint.get("preferred_task_ids", [])
        if not isinstance(preferred_task_ids, list):
            continue
        ranked = [task_id for task_id in preferred_task_ids if isinstance(task_id, str) and task_id in top_candidate_ids]
        if not ranked:
            continue
        return {
            "chosen_task_id": ranked[0],
            "applied_hint_ids": [hint.get("hint_id")],
            "hint_summary": hint.get("summary"),
        }
    return None


def _resolve_next_task_decision(*, pack_root: Path, backlog: dict[str, Any], eligible_tasks: list[dict[str, Any]]) -> dict[str, Any]:
    if not eligible_tasks:
        return {
            "status": "no_candidate",
            "selection_rule": "lowest selection_priority first; then operator branch-selection hints; then bounded semantic alignment; remaining ties require operator disambiguation",
            "candidate_task_ids": [],
            "top_candidate_task_ids": [],
            "chosen_task_id": None,
            "ambiguity_reason": None,
            "selection_method": None,
            "semantic_context_sources": [],
            "semantic_scores": [],
            "applied_hint_ids": [],
            "applied_hint_summary": None,
        }
    top_rank = cast(float, eligible_tasks[0]["priority_rank"])
    top_candidates = [item for item in eligible_tasks if cast(float, item["priority_rank"]) == top_rank]
    if len(top_candidates) > 1:
        context = _selection_context(pack_root)
        hint_decision = _hint_preference_decision(
            top_candidates=top_candidates,
            branch_selection_hints=cast(list[dict[str, Any]], context["branch_selection_hints"]),
        )
        if hint_decision is not None:
            return {
                "status": "selected",
                "selection_rule": "lowest selection_priority first; then operator branch-selection hints; then bounded semantic alignment; remaining ties require operator disambiguation",
                "candidate_task_ids": [cast(str, item["task_id"]) for item in eligible_tasks],
                "top_candidate_task_ids": [cast(str, item["task_id"]) for item in top_candidates],
                "chosen_task_id": cast(str, hint_decision["chosen_task_id"]),
                "ambiguity_reason": None,
                "selection_method": "operator_hint",
                "semantic_context_sources": context["source_labels"],
                "semantic_scores": [],
                "applied_hint_ids": hint_decision["applied_hint_ids"],
                "applied_hint_summary": hint_decision["hint_summary"],
            }
        context_tokens = cast(set[str], context["tokens"])
        semantic_scores = [
            _task_semantic_score(
                task=_task_by_id(backlog, cast(str, item["task_id"])),
                context_tokens=context_tokens,
            )
            for item in top_candidates
        ]
        if semantic_scores:
            best_score = max(cast(int, item["semantic_score"]) for item in semantic_scores)
            best_candidates = [item for item in semantic_scores if cast(int, item["semantic_score"]) == best_score]
            if best_score > 0 and len(best_candidates) == 1:
                return {
                    "status": "selected",
                    "selection_rule": "lowest selection_priority first; then operator branch-selection hints; then bounded semantic alignment; remaining ties require operator disambiguation",
                    "candidate_task_ids": [cast(str, item["task_id"]) for item in eligible_tasks],
                    "top_candidate_task_ids": [cast(str, item["task_id"]) for item in top_candidates],
                    "chosen_task_id": cast(str, best_candidates[0]["task_id"]),
                    "ambiguity_reason": None,
                    "selection_method": "semantic_alignment",
                    "semantic_context_sources": context["source_labels"],
                    "semantic_scores": semantic_scores,
                    "applied_hint_ids": [],
                    "applied_hint_summary": None,
                }
        return {
            "status": "ambiguous",
            "selection_rule": "lowest selection_priority first; then operator branch-selection hints; then bounded semantic alignment; remaining ties require operator disambiguation",
            "candidate_task_ids": [cast(str, item["task_id"]) for item in eligible_tasks],
            "top_candidate_task_ids": [cast(str, item["task_id"]) for item in top_candidates],
            "chosen_task_id": None,
            "ambiguity_reason": "multiple eligible tasks shared the same highest precedence and semantic alignment did not uniquely disambiguate them",
            "selection_method": "ambiguous_after_semantic_alignment",
            "semantic_context_sources": context["source_labels"],
            "semantic_scores": semantic_scores,
            "applied_hint_ids": [],
            "applied_hint_summary": None,
        }
    return {
        "status": "selected",
        "selection_rule": "lowest selection_priority first; then operator branch-selection hints; then bounded semantic alignment; remaining ties require operator disambiguation",
        "candidate_task_ids": [cast(str, item["task_id"]) for item in eligible_tasks],
        "top_candidate_task_ids": [cast(str, item["task_id"]) for item in top_candidates],
        "chosen_task_id": cast(str, eligible_tasks[0]["task_id"]),
        "ambiguity_reason": None,
        "selection_method": "priority_or_single_candidate",
        "semantic_context_sources": [],
        "semantic_scores": [],
        "applied_hint_ids": [],
        "applied_hint_summary": None,
    }


def _record_branch_decision(
    *,
    pack_root: Path,
    run_id: str,
    decision: dict[str, Any],
) -> str | None:
    candidate_task_ids = cast(list[str], decision.get("candidate_task_ids", []))
    if len(candidate_task_ids) <= 1 and decision.get("status") != "ambiguous":
        return None
    payload = {
        "schema_version": "branch-selection-summary/v1",
        "run_id": run_id,
        "recorded_at": isoformat_z(read_now()),
        "status": decision.get("status"),
        "selection_rule": decision.get("selection_rule"),
        "selection_method": decision.get("selection_method"),
        "candidate_task_ids": candidate_task_ids,
        "top_candidate_task_ids": decision.get("top_candidate_task_ids", []),
        "chosen_task_id": decision.get("chosen_task_id"),
        "ambiguity_reason": decision.get("ambiguity_reason"),
        "applied_hint_ids": decision.get("applied_hint_ids", []),
        "applied_hint_summary": decision.get("applied_hint_summary"),
        "semantic_context_sources": decision.get("semantic_context_sources", []),
        "semantic_scores": decision.get("semantic_scores", []),
    }
    branch_selection_file = pack_root / ".pack-state" / "autonomy-runs" / run_id / "branch-selection.json"
    write_json(branch_selection_file, payload)
    return branch_selection_file.relative_to(pack_root).as_posix()


def run_local_mid_backlog_checkpoint(
    *,
    factory_root: Path,
    build_pack_id: str,
    run_id: str,
) -> dict[str, Any]:
    target_pack = discover_pack(factory_root, build_pack_id)
    if target_pack.pack_kind != "build_pack":
        raise ValueError(f"{build_pack_id} is not a build_pack")

    pack_root = target_pack.pack_root
    work_state_path = pack_root / "status/work-state.json"
    backlog_path = pack_root / "tasks/active-backlog.json"
    readiness_path = pack_root / "status/readiness.json"

    work_state = _load_object(work_state_path)
    backlog = _load_object(backlog_path)
    readiness = _load_object(readiness_path)

    active_task_id = work_state.get("active_task_id")
    next_task_id = work_state.get("next_recommended_task_id")
    if not isinstance(active_task_id, str) or not active_task_id:
        raise ValueError("mid-backlog checkpoint requires a non-empty active_task_id")
    if next_task_id != active_task_id:
        raise ValueError("mid-backlog checkpoint requires next_recommended_task_id to equal active_task_id")
    if readiness.get("ready_for_deployment") is True:
        raise ValueError("mid-backlog checkpoint requires a pack that is not already ready_for_deployment")

    active_task = _find_active_task(backlog, active_task_id)
    validation_commands = active_task.get("validation_commands", [])
    if not isinstance(validation_commands, list) or not validation_commands or not all(
        isinstance(command, str) and command.strip() for command in validation_commands
    ):
        raise ValueError(f"active task `{active_task_id}` must declare non-empty validation_commands")

    memory_used, decision_source, selection_notes = _load_matching_memory(pack_root, active_task_id)
    memory_state = "used_and_consistent" if memory_used else "not_used"

    start_run(
        pack_root=pack_root,
        run_id=run_id,
        notes=["Local mid-backlog checkpoint initialized before handing the next task to a future autonomy run."],
        factory_root=factory_root,
    )
    append_event(
        pack_root=pack_root,
        run_id=run_id,
        event_type="task_selected",
        outcome="selected_active_task_for_mid_backlog_checkpoint",
        decision_source=decision_source,
        memory_state=memory_state,
        commands_attempted=[],
        notes=selection_notes,
        evidence_paths=[],
        stop_reason=None,
        active_task_id=active_task_id,
        next_recommended_task_id=active_task_id,
        factory_root=factory_root,
    )

    recorded_results: list[dict[str, Any]] = []
    for command in validation_commands:
        payload = _run_task_command(pack_root, command)
        evidence_paths = list(payload.get("evidence_paths", [])) if isinstance(payload.get("evidence_paths", []), list) else []
        recorded_results.append(
            {
                "validation_id": active_task_id,
                "status": "pass",
                "summary": f"Completed `{active_task_id}` through the declared validation_commands during a local mid-backlog checkpoint.",
                "evidence_paths": evidence_paths,
                "recorded_at": payload.get("generated_at"),
            }
        )
        append_event(
            pack_root=pack_root,
            run_id=run_id,
            event_type="command_completed",
            outcome=f"{active_task_id}_command_completed",
            decision_source=decision_source,
            memory_state=memory_state,
            commands_attempted=[command],
            notes=[f"Completed the declared command for active task `{active_task_id}`."],
            evidence_paths=evidence_paths,
            stop_reason=None,
            active_task_id=active_task_id,
            next_recommended_task_id=active_task_id,
            factory_root=factory_root,
        )

    refreshed_readiness = _load_object(readiness_path)
    refreshed_backlog = _load_object(backlog_path)
    for task in cast(list[dict[str, Any]], refreshed_backlog.get("tasks", [])):
        if not isinstance(task, dict):
            continue
        task_id = task.get("task_id")
        if task_id == active_task_id:
            task["status"] = "completed"

    remaining_task_ids = [
        str(task.get("task_id"))
        for task in cast(list[dict[str, Any]], refreshed_backlog.get("tasks", []))
        if isinstance(task, dict)
        and isinstance(task.get("task_id"), str)
        and task.get("status") != "completed"
    ]
    eligible_next_tasks = _eligible_next_tasks(refreshed_backlog)
    if refreshed_readiness.get("ready_for_deployment") is True or not eligible_next_tasks:
        raise ValueError("mid-backlog checkpoint requires at least one remaining canonical task after the selected task completes")

    branch_decision = _resolve_next_task_decision(
        pack_root=pack_root,
        backlog=refreshed_backlog,
        eligible_tasks=eligible_next_tasks,
    )
    branch_selection_path = _record_branch_decision(
        pack_root=pack_root,
        run_id=run_id,
        decision=branch_decision,
    )
    branch_selection_notes: list[str] = []
    if branch_decision["status"] == "ambiguous":
        ambiguous_task_ids = cast(list[str], branch_decision["top_candidate_task_ids"])
        for task in cast(list[dict[str, Any]], refreshed_backlog.get("tasks", [])):
            if not isinstance(task, dict):
                continue
            if task.get("task_id") != active_task_id and task.get("status") != "completed":
                task["status"] = "pending"
        write_json(backlog_path, refreshed_backlog)

        refreshed_work_state = _load_object(work_state_path)
        last_validation_results = list(refreshed_work_state.get("last_validation_results", []))
        for result in recorded_results:
            if isinstance(result, dict):
                last_validation_results = _merge_validation_results(last_validation_results, result)
        completed_task_ids = list(refreshed_work_state.get("completed_task_ids", []))
        if active_task_id not in completed_task_ids:
            completed_task_ids.append(active_task_id)
        refreshed_work_state.update(
            {
                "autonomy_state": "blocked",
                "active_task_id": None,
                "next_recommended_task_id": None,
                "pending_task_ids": remaining_task_ids,
                "blocked_task_ids": ambiguous_task_ids,
                "completed_task_ids": completed_task_ids,
                "last_outcome": "ambiguity_requires_operator_review",
                "last_outcome_at": isoformat_z(read_now()),
                "last_validation_results": last_validation_results,
                "last_agent_action": (
                    f"Completed `{active_task_id}` locally but stopped because multiple next tasks remained ambiguous: "
                    + ", ".join(f'`{task_id}`' for task_id in ambiguous_task_ids)
                    + "."
                ),
                "escalation_state": "operator_review_required",
            }
        )
        write_json(work_state_path, refreshed_work_state)
        append_event(
            pack_root=pack_root,
            run_id=run_id,
            event_type="escalation_raised",
            outcome="ambiguous_next_task_selection",
            decision_source=decision_source,
            memory_state=memory_state,
            commands_attempted=[],
                notes=[
                cast(str, branch_decision["ambiguity_reason"]),
                f"Operator disambiguation is required before continuing: {', '.join(ambiguous_task_ids)}.",
            ],
            evidence_paths=[] if branch_selection_path is None else [branch_selection_path],
            stop_reason="declared_escalation_boundary",
            active_task_id=None,
            next_recommended_task_id=None,
            factory_root=factory_root,
        )
        summary = finalize_run(
            pack_root=pack_root,
            run_id=run_id,
            schema_factory_root=factory_root,
            validation_factory_root=None,
        )
        pointer_result = refresh_local_feedback_memory_pointer(
            factory_root=factory_root,
            build_pack_id=build_pack_id,
            updated_at=cast(str, summary.get("ended_at")),
        )
        return {
            "status": "blocked",
            "build_pack_id": build_pack_id,
            "run_id": run_id,
            "completed_task_id": active_task_id,
            "next_active_task_id": None,
            "blocked_task_ids": ambiguous_task_ids,
            "run_summary_path": str(pack_root / ".pack-state" / "autonomy-runs" / run_id / "run-summary.json"),
            "feedback_memory_path": str(pack_root / ".pack-state" / "agent-memory" / f"autonomy-feedback-{run_id}.json"),
            "pointer_result": pointer_result,
        }

    next_active_task_id = cast(str, branch_decision["chosen_task_id"])
    if cast(str | None, branch_decision.get("selection_method")) == "operator_hint":
        branch_selection_notes.append(
            f"Multiple next tasks were eligible; selected `{next_active_task_id}` using operator branch-selection hints."
        )
    elif cast(str | None, branch_decision.get("selection_method")) == "semantic_alignment":
        branch_selection_notes.append(
            f"Multiple next tasks were eligible; selected `{next_active_task_id}` using bounded semantic alignment to the objective and resume context."
        )
    elif len(cast(list[str], branch_decision["candidate_task_ids"])) > 1:
        branch_selection_notes.append(
            f"Multiple next tasks were eligible; selected `{next_active_task_id}` using the lowest selection_priority."
        )
    for task in cast(list[dict[str, Any]], refreshed_backlog.get("tasks", [])):
        if not isinstance(task, dict):
            continue
        if task.get("task_id") == next_active_task_id:
            task["status"] = "in_progress"
        elif task.get("task_id") != active_task_id and task.get("status") != "completed":
            task["status"] = "pending"
    write_json(backlog_path, refreshed_backlog)

    refreshed_work_state = _load_object(work_state_path)
    last_validation_results = list(refreshed_work_state.get("last_validation_results", []))
    for result in recorded_results:
        if isinstance(result, dict):
            last_validation_results = _merge_validation_results(last_validation_results, result)
    completed_task_ids = list(refreshed_work_state.get("completed_task_ids", []))
    if active_task_id not in completed_task_ids:
        completed_task_ids.append(active_task_id)
    refreshed_work_state.update(
        {
            "autonomy_state": "actively_building",
            "active_task_id": next_active_task_id,
            "next_recommended_task_id": next_active_task_id,
            "pending_task_ids": [task_id for task_id in remaining_task_ids if task_id != next_active_task_id],
            "blocked_task_ids": [],
            "completed_task_ids": completed_task_ids,
            "last_outcome": "task_completed",
            "last_outcome_at": isoformat_z(read_now()),
            "last_validation_results": last_validation_results,
            "last_agent_action": (
                f"Completed `{active_task_id}` locally and stopped at a mid-backlog checkpoint with `{next_active_task_id}` as the canonical next task."
                if not branch_selection_notes
                else f"Completed `{active_task_id}` locally, evaluated multiple eligible next tasks, and selected `{next_active_task_id}` as the canonical next task."
            ),
            "escalation_state": "none",
        }
    )
    write_json(work_state_path, refreshed_work_state)

    append_event(
        pack_root=pack_root,
        run_id=run_id,
        event_type="state_updated",
        outcome="mid_backlog_checkpoint_created",
        decision_source=decision_source,
        memory_state=memory_state,
        commands_attempted=[],
        notes=[f"Advanced canonical state so `{next_active_task_id}` became the active task for the next autonomy run.", *branch_selection_notes],
        evidence_paths=[] if branch_selection_path is None else [branch_selection_path],
        stop_reason=None,
        active_task_id=next_active_task_id,
        next_recommended_task_id=next_active_task_id,
        factory_root=factory_root,
    )
    append_event(
        pack_root=pack_root,
        run_id=run_id,
        event_type="run_stopped",
        outcome="mid_backlog_checkpoint_created",
        decision_source="canonical_only",
        memory_state="not_used",
        commands_attempted=[],
        notes=["Stopped intentionally after advancing canonical state to the next task so the feedback-memory handoff could be exercised."],
        evidence_paths=[],
        stop_reason="mid_backlog_checkpoint_created",
        active_task_id=next_active_task_id,
        next_recommended_task_id=next_active_task_id,
        factory_root=factory_root,
    )

    summary = finalize_run(
        pack_root=pack_root,
        run_id=run_id,
        schema_factory_root=factory_root,
        validation_factory_root=None,
    )
    pointer_result = refresh_local_feedback_memory_pointer(
        factory_root=factory_root,
        build_pack_id=build_pack_id,
        updated_at=cast(str, summary.get("ended_at")),
    )
    return {
        "status": "completed",
        "build_pack_id": build_pack_id,
        "run_id": run_id,
        "completed_task_id": active_task_id,
        "next_active_task_id": next_active_task_id,
        "run_summary_path": str(pack_root / ".pack-state" / "autonomy-runs" / run_id / "run-summary.json"),
        "feedback_memory_path": str(pack_root / ".pack-state" / "agent-memory" / f"autonomy-feedback-{run_id}.json"),
        "pointer_result": pointer_result,
    }


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a local mid-backlog checkpoint and refresh local feedback memory.")
    parser.add_argument("--factory-root", required=True)
    parser.add_argument("--build-pack-id", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--output", choices=("json",), default="json")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    factory_root = resolve_factory_root(args.factory_root)
    result = run_local_mid_backlog_checkpoint(
        factory_root=factory_root,
        build_pack_id=args.build_pack_id,
        run_id=args.run_id,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
