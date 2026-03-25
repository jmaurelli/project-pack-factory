#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import shlex
import subprocess
import sys
import textwrap
from pathlib import Path
from typing import Any, cast

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from factory_ops import discover_pack, load_json, path_is_relative_to, read_now, resolve_factory_root, schema_path, validate_json_document, write_json
from import_external_runtime_evidence import import_external_runtime_evidence
from prepare_remote_autonomy_target import prepare_remote_autonomy_target
from pull_remote_runtime_evidence import pull_remote_runtime_evidence
from push_build_pack_to_remote import push_build_pack_to_remote
from remote_autonomy_roundtrip_common import (
    canonical_json_text,
    canonical_local_bundle_staging_dir,
    load_remote_autonomy_test_request,
    sha256_path,
    sha256_text,
    sha256_tree,
    write_validated_roundtrip_manifest,
)
from remote_autonomy_staging_common import (
    canonical_remote_export_dir,
    canonical_remote_pack_dir,
    canonical_remote_parent_dir,
    canonical_remote_run_dir,
)
from run_remote_autonomy_loop import run_remote_autonomy_loop


RUN_REQUEST_SCHEMA_NAME = "remote-autonomy-run-request.schema.json"
TEST_REQUEST_SCHEMA_NAME = "remote-autonomy-test-request.schema.json"
RUN_REQUEST_SCHEMA_VERSION = "remote-autonomy-run-request/v1"
TEST_REQUEST_SCHEMA_VERSION = "remote-autonomy-test-request/v1"
RUN_ID_SUFFIX_PATTERN = re.compile(r"^(.+)-active-task-continuity-run-v(\d+)$")


def _load_object(path: Path) -> dict[str, Any]:
    payload = load_json(path)
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: JSON document must contain an object")
    return cast(dict[str, Any], payload)


def _validate_active_task_boundary(pack_root: Path, pack_id: str) -> str:
    work_state = _load_object(pack_root / "status/work-state.json")
    readiness = _load_object(pack_root / "status/readiness.json")
    pointer_path = pack_root / ".pack-state" / "agent-memory" / "latest-memory.json"
    if not pointer_path.exists():
        raise ValueError("active-task continuity requires an active latest-memory pointer")
    pointer_payload = _load_object(pointer_path)
    selected_memory_path = pointer_payload.get("selected_memory_path")
    if not isinstance(selected_memory_path, str) or not selected_memory_path:
        raise ValueError("latest-memory.json is missing selected_memory_path")
    memory_path = (pack_root / selected_memory_path).resolve()
    if not path_is_relative_to(memory_path, pack_root):
        raise ValueError("latest-memory.json selected_memory_path must stay inside the pack root")
    memory_payload = _load_object(memory_path)

    active_task_id = work_state.get("active_task_id")
    next_task_id = work_state.get("next_recommended_task_id")
    if not isinstance(active_task_id, str) or not active_task_id:
        raise ValueError("active-task continuity requires a non-empty active_task_id")
    if next_task_id != active_task_id:
        raise ValueError("active-task continuity requires next_recommended_task_id to equal active_task_id")
    if readiness.get("ready_for_deployment") is True:
        raise ValueError("active-task continuity requires a pack that is not already ready_for_deployment")
    if memory_payload.get("pack_id") != pack_id:
        raise ValueError("latest-memory.json selected memory pack_id does not match the selected build pack")
    if memory_payload.get("active_task_id") != active_task_id or memory_payload.get("next_recommended_task_id") != active_task_id:
        raise ValueError("latest-memory.json selected memory does not match the canonical active task boundary")
    return active_task_id


def _next_run_id(factory_root: Path, remote_target_label: str, pack_id: str) -> str:
    request_root = factory_root / ".pack-state" / "remote-autonomy-requests" / remote_target_label / pack_id
    max_version = 0
    if request_root.exists():
        for child in request_root.iterdir():
            if not child.is_dir():
                continue
            match = RUN_ID_SUFFIX_PATTERN.fullmatch(child.name)
            if match and match.group(1) == pack_id:
                max_version = max(max_version, int(match.group(2)))
    return f"{pack_id}-active-task-continuity-run-v{max_version + 1}"


def _request_root(factory_root: Path, remote_target_label: str, pack_id: str, run_id: str) -> Path:
    return factory_root / ".pack-state" / "remote-autonomy-requests" / remote_target_label / pack_id / run_id


