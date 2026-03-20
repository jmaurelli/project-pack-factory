from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import ApprovalPolicy, RolloutPolicy, WorkflowPlan
from .templates import render_delegate_prompt

DEFAULT_OUTPUT_DIR = "/srv/adf/artifacts/ai-native-codex-package-template"
DEFAULT_CONTRACT = "/ai-workflow/adf/runtime-contract.json"
DEFAULT_OPERATION_CLASS = "delegated_execution"
DEFAULT_CYCLE_ROOT = "/ai-workflow/adf/artifacts/orchestration"
DEFAULT_APPROVAL_POLICY = str(
    Path(__file__).resolve().parent / "policies" / "approval-policy.json"
)
DEFAULT_MINIMUM_ROLLOUT_ORDER = str(
    Path(__file__).resolve().parent / "policies" / "minimum-rollout-order.json"
)

DELEGATED_BACKEND = "delegated_worker"
DIRECT_BACKEND = "local_only"

_DELEGATE_SCRIPT = "/ai-workflow/orchestration/run_adf_delegate.py"
_FIXED_INTENT = "execution_only"
_FIXED_DELEGATION_MODE = "codex_worker"
_PREVIEW_PLACEHOLDER = "<PREVIEW>"


def _load_json_object(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"policy artifact must deserialize to a JSON object: {path}")
    return payload


def load_approval_policy(*, path: str = DEFAULT_APPROVAL_POLICY) -> ApprovalPolicy:
    return ApprovalPolicy.from_mapping(_load_json_object(path))


def load_rollout_policy(*, path: str = DEFAULT_MINIMUM_ROLLOUT_ORDER) -> RolloutPolicy:
    return RolloutPolicy.from_mapping(_load_json_object(path))


def build_delegate_command_plan(plan: WorkflowPlan, prompt_file: str) -> dict[str, list[str]]:
    shared = [
        "python3",
        _DELEGATE_SCRIPT,
        "--prompt-file",
        prompt_file,
        "--contract",
        plan.contract,
        "--intent",
        _FIXED_INTENT,
        "--operation-class",
        plan.operation_class,
        "--delegation-mode",
        _FIXED_DELEGATION_MODE,
    ]
    return {
        "preflight": [
            *shared,
            "--dry-run",
            "--json",
        ],
        "dispatch": [
            *shared,
            "--require-preflight-evidence",
            _PREVIEW_PLACEHOLDER,
            "--json",
        ],
    }


def build_continuation_backend_payload(plan: WorkflowPlan) -> dict[str, object]:
    if plan.continuation_decision is None:
        return {}
    return {
        "autonomous_continuation": {
            "result": plan.continuation_decision.result,
            "continue_automatically": plan.continuation_decision.continue_automatically,
            "next_task_id": plan.continuation_decision.next_task_id,
            "stop_reasons": list(plan.continuation_decision.stop_reasons),
            "explanation": plan.continuation_decision.explanation(),
            "replay_resume_input": (
                plan.continuation_decision.replay_resume_input.to_dict()
                if plan.continuation_decision.replay_resume_input is not None
                else None
            ),
        }
    }


def build_audit_replay_backend_payload(plan: WorkflowPlan) -> dict[str, object]:
    payload: dict[str, object] = {}
    if plan.predispatch_decision is not None:
        payload["predispatch"] = {
            "decision": plan.predispatch_decision.to_dict(),
            "explanation": plan.predispatch_decision.explanation(),
        }
    if plan.posttask_decision is not None:
        payload["posttask"] = {
            "decision": plan.posttask_decision.to_dict(),
            "explanation": plan.posttask_decision.explanation(),
        }
    if plan.replay_resume_input is not None:
        payload["replay_resume_input"] = plan.replay_resume_input.to_dict()
    if plan.continuation_decision is not None:
        payload["continuation"] = plan.continuation_decision.explanation()
    if not payload:
        return {}
    return {"audit_and_replay": payload}


def build_backend_payload(plan: WorkflowPlan, *, prompt_file: str, include_prompt: bool) -> dict[str, object]:
    payload: dict[str, object] = build_continuation_backend_payload(plan)
    payload.update(build_audit_replay_backend_payload(plan))
    if plan.backend != DELEGATED_BACKEND:
        return payload

    payload["delegate_commands"] = build_delegate_command_plan(plan, prompt_file=prompt_file)
    if include_prompt:
        payload["rendered_prompt"] = render_delegate_prompt(plan)
    return payload