def _build_remote_runner(run_id: str, expected_active_task_id: str) -> str:
    return textwrap.dedent(
        f"""
        python3 - <<'PY'
        from __future__ import annotations

        import json
        import re
        import subprocess
        import sys
        from datetime import datetime, timezone
        from pathlib import Path

        sys.path.insert(0, str((Path(".packfactory-runtime/tools")).resolve()))
        from record_autonomy_run import append_event

        RUN_ID = "{run_id}"
        EXPECTED_ACTIVE_TASK_ID = "{expected_active_task_id}"
        PACK_ROOT = Path(".").resolve()
        MEMORY_DIR = PACK_ROOT / ".pack-state" / "agent-memory"
        LATEST_MEMORY_PATH = MEMORY_DIR / "latest-memory.json"
        TOKEN_PATTERN = re.compile(r"[a-z0-9]+")
        SEMANTIC_STOPWORDS = {{
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
        }}


        def now() -> str:
            return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


        def load_json(path: Path) -> dict[str, object]:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                raise SystemExit(f"{{path}} did not contain a JSON object")
            return payload


        def write_json(path: Path, payload: dict[str, object]) -> None:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\\n", encoding="utf-8")


        def latest_feedback_memory() -> tuple[Path, dict[str, object], str]:
            if LATEST_MEMORY_PATH.exists():
                pointer_doc = load_json(LATEST_MEMORY_PATH)
                selected_memory_path = pointer_doc.get("selected_memory_path")
                if not isinstance(selected_memory_path, str) or not selected_memory_path:
                    raise SystemExit("latest-memory.json is missing selected_memory_path")
                memory_path = (PACK_ROOT / selected_memory_path).resolve()
                if not memory_path.exists():
                    raise SystemExit(f"latest-memory.json pointed at a missing file: {{memory_path}}")
                return memory_path, load_json(memory_path), "latest_pointer"

            candidates = sorted(MEMORY_DIR.glob("autonomy-feedback-*.json"))
            if not candidates:
                raise SystemExit("expected at least one factory-default feedback-memory artifact under .pack-state/agent-memory")
            path = candidates[-1]
            return path, load_json(path), "directory_fallback"


        def run_command(command: str) -> dict[str, object]:
            completed = subprocess.run(
                command,
                shell=True,
                executable="/bin/bash",
                cwd=PACK_ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            if completed.returncode != 0:
                raise SystemExit(completed.stderr.strip() or completed.stdout.strip() or f"command failed: {{command}}")
            stdout = completed.stdout.strip()
            if not stdout:
                return {{"status": "completed", "generated_at": now(), "evidence_paths": []}}
            payload = json.loads(stdout)
            if not isinstance(payload, dict):
                raise SystemExit(f"command output must be a JSON object: {{command}}")
            return payload


        def merge_validation_results(existing: list[dict[str, object]], fresh: dict[str, object]) -> list[dict[str, object]]:
            merged = [result for result in existing if result.get("validation_id") != fresh.get("validation_id")]
            merged.append(fresh)
            return merged


        def eligible_next_tasks(backlog: dict[str, object]) -> list[dict[str, object]]:
            tasks = backlog.get("tasks", [])
            if not isinstance(tasks, list):
                raise SystemExit("tasks/active-backlog.json must contain a tasks array")
            completed_task_ids = set(
                str(task.get("task_id"))
                for task in tasks
                if isinstance(task, dict) and task.get("status") == "completed" and isinstance(task.get("task_id"), str)
            )
            eligible: list[dict[str, object]] = []
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
                    {{
                        "task_id": task_id,
                        "priority_rank": priority_rank,
                        "backlog_index": index,
                        "has_explicit_priority": isinstance(selection_priority, (int, float)),
                    }}
                )
            eligible.sort(key=lambda item: (float(item["priority_rank"]), int(item["backlog_index"])))
            return eligible


        def tokenize_fragments(fragments: list[str]) -> set[str]:
            tokens: set[str] = set()
            for fragment in fragments:
                for token in TOKEN_PATTERN.findall(fragment.lower()):
                    if len(token) < 3 or token in SEMANTIC_STOPWORDS:
                        continue
                    tokens.add(token)
            return tokens


        def selection_context() -> dict[str, object]:
            objective_path = PACK_ROOT / "contracts" / "project-objective.json"
            work_state_path = PACK_ROOT / "status" / "work-state.json"
            fragments: list[str] = []
            source_labels: list[str] = []
            branch_selection_hints: list[dict[str, object]] = []
            if objective_path.exists():
                objective = load_json(objective_path)
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
                work_state = load_json(work_state_path)
                values = work_state.get("resume_instructions", [])
                if isinstance(values, list):
                    fragments.extend(value for value in values if isinstance(value, str) and value.strip())
                source_labels.append("work_state_resume_instructions")
                hints = work_state.get("branch_selection_hints", [])
                if isinstance(hints, list):
                    branch_selection_hints = [hint for hint in hints if isinstance(hint, dict)]
                    if branch_selection_hints:
                        source_labels.append("work_state_branch_selection_hints")
            return {{
                "tokens": tokenize_fragments(fragments),
                "source_labels": source_labels,
                "branch_selection_hints": branch_selection_hints,
            }}


        def task_by_id(backlog: dict[str, object], task_id: str) -> dict[str, object]:
            for task in backlog.get("tasks", []):
                if isinstance(task, dict) and task.get("task_id") == task_id:
                    return task
            raise SystemExit(f"task {{task_id!r}} was not found in tasks/active-backlog.json")


        def task_semantic_score(*, task: dict[str, object], context_tokens: set[str]) -> dict[str, object]:
            summary_tokens = tokenize_fragments([value for value in [task.get("summary")] if isinstance(value, str)])
            acceptance_tokens = tokenize_fragments(
                [value for value in task.get("acceptance_criteria", []) if isinstance(value, str)]
                if isinstance(task.get("acceptance_criteria", []), list) else []
            )
            completion_tokens = tokenize_fragments(
                [value for value in task.get("completion_signals", []) if isinstance(value, str)]
                if isinstance(task.get("completion_signals", []), list) else []
            )
            signal_tokens = tokenize_fragments(
                [value for value in task.get("selection_signals", []) if isinstance(value, str)]
                if isinstance(task.get("selection_signals", []), list) else []
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
            return {{
                "task_id": task.get("task_id"),
                "semantic_score": score,
                "matched_terms": sorted(set(summary_matches + acceptance_matches + completion_matches + signal_matches)),
                "matched_signal_terms": signal_matches,
            }}


        selection_rule = "lowest selection_priority first; then active operator avoid-task hints in canonical list order without eliminating all remaining top candidates; then active operator preferred-task hints in canonical list order; then bounded semantic alignment; remaining ties require operator disambiguation"


        def stable_unique_task_ids(task_ids: list[str]) -> list[str]:
            seen: set[str] = set()
            ordered: list[str] = []
            for task_id in task_ids:
                if task_id in seen:
                    continue
                seen.add(task_id)
                ordered.append(task_id)
            return ordered


        def hint_is_eligible(hint: dict[str, object]) -> bool:
            if hint.get("active") is False:
                return False
            remaining_applications = hint.get("remaining_applications")
            return not (isinstance(remaining_applications, int) and remaining_applications <= 0)


        def apply_hint_lifecycle_updates(*, work_state: dict[str, object], applied_hint_ids: list[str]) -> dict[str, object]:
            target_hint_ids = set(stable_unique_task_ids([hint_id for hint_id in applied_hint_ids if isinstance(hint_id, str)]))
            if not target_hint_ids:
                return {{
                    "consumed_hint_ids": [],
                    "deactivated_hint_ids": [],
                }}
            hints = work_state.get("branch_selection_hints", [])
            if not isinstance(hints, list):
                return {{
                    "consumed_hint_ids": [],
                    "deactivated_hint_ids": [],
                }}

            consumed_hint_ids: list[str] = []
            deactivated_hint_ids: list[str] = []
            for hint in hints:
                if not isinstance(hint, dict):
                    continue
                hint_id = hint.get("hint_id")
                if not isinstance(hint_id, str) or hint_id not in target_hint_ids:
                    continue
                remaining_applications = hint.get("remaining_applications")
                if not isinstance(remaining_applications, int):
                    continue
                updated_remaining = max(0, remaining_applications - 1)
                hint["remaining_applications"] = updated_remaining
                consumed_hint_ids.append(hint_id)
                if updated_remaining == 0:
                    hint["active"] = False
                    deactivated_hint_ids.append(hint_id)
            return {{
                "consumed_hint_ids": stable_unique_task_ids(consumed_hint_ids),
                "deactivated_hint_ids": stable_unique_task_ids(deactivated_hint_ids),
            }}


        def hint_preference_decision(*, top_candidates: list[dict[str, object]], branch_selection_hints: list[dict[str, object]]) -> dict[str, object] | None:
            remaining_candidates = list(top_candidates)
            applied_hint_ids: list[str] = []
            applied_hint_summaries: list[str] = []
            filtered_out_task_ids: list[str] = []
            ignored_hint_ids: list[str] = []
            ignored_hint_summaries: list[str] = []

            for hint in branch_selection_hints:
                if not hint_is_eligible(hint):
                    continue
                current_candidate_ids = {{str(item["task_id"]) for item in remaining_candidates}}
                if not current_candidate_ids:
                    break
                hint_id = hint.get("hint_id")
                summary = hint.get("summary")
                avoid_task_ids = hint.get("avoid_task_ids", [])
                if isinstance(avoid_task_ids, list):
                    removed = [
                        task_id
                        for task_id in avoid_task_ids
                        if isinstance(task_id, str) and task_id in current_candidate_ids
                    ]
                    narrowed_candidates = [
                        item for item in remaining_candidates if str(item["task_id"]) not in removed
                    ]
                    if removed and narrowed_candidates:
                        remaining_candidates = narrowed_candidates
                        filtered_out_task_ids.extend(removed)
                        if isinstance(hint_id, str):
                            applied_hint_ids.append(hint_id)
                        if isinstance(summary, str) and summary:
                            applied_hint_summaries.append(summary)
                    elif removed:
                        if isinstance(hint_id, str):
                            ignored_hint_ids.append(hint_id)
                        if isinstance(summary, str) and summary:
                            ignored_hint_summaries.append(summary)

            if len(remaining_candidates) == 1:
                return {{
                    "chosen_task_id": str(remaining_candidates[0]["task_id"]),
                    "applied_hint_ids": applied_hint_ids,
                    "hint_summary": " | ".join(applied_hint_summaries) if applied_hint_summaries else None,
                    "filtered_out_task_ids": sorted(set(filtered_out_task_ids)),
                    "post_hint_candidate_task_ids": [str(item["task_id"]) for item in remaining_candidates],
                    "ignored_hint_ids": ignored_hint_ids,
                    "ignored_hint_summary": " | ".join(ignored_hint_summaries) if ignored_hint_summaries else None,
                }}

            for hint in branch_selection_hints:
                if not hint_is_eligible(hint):
                    continue
                current_candidate_ids = {{str(item["task_id"]) for item in remaining_candidates}}
                if not current_candidate_ids:
                    break
                hint_id = hint.get("hint_id")
                summary = hint.get("summary")
                preferred_task_ids = hint.get("preferred_task_ids", [])
                if not isinstance(preferred_task_ids, list):
                    continue
                ranked = [task_id for task_id in preferred_task_ids if isinstance(task_id, str) and task_id in current_candidate_ids]
                if not ranked:
                    continue
                if isinstance(hint_id, str):
                    applied_hint_ids.append(hint_id)
                if isinstance(summary, str) and summary:
                    applied_hint_summaries.append(summary)
                return {{
                    "chosen_task_id": ranked[0],
                    "applied_hint_ids": applied_hint_ids,
                    "hint_summary": " | ".join(applied_hint_summaries) if applied_hint_summaries else None,
                    "filtered_out_task_ids": sorted(set(filtered_out_task_ids)),
                    "post_hint_candidate_task_ids": [str(item["task_id"]) for item in remaining_candidates],
                    "ignored_hint_ids": ignored_hint_ids,
                    "ignored_hint_summary": " | ".join(ignored_hint_summaries) if ignored_hint_summaries else None,
                }}
            if applied_hint_ids or ignored_hint_ids:
                return {{
                    "chosen_task_id": None,
                    "applied_hint_ids": applied_hint_ids,
                    "hint_summary": " | ".join(applied_hint_summaries) if applied_hint_summaries else None,
                    "filtered_out_task_ids": sorted(set(filtered_out_task_ids)),
                    "post_hint_candidate_task_ids": [str(item["task_id"]) for item in remaining_candidates],
                    "ignored_hint_ids": ignored_hint_ids,
                    "ignored_hint_summary": " | ".join(ignored_hint_summaries) if ignored_hint_summaries else None,
                }}
            return None


        def resolve_next_task_decision(eligible: list[dict[str, object]]) -> dict[str, object]:
            if not eligible:
                return {{
                    "status": "no_candidate",
                    "selection_rule": selection_rule,
                    "candidate_task_ids": [],
                    "top_candidate_task_ids": [],
                    "post_hint_candidate_task_ids": [],
                    "filtered_out_task_ids": [],
                    "chosen_task_id": None,
                    "ambiguity_reason": None,
                    "selection_method": None,
                    "semantic_context_sources": [],
                    "semantic_scores": [],
                    "applied_hint_ids": [],
                    "applied_hint_summary": None,
                    "ignored_hint_ids": [],
                    "ignored_hint_summary": None,
                    "consumed_hint_ids": [],
                    "deactivated_hint_ids": [],
                }}
            top_rank = float(eligible[0]["priority_rank"])
            top_candidates = [item for item in eligible if float(item["priority_rank"]) == top_rank]
            if len(top_candidates) > 1:
                context = selection_context()
                hint_decision = hint_preference_decision(
                    top_candidates=top_candidates,
                    branch_selection_hints=context["branch_selection_hints"],
                )
                narrowed_candidates = top_candidates
                applied_hint_ids: list[str] = []
                applied_hint_summary = None
                filtered_out_task_ids: list[str] = []
                ignored_hint_ids: list[str] = []
                ignored_hint_summary = None
                if hint_decision is not None:
                    applied_hint_ids = list(hint_decision.get("applied_hint_ids", []))
                    applied_hint_summary = hint_decision.get("hint_summary")
                    filtered_out_task_ids = list(hint_decision.get("filtered_out_task_ids", []))
                    ignored_hint_ids = list(hint_decision.get("ignored_hint_ids", []))
                    ignored_hint_summary = hint_decision.get("ignored_hint_summary")
                    post_hint_candidate_task_ids = list(hint_decision.get("post_hint_candidate_task_ids", []))
                    if post_hint_candidate_task_ids:
                        narrowed_candidates = [item for item in top_candidates if str(item["task_id"]) in set(post_hint_candidate_task_ids)]
                    if hint_decision.get("chosen_task_id") is not None:
                        chosen_task_id = str(hint_decision["chosen_task_id"])
                        selection_method = "operator_hint"
                        return {{
                            "status": "selected",
                            "selection_rule": selection_rule,
                            "candidate_task_ids": [str(item["task_id"]) for item in eligible],
                            "top_candidate_task_ids": [str(item["task_id"]) for item in top_candidates],
                            "post_hint_candidate_task_ids": post_hint_candidate_task_ids,
                            "filtered_out_task_ids": filtered_out_task_ids,
                            "chosen_task_id": chosen_task_id,
                            "ambiguity_reason": None,
                            "selection_method": selection_method,
                            "semantic_context_sources": context["source_labels"],
                            "semantic_scores": [],
                            "applied_hint_ids": applied_hint_ids,
                            "applied_hint_summary": applied_hint_summary,
                            "ignored_hint_ids": ignored_hint_ids,
                            "ignored_hint_summary": ignored_hint_summary,
                            "consumed_hint_ids": [],
                            "deactivated_hint_ids": [],
                        }}
                semantic_scores = [
                    task_semantic_score(
                        task=task_by_id(refreshed_backlog, str(item["task_id"])),
                        context_tokens=context["tokens"],
                    )
                    for item in narrowed_candidates
                ]
                if semantic_scores:
                    best_score = max(int(item["semantic_score"]) for item in semantic_scores)
                    best_candidates = [item for item in semantic_scores if int(item["semantic_score"]) == best_score]
                    if best_score > 0 and len(best_candidates) == 1:
                        return {{
                            "status": "selected",
                            "selection_rule": selection_rule,
                            "candidate_task_ids": [str(item["task_id"]) for item in eligible],
                            "top_candidate_task_ids": [str(item["task_id"]) for item in top_candidates],
                            "post_hint_candidate_task_ids": [str(item["task_id"]) for item in narrowed_candidates],
                            "filtered_out_task_ids": filtered_out_task_ids,
                            "chosen_task_id": str(best_candidates[0]["task_id"]),
                            "ambiguity_reason": None,
                            "selection_method": "operator_hint_plus_semantic_alignment" if applied_hint_ids else "semantic_alignment",
                            "semantic_context_sources": context["source_labels"],
                            "semantic_scores": semantic_scores,
                            "applied_hint_ids": applied_hint_ids,
                            "applied_hint_summary": applied_hint_summary,
                            "ignored_hint_ids": ignored_hint_ids,
                            "ignored_hint_summary": ignored_hint_summary,
                            "consumed_hint_ids": [],
                            "deactivated_hint_ids": [],
                        }}
                return {{
                    "status": "ambiguous",
                    "selection_rule": selection_rule,
                    "candidate_task_ids": [str(item["task_id"]) for item in eligible],
                    "top_candidate_task_ids": [str(item["task_id"]) for item in top_candidates],
                    "post_hint_candidate_task_ids": [str(item["task_id"]) for item in narrowed_candidates],
                    "filtered_out_task_ids": filtered_out_task_ids,
                    "chosen_task_id": None,
                    "ambiguity_reason": "multiple eligible tasks shared the same highest precedence and operator guidance plus semantic alignment did not uniquely disambiguate them" if applied_hint_ids else "multiple eligible tasks shared the same highest precedence and semantic alignment did not uniquely disambiguate them",
                    "selection_method": "ambiguous_after_operator_hint_and_semantic_alignment" if applied_hint_ids else "ambiguous_after_semantic_alignment",
                    "semantic_context_sources": context["source_labels"],
                    "semantic_scores": semantic_scores,
                    "applied_hint_ids": applied_hint_ids,
                    "applied_hint_summary": applied_hint_summary,
                    "ignored_hint_ids": ignored_hint_ids,
                    "ignored_hint_summary": ignored_hint_summary,
                    "consumed_hint_ids": [],
                    "deactivated_hint_ids": [],
                }}
            return {{
                "status": "selected",
                "selection_rule": selection_rule,
                "candidate_task_ids": [str(item["task_id"]) for item in eligible],
                "top_candidate_task_ids": [str(item["task_id"]) for item in top_candidates],
                "post_hint_candidate_task_ids": [str(item["task_id"]) for item in top_candidates],
                "filtered_out_task_ids": [],
                "chosen_task_id": str(eligible[0]["task_id"]),
                "ambiguity_reason": None,
                "selection_method": "priority_or_single_candidate",
                "semantic_context_sources": [],
                "semantic_scores": [],
                "applied_hint_ids": [],
                "applied_hint_summary": None,
                "ignored_hint_ids": [],
                "ignored_hint_summary": None,
                "consumed_hint_ids": [],
                "deactivated_hint_ids": [],
            }}


        memory_path, memory_doc, memory_source = latest_feedback_memory()
        work_state_path = PACK_ROOT / "status" / "work-state.json"
        backlog_path = PACK_ROOT / "tasks" / "active-backlog.json"
        readiness_path = PACK_ROOT / "status" / "readiness.json"
        work_state = load_json(work_state_path)
        backlog = load_json(backlog_path)
        readiness = load_json(readiness_path)
        active_task_id = work_state.get("active_task_id")
        next_task_id = work_state.get("next_recommended_task_id")
        if active_task_id != EXPECTED_ACTIVE_TASK_ID or next_task_id != EXPECTED_ACTIVE_TASK_ID:
            raise SystemExit(f"unexpected canonical active-task boundary: active={{active_task_id!r}} next={{next_task_id!r}} expected={{EXPECTED_ACTIVE_TASK_ID!r}}")
        if bool(readiness.get("ready_for_deployment")):
            raise SystemExit("expected readiness.ready_for_deployment to be false")
        if memory_doc.get("active_task_id") != EXPECTED_ACTIVE_TASK_ID or memory_doc.get("next_recommended_task_id") != EXPECTED_ACTIVE_TASK_ID:
            raise SystemExit("feedback memory did not match the canonical active task boundary")

        selected_task = None
        for task in backlog.get("tasks", []):
            if isinstance(task, dict) and task.get("task_id") == EXPECTED_ACTIVE_TASK_ID:
                selected_task = task
                break
        if not isinstance(selected_task, dict):
            raise SystemExit(f"active task {{EXPECTED_ACTIVE_TASK_ID!r}} was not found in tasks/active-backlog.json")
        commands = selected_task.get("validation_commands", [])
        if not isinstance(commands, list) or not commands or not all(isinstance(command, str) and command.strip() for command in commands):
            raise SystemExit(f"active task {{EXPECTED_ACTIVE_TASK_ID!r}} must declare non-empty validation_commands")

        memory_ingress_path = PACK_ROOT / ".pack-state" / "autonomy-runs" / RUN_ID / "memory-ingress.json"
        write_json(
            memory_ingress_path,
            {{
                "memory_path": memory_path.as_posix(),
                "memory_run_id": memory_doc.get("run_id"),
                "memory_generated_at": memory_doc.get("generated_at"),
                "memory_source": memory_source,
                "active_task_id": active_task_id,
                "next_recommended_task_id": next_task_id,
                "recorded_at": now(),
            }},
        )

        append_event(
            pack_root=PACK_ROOT,
            run_id=RUN_ID,
            event_type="task_selected",
            outcome="selected_active_task_from_feedback_memory",
            decision_source="canonical_plus_memory",
            memory_state="used_and_consistent",
            commands_attempted=[],
            notes=[
                f"Loaded factory-default feedback memory from {{memory_path.as_posix()}} via {{memory_source}}.",
                f"Memory agreed with canonical state on active task {{EXPECTED_ACTIVE_TASK_ID}}.",
            ],
            evidence_paths=[memory_ingress_path.relative_to(PACK_ROOT).as_posix()],
            stop_reason=None,
            active_task_id=EXPECTED_ACTIVE_TASK_ID,
            next_recommended_task_id=EXPECTED_ACTIVE_TASK_ID,
        )

        recorded_results: list[dict[str, object]] = []
        for command in commands:
            payload = run_command(command)
            evidence_paths = list(payload.get("evidence_paths", [])) if isinstance(payload.get("evidence_paths", []), list) else []
            recorded_results.append(
                {{
                    "validation_id": EXPECTED_ACTIVE_TASK_ID,
                    "status": "pass",
                    "summary": f"Completed `{{EXPECTED_ACTIVE_TASK_ID}}` through the declared validation_commands during remote active-task continuity.",
                    "evidence_paths": evidence_paths,
                    "recorded_at": payload.get("generated_at"),
                }}
            )
            append_event(
                pack_root=PACK_ROOT,
                run_id=RUN_ID,
                event_type="command_completed",
                outcome=f"{{EXPECTED_ACTIVE_TASK_ID}}_command_completed",
                decision_source="canonical_plus_memory",
                memory_state="used_and_consistent",
                commands_attempted=[command],
                notes=[f"Completed the declared command for active task `{{EXPECTED_ACTIVE_TASK_ID}}`."],
                evidence_paths=evidence_paths,
                stop_reason=None,
                active_task_id=EXPECTED_ACTIVE_TASK_ID,
                next_recommended_task_id=EXPECTED_ACTIVE_TASK_ID,
            )

        refreshed_readiness = load_json(readiness_path)
        refreshed_backlog = load_json(backlog_path)
        for task in refreshed_backlog.get("tasks", []):
            if isinstance(task, dict) and task.get("task_id") == EXPECTED_ACTIVE_TASK_ID:
                task["status"] = "completed"

        remaining_task_ids = [
            str(task.get("task_id"))
            for task in refreshed_backlog.get("tasks", [])
            if isinstance(task, dict)
            and isinstance(task.get("task_id"), str)
            and task.get("status") != "completed"
        ]
        eligible_tasks = eligible_next_tasks(refreshed_backlog)
        next_active_task_id = None
        branch_selection_path = None
        branch_selection_notes = []
        if not bool(refreshed_readiness.get("ready_for_deployment")) and eligible_tasks:
            branch_decision = resolve_next_task_decision(eligible_tasks)
            if len(branch_decision["candidate_task_ids"]) > 1 or branch_decision["status"] == "ambiguous":
                branch_selection_payload = {{
                    "schema_version": "branch-selection-summary/v1",
                    "run_id": RUN_ID,
                    "recorded_at": now(),
                    "status": branch_decision["status"],
                    "selection_rule": branch_decision["selection_rule"],
                    "selection_method": branch_decision["selection_method"],
                    "candidate_task_ids": branch_decision["candidate_task_ids"],
                    "top_candidate_task_ids": branch_decision["top_candidate_task_ids"],
                    "post_hint_candidate_task_ids": branch_decision["post_hint_candidate_task_ids"],
                    "filtered_out_task_ids": branch_decision["filtered_out_task_ids"],
                    "chosen_task_id": branch_decision["chosen_task_id"],
                    "ambiguity_reason": branch_decision["ambiguity_reason"],
                    "applied_hint_ids": branch_decision["applied_hint_ids"],
                    "applied_hint_summary": branch_decision["applied_hint_summary"],
                    "ignored_hint_ids": branch_decision["ignored_hint_ids"],
                    "ignored_hint_summary": branch_decision["ignored_hint_summary"],
                    "consumed_hint_ids": branch_decision["consumed_hint_ids"],
                    "deactivated_hint_ids": branch_decision["deactivated_hint_ids"],
                    "semantic_context_sources": branch_decision["semantic_context_sources"],
                    "semantic_scores": branch_decision["semantic_scores"],
                }}
                branch_selection_file = PACK_ROOT / ".pack-state" / "autonomy-runs" / RUN_ID / "branch-selection.json"
                write_json(branch_selection_file, branch_selection_payload)
                branch_selection_path = branch_selection_file.relative_to(PACK_ROOT).as_posix()
            if branch_decision["status"] == "ambiguous":
                ambiguous_task_ids = [str(task_id) for task_id in branch_decision["top_candidate_task_ids"]]
                for task in refreshed_backlog.get("tasks", []):
                    if not isinstance(task, dict):
                        continue
                    if task.get("status") != "completed":
                        task["status"] = "pending"
                write_json(backlog_path, refreshed_backlog)

                refreshed_work_state = load_json(work_state_path)
                last_validation_results = list(refreshed_work_state.get("last_validation_results", []))
                for result in recorded_results:
                    if isinstance(result, dict):
                        last_validation_results = merge_validation_results(last_validation_results, result)
                completed_task_ids = list(refreshed_work_state.get("completed_task_ids", []))
                if EXPECTED_ACTIVE_TASK_ID not in completed_task_ids:
                    completed_task_ids.append(EXPECTED_ACTIVE_TASK_ID)
                refreshed_work_state.update(
                    {{
                        "autonomy_state": "blocked",
                        "active_task_id": None,
                        "next_recommended_task_id": None,
                        "pending_task_ids": remaining_task_ids,
                        "blocked_task_ids": ambiguous_task_ids,
                        "completed_task_ids": completed_task_ids,
                        "last_outcome": "ambiguity_requires_operator_review",
                        "last_outcome_at": now(),
                        "last_validation_results": last_validation_results,
                        "last_agent_action": (
                            f"Completed `{{EXPECTED_ACTIVE_TASK_ID}}` through remote active-task continuity but stopped because multiple next tasks remained ambiguous: "
                            + ", ".join(f"`{{task_id}}`" for task_id in ambiguous_task_ids)
                            + "."
                        ),
                        "escalation_state": "operator_review_required",
                    }}
                )
                write_json(work_state_path, refreshed_work_state)

                append_event(
                    pack_root=PACK_ROOT,
                    run_id=RUN_ID,
                    event_type="escalation_raised",
                    outcome="ambiguous_next_task_selection",
                    decision_source="canonical_plus_memory",
                    memory_state="used_and_consistent",
                    commands_attempted=[],
                    notes=[
                        str(branch_decision["ambiguity_reason"]),
                        f"Operator disambiguation is required before continuing: {{', '.join(ambiguous_task_ids)}}.",
                    ],
                    evidence_paths=[] if branch_selection_path is None else [branch_selection_path],
                    stop_reason="declared_escalation_boundary",
                    active_task_id=None,
                    next_recommended_task_id=None,
                )
                print(
                    json.dumps(
                        {{
                            "status": "blocked",
                            "completed_task_id": EXPECTED_ACTIVE_TASK_ID,
                            "blocked_task_ids": ambiguous_task_ids,
                            "ready_for_deployment": bool(refreshed_readiness.get("ready_for_deployment")),
                        }},
                        sort_keys=True,
                    )
                )
                raise SystemExit(0)

            next_active_task_id = str(branch_decision["chosen_task_id"])
            if str(branch_decision.get("selection_method")) == "operator_hint":
                branch_selection_notes.append(
                    f"Multiple next tasks were eligible; selected `{{next_active_task_id}}` using operator branch-selection hints."
                )
            elif str(branch_decision.get("selection_method")) == "operator_hint_plus_semantic_alignment":
                branch_selection_notes.append(
                    f"Multiple next tasks were eligible; operator branch-selection hints narrowed the candidates, then bounded semantic alignment selected `{{next_active_task_id}}`."
                )
            elif str(branch_decision.get("selection_method")) == "semantic_alignment":
                branch_selection_notes.append(
                    f"Multiple next tasks were eligible; selected `{{next_active_task_id}}` using bounded semantic alignment to the objective and resume context."
                )
            elif len(branch_decision["candidate_task_ids"]) > 1:
                branch_selection_notes.append(
                    f"Multiple next tasks were eligible; selected `{{next_active_task_id}}` using the lowest selection_priority."
                )
        for task in refreshed_backlog.get("tasks", []):
            if not isinstance(task, dict):
                continue
            task_id = task.get("task_id")
            if next_active_task_id is not None and task_id == next_active_task_id:
                task["status"] = "in_progress"
            elif task_id != EXPECTED_ACTIVE_TASK_ID and task.get("status") != "completed":
                task["status"] = "pending"
        write_json(backlog_path, refreshed_backlog)

        refreshed_work_state = load_json(work_state_path)
        last_validation_results = list(refreshed_work_state.get("last_validation_results", []))
        for result in recorded_results:
            if isinstance(result, dict):
                last_validation_results = merge_validation_results(last_validation_results, result)
        completed_task_ids = list(refreshed_work_state.get("completed_task_ids", []))
        if EXPECTED_ACTIVE_TASK_ID not in completed_task_ids:
            completed_task_ids.append(EXPECTED_ACTIVE_TASK_ID)
        if next_active_task_id is not None:
            hint_lifecycle_result = apply_hint_lifecycle_updates(
                work_state=refreshed_work_state,
                applied_hint_ids=list(branch_decision.get("applied_hint_ids", [])),
            )
            branch_decision["consumed_hint_ids"] = hint_lifecycle_result["consumed_hint_ids"]
            branch_decision["deactivated_hint_ids"] = hint_lifecycle_result["deactivated_hint_ids"]
            if len(branch_decision["candidate_task_ids"]) > 1 or branch_decision["status"] == "ambiguous":
                branch_selection_payload = {{
                    "schema_version": "branch-selection-summary/v1",
                    "run_id": RUN_ID,
                    "recorded_at": now(),
                    "status": branch_decision["status"],
                    "selection_rule": branch_decision["selection_rule"],
                    "selection_method": branch_decision["selection_method"],
                    "candidate_task_ids": branch_decision["candidate_task_ids"],
                    "top_candidate_task_ids": branch_decision["top_candidate_task_ids"],
                    "post_hint_candidate_task_ids": branch_decision["post_hint_candidate_task_ids"],
                    "filtered_out_task_ids": branch_decision["filtered_out_task_ids"],
                    "chosen_task_id": branch_decision["chosen_task_id"],
                    "ambiguity_reason": branch_decision["ambiguity_reason"],
                    "applied_hint_ids": branch_decision["applied_hint_ids"],
                    "applied_hint_summary": branch_decision["applied_hint_summary"],
                    "ignored_hint_ids": branch_decision["ignored_hint_ids"],
                    "ignored_hint_summary": branch_decision["ignored_hint_summary"],
                    "consumed_hint_ids": branch_decision["consumed_hint_ids"],
                    "deactivated_hint_ids": branch_decision["deactivated_hint_ids"],
                    "semantic_context_sources": branch_decision["semantic_context_sources"],
                    "semantic_scores": branch_decision["semantic_scores"],
                }}
                branch_selection_file = PACK_ROOT / ".pack-state" / "autonomy-runs" / RUN_ID / "branch-selection.json"
                write_json(branch_selection_file, branch_selection_payload)
                branch_selection_path = branch_selection_file.relative_to(PACK_ROOT).as_posix()
            consumed_hint_ids = list(branch_decision.get("consumed_hint_ids", []))
            if consumed_hint_ids:
                branch_selection_notes.append(
                    "Consumed bounded operator hints during branch selection: "
                    + ", ".join(f"`{{hint_id}}`" for hint_id in consumed_hint_ids)
                    + "."
                )
            deactivated_hint_ids = list(branch_decision.get("deactivated_hint_ids", []))
            if deactivated_hint_ids:
                branch_selection_notes.append(
                    "Deactivated exhausted operator hints after branch selection: "
                    + ", ".join(f"`{{hint_id}}`" for hint_id in deactivated_hint_ids)
                    + "."
                )
        autonomy_state = "ready_for_deploy" if bool(refreshed_readiness.get("ready_for_deployment")) else "actively_building"
        refreshed_work_state.update(
            {{
                "autonomy_state": autonomy_state,
                "active_task_id": next_active_task_id,
                "next_recommended_task_id": next_active_task_id,
                "pending_task_ids": [] if next_active_task_id is None else [task_id for task_id in remaining_task_ids if task_id != next_active_task_id],
                "blocked_task_ids": [],
                "completed_task_ids": completed_task_ids,
                "last_outcome": "task_completed",
                "last_outcome_at": now(),
                "last_validation_results": last_validation_results,
                "last_agent_action": (
                    f"Completed `{{EXPECTED_ACTIVE_TASK_ID}}` through remote active-task continuity and advanced canonical state."
                    if not branch_selection_notes
                    else f"Completed `{{EXPECTED_ACTIVE_TASK_ID}}`, evaluated multiple eligible next tasks, and advanced canonical state with `{{next_active_task_id}}` selected."
                ),
                "escalation_state": "none",
            }}
        )
        write_json(work_state_path, refreshed_work_state)

        append_event(
            pack_root=PACK_ROOT,
            run_id=RUN_ID,
            event_type="state_updated",
            outcome="active_task_continuity_completed",
            decision_source="canonical_plus_memory",
            memory_state="used_and_consistent",
            commands_attempted=[],
            notes=[
                f"Completed active task `{{EXPECTED_ACTIVE_TASK_ID}}` and advanced canonical state to next task {{next_active_task_id!r}}.",
                f"ready_for_deployment={{bool(refreshed_readiness.get('ready_for_deployment'))}}.",
                *branch_selection_notes,
            ],
            evidence_paths=[] if branch_selection_path is None else [branch_selection_path],
            stop_reason=None,
            active_task_id=next_active_task_id,
            next_recommended_task_id=next_active_task_id,
        )

        print(
            json.dumps(
                {{
                    "status": "completed",
                    "completed_task_id": EXPECTED_ACTIVE_TASK_ID,
                    "next_active_task_id": next_active_task_id,
                    "ready_for_deployment": bool(refreshed_readiness.get("ready_for_deployment")),
                }},
                sort_keys=True,
            )
        )
        PY
        """
    ).strip()


def _write_validated(factory_root: Path, path: Path, payload: dict[str, Any], schema_name: str) -> None:
    write_json(path, payload)
    errors = validate_json_document(path, schema_path(factory_root, schema_name))
    if errors:
        raise ValueError("; ".join(errors))


def _expand_remote_home(path: str, remote_user: str) -> str:
    if path == "~":
        return f"/home/{remote_user}"
    if path.startswith("~/"):
        return f"/home/{remote_user}/{path[2:]}"
    return path


def _seed_required_validation_artifacts(*, remote_request) -> list[str]:
    source_pack_root = remote_request.source_build_pack_root
    readiness = _load_object(source_pack_root / "status/readiness.json")
    required_paths: list[Path] = []
    for gate in cast(list[dict[str, Any]], readiness.get("required_gates", [])):
        if not isinstance(gate, dict) or gate.get("gate_id") != "validate_build_pack_contract":
            continue
        for evidence_path in gate.get("evidence_paths", []):
            if not isinstance(evidence_path, str) or not evidence_path:
                continue
            local_path = (source_pack_root / evidence_path).resolve()
            if local_path.exists() and path_is_relative_to(local_path, source_pack_root):
                required_paths.append(local_path)
        break

    seeded: list[str] = []
    for local_path in required_paths:
        relative = local_path.relative_to(source_pack_root).as_posix()
        remote_path = _expand_remote_home(f"{remote_request.remote_pack_dir}/{relative}", remote_request.remote_user)
        remote_dir = str(Path(remote_path).parent).replace("\\", "/")
        mkdir_command = f"mkdir -p {shlex.quote(remote_dir)}"
        completed = subprocess.run(
            ["ssh", remote_request.remote_address, f"bash -lc {shlex.quote(mkdir_command)}"],
            text=True,
            capture_output=True,
            check=False,
        )
        if completed.returncode != 0:
            raise RuntimeError(completed.stderr.strip() or completed.stdout.strip() or f"failed to mkdir {remote_dir}")
        copied = subprocess.run(
            ["scp", str(local_path), f"{remote_request.remote_address}:{remote_path}"],
            text=True,
            capture_output=True,
            check=False,
        )
        if copied.returncode != 0:
            raise RuntimeError(copied.stderr.strip() or copied.stdout.strip() or f"failed to copy {relative}")
        seeded.append(relative)
    return seeded


def _run_roundtrip_with_seeded_validation_artifacts(*, factory_root: Path, test_request_path: Path) -> dict[str, Any]:
    wrapper_request = load_remote_autonomy_test_request(factory_root=factory_root, request_path=test_request_path)
    remote_request = wrapper_request.remote_run_request
    if wrapper_request.import_bundle and not wrapper_request.pull_bundle:
        raise ValueError("active-task continuity requires pull_bundle=true when import_bundle=true")
    if wrapper_request.local_bundle_staging_dir.exists() and any(wrapper_request.local_bundle_staging_dir.iterdir()):
        raise ValueError(
            f"local_bundle_staging_dir must be empty before the roundtrip run: {wrapper_request.local_bundle_staging_dir}"
        )

    wrapper_request_sha256 = sha256_text(canonical_json_text(wrapper_request.raw_payload))
    remote_run_request_sha256 = sha256_text(canonical_json_text(remote_request.raw_payload))

    preparation_result = prepare_remote_autonomy_target(factory_root, wrapper_request.remote_run_request_path)
    staging_result = push_build_pack_to_remote(factory_root, wrapper_request.remote_run_request_path, transport="auto")
    seeded_prerequisite_paths = _seed_required_validation_artifacts(remote_request=remote_request)
    execution_result = run_remote_autonomy_loop(factory_root, wrapper_request.remote_run_request_path)

    pull_result = pull_remote_runtime_evidence(
        factory_root,
        wrapper_request.remote_run_request_path,
        local_bundle_staging_dir=wrapper_request.local_bundle_staging_dir,
        transport="auto",
    )
    if pull_result["source_build_pack_id"] != remote_request.source_build_pack_id:
        raise ValueError("pull result source_build_pack_id does not match the selected remote run request")
    if pull_result["run_id"] != remote_request.run_id:
        raise ValueError("pull result run_id does not match the selected remote run request")
    if pull_result["remote_target_label"] != remote_request.remote_target_label:
        raise ValueError("pull result remote_target_label does not match the selected remote run request")
    if pull_result["target_manifest_sha256"] != execution_result["target_manifest_sha256"]:
        raise ValueError("pull result target_manifest_sha256 does not match the execution result")

    pulled_bundle_path = Path(str(pull_result["local_bundle_root"]))
    pulled_bundle_sha256 = str(pull_result["pulled_bundle_sha256"])
    if pulled_bundle_sha256 != sha256_tree(pulled_bundle_path):
        raise ValueError("pulled bundle sha256 does not match the staged local bundle directory")

    import_request_path: Path | None = None
    import_result: dict[str, Any] | None = None
    if wrapper_request.import_bundle:
        import_request_path = wrapper_request.local_bundle_staging_dir / "generated-import-request.json"
        import_request_payload = {
            "schema_version": "external-runtime-evidence-import-request/v1",
            "build_pack_id": remote_request.source_build_pack_id,
            "bundle_manifest_path": str(pulled_bundle_path / "bundle.json"),
            "import_reason": wrapper_request.import_reason,
            "imported_by": wrapper_request.imported_by,
        }
        write_json(import_request_path, import_request_payload)
        import_result = import_external_runtime_evidence(
            factory_root,
            import_request_payload,
            request_file_dir=import_request_path.parent.resolve(),
        )

    roundtrip_manifest_path = wrapper_request.local_bundle_staging_dir / "roundtrip-manifest.json"
    roundtrip_manifest = {
        "schema_version": "remote-roundtrip-manifest/v1",
        "wrapper_request_sha256": wrapper_request_sha256,
        "remote_run_request_sha256": remote_run_request_sha256,
        "source_build_pack_id": remote_request.source_build_pack_id,
        "run_id": remote_request.run_id,
        "remote_target_label": remote_request.remote_target_label,
        "target_manifest_sha256": execution_result["target_manifest_sha256"],
        "execution_manifest_sha256": pull_result["execution_manifest_sha256"],
        "portable_helper_manifest_sha256": pull_result["portable_helper_manifest_sha256"],
        "pulled_bundle_path": str(pulled_bundle_path),
        "pulled_bundle_sha256": pulled_bundle_sha256,
        "pulled_at": pull_result["pulled_at"],
        "generated_import_request_path": None if import_request_path is None else str(import_request_path),
        "generated_import_request_sha256": None if import_request_path is None else sha256_path(import_request_path),
    }
    write_validated_roundtrip_manifest(
        factory_root=factory_root,
        path=roundtrip_manifest_path,
        payload=roundtrip_manifest,
    )

    return {
        "schema_version": "remote-autonomy-test-result/v1",
        "status": "completed",
        "source_build_pack_id": remote_request.source_build_pack_id,
        "run_id": remote_request.run_id,
        "remote_target_label": remote_request.remote_target_label,
        "wrapper_request_path": str(wrapper_request.request_path),
        "remote_run_request_path": str(wrapper_request.remote_run_request_path),
        "local_bundle_staging_dir": str(wrapper_request.local_bundle_staging_dir),
        "preparation_result": preparation_result,
        "staging_result": staging_result,
        "seeded_prerequisite_paths": seeded_prerequisite_paths,
        "execution_result": execution_result,
        "pull_result": pull_result,
        "import_result": import_result,
        "roundtrip_manifest_path": str(roundtrip_manifest_path),
        "import_report_path": None if import_result is None else str(import_result["import_report_path"]),
    }


def _build_run_request(
    *,
    factory_root: Path,
    pack_root: Path,
    pack_id: str,
    run_id: str,
    active_task_id: str,
    remote_target_label: str,
    remote_host: str,
    remote_user: str,
    staged_by: str,
) -> dict[str, Any]:
    remote_parent_dir = canonical_remote_parent_dir(remote_target_label)
    remote_pack_dir = canonical_remote_pack_dir(remote_parent_dir, pack_id)
    return {
        "schema_version": RUN_REQUEST_SCHEMA_VERSION,
        "source_factory_root": str(factory_root),
        "source_build_pack_id": pack_id,
        "source_build_pack_root": str(pack_root),
        "run_id": run_id,
        "remote_host": remote_host,
        "remote_user": remote_user,
        "remote_target_label": remote_target_label,
        "remote_parent_dir": remote_parent_dir,
        "remote_pack_dir": remote_pack_dir,
        "remote_run_dir": canonical_remote_run_dir(remote_pack_dir, run_id),
        "remote_export_dir": canonical_remote_export_dir(remote_pack_dir),
        "remote_reason": "Factory-default active-task continuity run from canonical mid-backlog state.",
        "staged_by": staged_by,
        "remote_runner": _build_remote_runner(run_id, active_task_id),
    }


def _build_test_request(
    *,
    factory_root: Path,
    remote_target_label: str,
    pack_id: str,
    run_id: str,
    remote_run_request_path: Path,
    imported_by: str,
) -> dict[str, Any]:
    return {
        "schema_version": TEST_REQUEST_SCHEMA_VERSION,
        "remote_run_request_path": str(remote_run_request_path),
        "local_bundle_staging_dir": str(
            canonical_local_bundle_staging_dir(
                factory_root=factory_root,
                remote_target_label=remote_target_label,
                build_pack_id=pack_id,
                run_id=run_id,
            )
        ),
        "pull_bundle": True,
        "import_bundle": True,
        "imported_by": imported_by,
        "import_reason": "Factory-default active-task continuity import from canonical mid-backlog state.",
        "test_reason": "PackFactory remote continuity run that resumes the canonical active task from feedback memory.",
    }


def run_remote_active_task_continuity_test(
    *,
    factory_root: Path,
    build_pack_id: str,
    remote_target_label: str,
    remote_host: str,
    remote_user: str,
    staged_by: str,
    imported_by: str,
    run_id: str | None,
) -> dict[str, Any]:
    location = discover_pack(factory_root, build_pack_id)
    if location.pack_kind != "build_pack":
        raise ValueError(f"{build_pack_id} is not a build_pack")
    active_task_id = _validate_active_task_boundary(location.pack_root, build_pack_id)

    resolved_run_id = run_id.strip() if run_id and run_id.strip() else _next_run_id(factory_root, remote_target_label, build_pack_id)
    request_root = _request_root(factory_root, remote_target_label, build_pack_id, resolved_run_id)
    request_root.mkdir(parents=True, exist_ok=True)
    run_request_path = request_root / "remote-run-request.json"
    test_request_path = request_root / "remote-test-request.json"

    run_request = _build_run_request(
        factory_root=factory_root,
        pack_root=location.pack_root,
        pack_id=build_pack_id,
        run_id=resolved_run_id,
        active_task_id=active_task_id,
        remote_target_label=remote_target_label,
        remote_host=remote_host,
        remote_user=remote_user,
        staged_by=staged_by,
    )
    test_request = _build_test_request(
        factory_root=factory_root,
        remote_target_label=remote_target_label,
        pack_id=build_pack_id,
        run_id=resolved_run_id,
        remote_run_request_path=run_request_path,
        imported_by=imported_by,
    )
    _write_validated(factory_root, run_request_path, run_request, RUN_REQUEST_SCHEMA_NAME)
    _write_validated(factory_root, test_request_path, test_request, TEST_REQUEST_SCHEMA_NAME)

    result = _run_roundtrip_with_seeded_validation_artifacts(
        factory_root=factory_root,
        test_request_path=test_request_path,
    )
    return {
        "schema_version": "remote-active-task-continuity-test-result/v1",
        "status": "completed",
        "build_pack_id": build_pack_id,
        "run_id": resolved_run_id,
        "active_task_id": active_task_id,
        "remote_target_label": remote_target_label,
        "remote_host": remote_host,
        "remote_user": remote_user,
        "generated_at": read_now().isoformat().replace("+00:00", "Z"),
        "request_root": str(request_root),
        "remote_run_request_path": str(run_request_path),
        "remote_test_request_path": str(test_request_path),
        "roundtrip_result": result,
    }


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run remote active-task continuity from a mid-backlog feedback-memory boundary.")
    parser.add_argument("--factory-root", required=True)
    parser.add_argument("--build-pack-id", required=True)
    parser.add_argument("--remote-target-label", required=True)
    parser.add_argument("--remote-host", required=True)
    parser.add_argument("--remote-user", required=True)
    parser.add_argument("--run-id")
    parser.add_argument("--staged-by", default="codex")
    parser.add_argument("--imported-by", default="codex")
    parser.add_argument("--output", choices=("json",), default="json")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    factory_root = resolve_factory_root(args.factory_root)
    result = run_remote_active_task_continuity_test(
        factory_root=factory_root,
        build_pack_id=args.build_pack_id,
        remote_target_label=args.remote_target_label,
        remote_host=args.remote_host,
        remote_user=args.remote_user,
        staged_by=args.staged_by,
        imported_by=args.imported_by,
        run_id=args.run_id,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
