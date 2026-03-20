from __future__ import annotations

from collections.abc import Mapping, Sequence

from .backends import build_backend_payload, load_approval_policy, load_rollout_policy
from .models import (
    ApprovalPolicy,
    ContinuationDecision,
    ContinuationGateDecision,
    ReplayResumeInput,
    RolloutPolicy,
    TaskSelectionContext,
    TaskSelectionDecision,
    TaskSelectionEvaluation,
    TaskSelectionInput,
    TaskSelectionState,
    WorkflowPlan,
    WorkflowRequest,
)

_GLOBAL_BLOCKER_REASON_ORDER = (
    "blocking_validation_failure",
    "unresolved_scope_mismatch",
)
_TASK_BLOCKER_REASON_ORDER = (
    "dependencies_not_satisfied",
    "approval_not_dispatchable",
    "approval_blocks_autonomous_continuation",
    "brief_not_ready",
    "task_blocked",
)
_FALLBACK_ORDERING = ("declared_order", "task_id")
_REPLAY_COMPLETED_TASK_STATES = frozenset({"completed"})
_REPLAY_BLOCKED_TASK_STATES = frozenset({"blocked", "retry_pending", "escalated", "failed"})
_REPLAY_READY_TASK_STATES = frozenset({"pending", "in_progress", "ready_to_dispatch"})


def _normalize_task_name(task_name: str) -> str:
    normalized = task_name.strip()
    if not normalized:
        raise ValueError("task name is required")
    return normalized


def _coerce_selection_context(
    selection_context: TaskSelectionContext
    | Mapping[str, object]
    | Sequence[TaskSelectionInput | Mapping[str, object]],
) -> TaskSelectionContext:
    if isinstance(selection_context, TaskSelectionContext):
        return selection_context
    if isinstance(selection_context, Mapping):
        task_records = selection_context.get("task_records")
        if not isinstance(task_records, Sequence) or isinstance(task_records, str | bytes):
            raise ValueError("selection_context must declare ordered `task_records`")
        state = selection_context.get("state")
        if state is not None and not isinstance(state, Mapping):
            raise ValueError("selection_context `state` must be an object when provided")
        return TaskSelectionContext.from_task_records(task_records, state=state)
    return TaskSelectionContext.from_task_records(selection_context)


def _coerce_approval_policy(
    approval_policy: ApprovalPolicy | Mapping[str, object] | None,
) -> ApprovalPolicy:
    if approval_policy is None:
        return load_approval_policy()
    if isinstance(approval_policy, ApprovalPolicy):
        return approval_policy
    return ApprovalPolicy.from_mapping(approval_policy)


def _coerce_rollout_policy(
    rollout_policy: RolloutPolicy | Mapping[str, object] | None,
) -> RolloutPolicy:
    if rollout_policy is None:
        return load_rollout_policy()
    if isinstance(rollout_policy, RolloutPolicy):
        return rollout_policy
    return RolloutPolicy.from_mapping(rollout_policy)


def _task_sort_key(task: TaskSelectionInput | TaskSelectionEvaluation) -> tuple[int, str]:
    return (task.declared_order, task.task_id)


def _coerce_gate_decision(
    gate_decision: ContinuationGateDecision | Mapping[str, object] | None,
    *,
    gate: str,
) -> ContinuationGateDecision | None:
    if gate_decision is None:
        return None
    if isinstance(gate_decision, ContinuationGateDecision):
        if gate_decision.gate != gate:
            raise ValueError(f"continuation gate decision must declare gate `{gate}`")
        return gate_decision
    return ContinuationGateDecision.from_mapping(gate_decision, gate=gate)


def _coerce_replay_resume_input(
    replay_resume_input: ReplayResumeInput | Mapping[str, object] | None,
) -> ReplayResumeInput | None:
    if replay_resume_input is None:
        return None
    if isinstance(replay_resume_input, ReplayResumeInput):
        return replay_resume_input
    return ReplayResumeInput.from_mapping(replay_resume_input)


def _apply_replay_task_outcomes(
    selection_context: TaskSelectionContext | None,
    replay_resume_input: ReplayResumeInput | None,
) -> TaskSelectionContext | None:
    if selection_context is None or replay_resume_input is None or not replay_resume_input.task_outcomes:
        return selection_context

    completed_task_ids = set(selection_context.state.completed_task_ids)
    blocked_task_ids = set(selection_context.state.blocked_task_ids)
    for task_outcome in replay_resume_input.task_outcomes:
        resulting_task_state = task_outcome.resulting_task_state
        if resulting_task_state in _REPLAY_COMPLETED_TASK_STATES:
            completed_task_ids.add(task_outcome.task_id)
            blocked_task_ids.discard(task_outcome.task_id)
            continue
        if resulting_task_state in _REPLAY_BLOCKED_TASK_STATES:
            completed_task_ids.discard(task_outcome.task_id)
            blocked_task_ids.add(task_outcome.task_id)
            continue
        if resulting_task_state in _REPLAY_READY_TASK_STATES:
            blocked_task_ids.discard(task_outcome.task_id)
            continue
        raise ValueError(
            "unsupported replay task outcome state "
            f"`{resulting_task_state}` for task `{task_outcome.task_id}`"
        )

    return TaskSelectionContext(
        task_records=selection_context.task_records,
        state=TaskSelectionState(
            completed_task_ids=frozenset(completed_task_ids),
            blocked_task_ids=frozenset(blocked_task_ids),
            blocking_validation_task_ids=selection_context.state.blocking_validation_task_ids,
            unresolved_scope_mismatch_task_ids=(
                selection_context.state.unresolved_scope_mismatch_task_ids
            ),
            brief_unready_task_ids=selection_context.state.brief_unready_task_ids,
        ),
    )


def _coerce_selection_decision(
    selection_decision: TaskSelectionDecision | None,
    selection_context: TaskSelectionContext | None,
    *,
    approval_policy: ApprovalPolicy,
    rollout_policy: RolloutPolicy,
) -> TaskSelectionDecision:
    if selection_decision is not None:
        return selection_decision
    if selection_context is None:
        raise ValueError(
            "selection_context or selection_decision is required for autonomous continuation"
        )
    return select_next_task(
        selection_context,
        approval_policy=approval_policy,
        rollout_policy=rollout_policy,
    )


def _dedupe_reasons(*reason_groups: Sequence[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    ordered: list[str] = []
    for group in reason_groups:
        for reason in group:
            if reason not in seen:
                seen.add(reason)
                ordered.append(reason)
    return tuple(ordered)


def _gate_stop_reasons(gate_decision: ContinuationGateDecision) -> tuple[str, ...]:
    reasons = [
        f"{gate_decision.gate}_required_validator_missing:{validator}"
        for validator in gate_decision.missing_required_validators
    ]
    reasons.extend(
        f"{gate_decision.gate}_validator_failed:{validator}"
        for validator in gate_decision.failing_validator_labels
    )
    if gate_decision.decision == "blocked":
        reasons.append(f"{gate_decision.gate}_gate_blocked")
        reasons.extend(f"{gate_decision.gate}:{reason}" for reason in gate_decision.blocking_reasons)
    return tuple(reasons)


def _build_stop_decision(
    *,
    stop_reasons: Sequence[str],
    selection_decision: TaskSelectionDecision,
    predispatch_decision: ContinuationGateDecision | None,
    posttask_decision: ContinuationGateDecision | None,
    approval_policy: ApprovalPolicy,
    rollout_policy: RolloutPolicy,
    replay_resume_input: ReplayResumeInput | None,
) -> ContinuationDecision:
    next_task_id = (
        selection_decision.selected_task.task_id
        if selection_decision.selected_task is not None
        else None
    )
    return ContinuationDecision(
        result="stop",
        continue_automatically=False,
        next_task_id=next_task_id,
        stop_reasons=_dedupe_reasons(stop_reasons),
        selection_decision=selection_decision,
        predispatch_decision=predispatch_decision,
        posttask_decision=posttask_decision,
        approval_policy=approval_policy,
        rollout_policy=rollout_policy,
        replay_resume_input=replay_resume_input,
    )


def _validate_task_records(task_records: Sequence[TaskSelectionInput]) -> dict[str, TaskSelectionInput]:
    records_by_id: dict[str, TaskSelectionInput] = {}
    for task_record in sorted(task_records, key=_task_sort_key):
        if task_record.task_id in records_by_id:
            raise ValueError(f"duplicate task_id found in selection context: {task_record.task_id}")
        records_by_id[task_record.task_id] = task_record

    for task_record in task_records:
        for dependency in task_record.dependencies:
            if dependency not in records_by_id:
                raise ValueError(
                    f"task `{task_record.task_id}` depends on unknown task_id `{dependency}`"
                )
    return records_by_id


def _task_reasons(
    *,
    task_record: TaskSelectionInput,
    state: TaskSelectionState,
    completed_task_ids: frozenset[str],
    approval_policy: ApprovalPolicy,
) -> tuple[tuple[str, ...], tuple[str, ...], bool, bool, bool]:
    reasons: list[str] = []
    missing_dependencies = tuple(
        dependency
        for dependency in task_record.dependencies
        if dependency not in completed_task_ids
    )
    if task_record.task_id in completed_task_ids:
        reasons.append("completed")
    if missing_dependencies:
        reasons.append("dependencies_not_satisfied")

    approval_state_policy = approval_policy.policy_for_state(task_record.approval_state)
    if not approval_state_policy.dispatchable:
        reasons.append("approval_not_dispatchable")
    elif not approval_state_policy.permits_autonomous_continuation:
        reasons.append("approval_blocks_autonomous_continuation")

    if task_record.task_id in state.brief_unready_task_ids:
        reasons.append("brief_not_ready")
    if task_record.task_id in state.blocked_task_ids:
        reasons.append("task_blocked")

    is_completed = task_record.task_id in completed_task_ids
    is_blocked = task_record.task_id in state.blocked_task_ids
    is_fully_specified = task_record.task_id not in state.brief_unready_task_ids
    return tuple(reasons), missing_dependencies, is_completed, is_blocked, is_fully_specified


def _build_task_evaluations(
    selection_context: TaskSelectionContext,
    approval_policy: ApprovalPolicy,
) -> tuple[TaskSelectionEvaluation, ...]:
    evaluations: list[TaskSelectionEvaluation] = []
    completed_task_ids = selection_context.state.completed_task_ids
    for task_record in sorted(selection_context.task_records, key=_task_sort_key):
        (
            reasons,
            missing_dependencies,
            is_completed,
            is_blocked,
            is_fully_specified,
        ) = _task_reasons(
            task_record=task_record,
            state=selection_context.state,
            completed_task_ids=completed_task_ids,
            approval_policy=approval_policy,
        )
        evaluation = TaskSelectionEvaluation(
            task_id=task_record.task_id,
            task_name=task_record.task_name,
            declared_order=task_record.declared_order,
            approval_state=task_record.approval_state,
            approval_dispatchable=approval_policy.policy_for_state(
                task_record.approval_state
            ).dispatchable,
            approval_allows_autonomous_continuation=approval_policy.policy_for_state(
                task_record.approval_state
            ).permits_autonomous_continuation,
            dependencies_satisfied=not missing_dependencies,
            missing_dependencies=missing_dependencies,
            dependency_unlock_score=task_record.dependency_unlock_score,
            risk_reduction_score=task_record.risk_reduction_score,
            is_completed=is_completed,
            is_blocked=is_blocked,
            is_fully_specified=is_fully_specified,
            eligible=not reasons,
            reasons=reasons,
        )
        evaluations.append(evaluation)
    return tuple(evaluations)


def _apply_ordering(
    evaluations: Sequence[TaskSelectionEvaluation],
) -> tuple[tuple[TaskSelectionEvaluation, ...], tuple[str, ...], tuple[str, ...]]:
    ordered = tuple(sorted(evaluations, key=_task_sort_key))
    if len(ordered) <= 1:
        return ordered, (), ()

    if all(item.dependency_unlock_score is not None for item in ordered):
        grouped_by_dependency_unlock_score: dict[float, list[TaskSelectionEvaluation]] = {}
        for item in ordered:
            score = item.dependency_unlock_score
            assert score is not None
            grouped_by_dependency_unlock_score.setdefault(score, []).append(item)

        ranked: list[TaskSelectionEvaluation] = []
        risk_applied = False
        risk_skipped = False
        for score in sorted(grouped_by_dependency_unlock_score, reverse=True):
            ranked_group, group_applied, group_skipped = _apply_risk_ordering(
                grouped_by_dependency_unlock_score[score]
            )
            ranked.extend(ranked_group)
            risk_applied = risk_applied or "risk_reduction_score" in group_applied
            risk_skipped = risk_skipped or "risk_reduction_score" in group_skipped

        applied_ordering = ["dependency_unlock_score"]
        skipped_ordering: list[str] = []
        if risk_applied:
            applied_ordering.append("risk_reduction_score")
        if risk_skipped:
            skipped_ordering.append("risk_reduction_score")
        return tuple(ranked), tuple(applied_ordering), tuple(skipped_ordering)

    risk_ranked, risk_applied_ordering, risk_skipped_ordering = _apply_risk_ordering(ordered)
    skipped_ordering = ["dependency_unlock_score"]
    if risk_skipped_ordering:
        skipped_ordering.append("risk_reduction_score")
    return tuple(risk_ranked), tuple(risk_applied_ordering), tuple(skipped_ordering)


def _apply_risk_ordering(
    evaluations: Sequence[TaskSelectionEvaluation],
) -> tuple[tuple[TaskSelectionEvaluation, ...], tuple[str, ...], tuple[str, ...]]:
    ordered = tuple(sorted(evaluations, key=_task_sort_key))
    if len(ordered) <= 1:
        return ordered, (), ()
    if not all(item.risk_reduction_score is not None for item in ordered):
        return ordered, (), ("risk_reduction_score",)

    grouped_by_risk_reduction_score: dict[float, list[TaskSelectionEvaluation]] = {}
    for item in ordered:
        score = item.risk_reduction_score
        assert score is not None
        grouped_by_risk_reduction_score.setdefault(score, []).append(item)

    ranked: list[TaskSelectionEvaluation] = []
    for score in sorted(grouped_by_risk_reduction_score, reverse=True):
        ranked.extend(sorted(grouped_by_risk_reduction_score[score], key=_task_sort_key))
    return tuple(ranked), ("risk_reduction_score",), ()


def _aggregate_blocked_reasons(
    selection_context: TaskSelectionContext,
    remaining_evaluations: Sequence[TaskSelectionEvaluation],
) -> tuple[str, ...]:
    blocker_flags = {
        "blocking_validation_failure": bool(selection_context.state.blocking_validation_task_ids),
        "unresolved_scope_mismatch": bool(selection_context.state.unresolved_scope_mismatch_task_ids),
    }
    reasons = [
        reason for reason in _GLOBAL_BLOCKER_REASON_ORDER if blocker_flags[reason]
    ]
    if reasons:
        return tuple(reasons)
    if any(evaluation.eligible for evaluation in remaining_evaluations):
        return ()

    reason_set = {
        reason
        for evaluation in remaining_evaluations
        for reason in evaluation.reasons
        if reason != "completed"
    }
    ordered_reasons = [
        reason for reason in _TASK_BLOCKER_REASON_ORDER if reason in reason_set
    ]
    if ordered_reasons:
        return tuple(ordered_reasons)
    if remaining_evaluations:
        return ("no_eligible_task",)
    return ()


def build_task_selection_context(
    task_records: Sequence[TaskSelectionInput | Mapping[str, object]],
    *,
    completed_task_ids: Sequence[str] = (),
    blocked_task_ids: Sequence[str] = (),
    blocking_validation_task_ids: Sequence[str] = (),
    unresolved_scope_mismatch_task_ids: Sequence[str] = (),
    brief_unready_task_ids: Sequence[str] = (),
) -> TaskSelectionContext:
    state = TaskSelectionState.from_mapping(
        {
            "completed_task_ids": list(completed_task_ids),
            "blocked_task_ids": list(blocked_task_ids),
            "blocking_validation_task_ids": list(blocking_validation_task_ids),
            "unresolved_scope_mismatch_task_ids": list(unresolved_scope_mismatch_task_ids),
            "brief_unready_task_ids": list(brief_unready_task_ids),
        }
    )
    return TaskSelectionContext.from_task_records(task_records, state=state)


def select_next_task(
    selection_context: TaskSelectionContext
    | Mapping[str, object]
    | Sequence[TaskSelectionInput | Mapping[str, object]],
    *,
    approval_policy: ApprovalPolicy | Mapping[str, object] | None = None,
    rollout_policy: RolloutPolicy | Mapping[str, object] | None = None,
) -> TaskSelectionDecision:
    normalized_context = _coerce_selection_context(selection_context)
    normalized_approval_policy = _coerce_approval_policy(approval_policy)
    normalized_rollout_policy = _coerce_rollout_policy(rollout_policy)
    records_by_id = _validate_task_records(normalized_context.task_records)

    evaluations = _build_task_evaluations(normalized_context, normalized_approval_policy)
    remaining_evaluations = tuple(
        evaluation for evaluation in evaluations if not evaluation.is_completed
    )
    eligible_evaluations = tuple(
        evaluation for evaluation in remaining_evaluations if evaluation.eligible
    )
    ordered_candidates, applied_ordering, skipped_ordering = _apply_ordering(eligible_evaluations)
    blocked_reasons = _aggregate_blocked_reasons(normalized_context, remaining_evaluations)

    selected_task = None
    result = "blocked"
    if not blocked_reasons and not remaining_evaluations:
        result = "complete"
    elif not blocked_reasons and ordered_candidates:
        result = "selected"
        selected_task = records_by_id[ordered_candidates[0].task_id]

    return TaskSelectionDecision(
        result=result,
        selected_task=selected_task,
        eligible_task_ids=tuple(evaluation.task_id for evaluation in eligible_evaluations),
        ordered_candidate_task_ids=tuple(evaluation.task_id for evaluation in ordered_candidates),
        applied_ordering=applied_ordering,
        skipped_ordering=skipped_ordering,
        blocked_reasons=blocked_reasons,
        fallback_ordering=_FALLBACK_ORDERING,
        approval_policy=normalized_approval_policy,
        rollout_policy=normalized_rollout_policy,
        task_evaluations=evaluations,
    )


def build_task_selection_payload(
    selection_context: TaskSelectionContext
    | Mapping[str, object]
    | Sequence[TaskSelectionInput | Mapping[str, object]],
    *,
    approval_policy: ApprovalPolicy | Mapping[str, object] | None = None,
    rollout_policy: RolloutPolicy | Mapping[str, object] | None = None,
) -> dict[str, object]:
    return select_next_task(
        selection_context,
        approval_policy=approval_policy,
        rollout_policy=rollout_policy,
    ).to_dict()


def build_continuation_payload(
    selection_context: TaskSelectionContext
    | Mapping[str, object]
    | Sequence[TaskSelectionInput | Mapping[str, object]],
    *,
    selection_decision: TaskSelectionDecision | None = None,
    predispatch_decision: ContinuationGateDecision | Mapping[str, object] | None = None,
    posttask_decision: ContinuationGateDecision | Mapping[str, object] | None = None,
    replay_resume_input: ReplayResumeInput | Mapping[str, object] | None = None,
    approval_policy: ApprovalPolicy | Mapping[str, object] | None = None,
    rollout_policy: RolloutPolicy | Mapping[str, object] | None = None,
) -> dict[str, object]:
    return decide_autonomous_continuation(
        selection_context,
        selection_decision=selection_decision,
        predispatch_decision=predispatch_decision,
        posttask_decision=posttask_decision,
        replay_resume_input=replay_resume_input,
        approval_policy=approval_policy,
        rollout_policy=rollout_policy,
    ).to_dict()


def decide_autonomous_continuation(
    selection_context: TaskSelectionContext
    | Mapping[str, object]
    | Sequence[TaskSelectionInput | Mapping[str, object]],
    *,
    selection_decision: TaskSelectionDecision | None = None,
    predispatch_decision: ContinuationGateDecision | Mapping[str, object] | None = None,
    posttask_decision: ContinuationGateDecision | Mapping[str, object] | None = None,
    replay_resume_input: ReplayResumeInput | Mapping[str, object] | None = None,
    approval_policy: ApprovalPolicy | Mapping[str, object] | None = None,
    rollout_policy: RolloutPolicy | Mapping[str, object] | None = None,
) -> ContinuationDecision:
    normalized_replay_resume_input = _coerce_replay_resume_input(replay_resume_input)
    normalized_context = _apply_replay_task_outcomes(
        _coerce_selection_context(selection_context),
        normalized_replay_resume_input,
    )
    if normalized_context is None:
        raise ValueError("selection_context is required for autonomous continuation")
    normalized_approval_policy = _coerce_approval_policy(approval_policy)
    normalized_rollout_policy = _coerce_rollout_policy(rollout_policy)
    normalized_selection_decision = _coerce_selection_decision(
        selection_decision,
        normalized_context,
        approval_policy=normalized_approval_policy,
        rollout_policy=normalized_rollout_policy,
    )
    normalized_predispatch_decision = _coerce_gate_decision(
        predispatch_decision,
        gate="predispatch",
    )
    if normalized_predispatch_decision is None and normalized_replay_resume_input is not None:
        normalized_predispatch_decision = normalized_replay_resume_input.predispatch_decision
    normalized_posttask_decision = _coerce_gate_decision(
        posttask_decision,
        gate="posttask",
    )
    if normalized_posttask_decision is None and normalized_replay_resume_input is not None:
        normalized_posttask_decision = normalized_replay_resume_input.posttask_decision

    if normalized_posttask_decision is None:
        return _build_stop_decision(
            stop_reasons=("posttask_decision_required",),
            selection_decision=normalized_selection_decision,
            predispatch_decision=normalized_predispatch_decision,
            posttask_decision=None,
            approval_policy=normalized_approval_policy,
            rollout_policy=normalized_rollout_policy,
            replay_resume_input=normalized_replay_resume_input,
        )

    if normalized_posttask_decision.decision == "escalate":
        return ContinuationDecision(
            result="escalate",
            continue_automatically=False,
            next_task_id=None,
            stop_reasons=_dedupe_reasons(
                _gate_stop_reasons(normalized_posttask_decision),
                ("posttask_gate_escalated",),
            ),
            escalation_reason=normalized_posttask_decision.escalation_reason,
            selection_decision=normalized_selection_decision,
            predispatch_decision=normalized_predispatch_decision,
            posttask_decision=normalized_posttask_decision,
            approval_policy=normalized_approval_policy,
            rollout_policy=normalized_rollout_policy,
            replay_resume_input=normalized_replay_resume_input,
        )

    if normalized_posttask_decision.decision == "retry":
        return ContinuationDecision(
            result="retry",
            continue_automatically=False,
            next_task_id=None,
            stop_reasons=_dedupe_reasons(
                _gate_stop_reasons(normalized_posttask_decision),
                ("posttask_gate_retry",),
            ),
            retry_reason=normalized_posttask_decision.retry_reason,
            selection_decision=normalized_selection_decision,
            predispatch_decision=normalized_predispatch_decision,
            posttask_decision=normalized_posttask_decision,
            approval_policy=normalized_approval_policy,
            rollout_policy=normalized_rollout_policy,
            replay_resume_input=normalized_replay_resume_input,
        )

    posttask_stop_reasons = _gate_stop_reasons(normalized_posttask_decision)
    if normalized_posttask_decision.decision != "complete" or posttask_stop_reasons:
        return _build_stop_decision(
            stop_reasons=_dedupe_reasons(
                posttask_stop_reasons,
                ("posttask_gate_incomplete",),
            ),
            selection_decision=normalized_selection_decision,
            predispatch_decision=normalized_predispatch_decision,
            posttask_decision=normalized_posttask_decision,
            approval_policy=normalized_approval_policy,
            rollout_policy=normalized_rollout_policy,
            replay_resume_input=normalized_replay_resume_input,
        )

    if normalized_selection_decision.result == "complete":
        return ContinuationDecision(
            result="complete",
            continue_automatically=False,
            next_task_id=None,
            selection_decision=normalized_selection_decision,
            predispatch_decision=normalized_predispatch_decision,
            posttask_decision=normalized_posttask_decision,
            approval_policy=normalized_approval_policy,
            rollout_policy=normalized_rollout_policy,
            replay_resume_input=normalized_replay_resume_input,
        )

    if (
        normalized_selection_decision.result != "selected"
        or normalized_selection_decision.selected_task is None
    ):
        return _build_stop_decision(
            stop_reasons=_dedupe_reasons(
                normalized_selection_decision.blocked_reasons,
                ("no_selected_task_for_continuation",),
            ),
            selection_decision=normalized_selection_decision,
            predispatch_decision=normalized_predispatch_decision,
            posttask_decision=normalized_posttask_decision,
            approval_policy=normalized_approval_policy,
            rollout_policy=normalized_rollout_policy,
            replay_resume_input=normalized_replay_resume_input,
        )

    selected_task = normalized_selection_decision.selected_task
    selected_task_approval_policy = normalized_approval_policy.policy_for_state(
        selected_task.approval_state
    )
    approval_stop_reasons: list[str] = []
    if not selected_task_approval_policy.dispatchable:
        approval_stop_reasons.append(
            f"next_task_approval_not_dispatchable:{selected_task.approval_state}"
        )
    if not selected_task_approval_policy.permits_autonomous_continuation:
        approval_stop_reasons.append(
            "next_task_approval_blocks_autonomous_continuation:"
            f"{selected_task.approval_state}"
        )
    if approval_stop_reasons:
        return _build_stop_decision(
            stop_reasons=approval_stop_reasons,
            selection_decision=normalized_selection_decision,
            predispatch_decision=normalized_predispatch_decision,
            posttask_decision=normalized_posttask_decision,
            approval_policy=normalized_approval_policy,
            rollout_policy=normalized_rollout_policy,
            replay_resume_input=normalized_replay_resume_input,
        )

    if normalized_predispatch_decision is None:
        return _build_stop_decision(
            stop_reasons=("predispatch_decision_required",),
            selection_decision=normalized_selection_decision,
            predispatch_decision=None,
            posttask_decision=normalized_posttask_decision,
            approval_policy=normalized_approval_policy,
            rollout_policy=normalized_rollout_policy,
            replay_resume_input=normalized_replay_resume_input,
        )

    predispatch_stop_reasons = list(_gate_stop_reasons(normalized_predispatch_decision))
    if normalized_predispatch_decision.task_id != selected_task.task_id:
        predispatch_stop_reasons.append("predispatch_task_mismatch")
    if normalized_predispatch_decision.approval_state != selected_task.approval_state:
        predispatch_stop_reasons.append("predispatch_approval_state_mismatch")
    predispatch_approval_state = normalized_predispatch_decision.approval_state
    if predispatch_approval_state is None:
        predispatch_stop_reasons.append("predispatch_approval_state_missing")
        return _build_stop_decision(
            stop_reasons=predispatch_stop_reasons,
            selection_decision=normalized_selection_decision,
            predispatch_decision=normalized_predispatch_decision,
            posttask_decision=normalized_posttask_decision,
            approval_policy=normalized_approval_policy,
            rollout_policy=normalized_rollout_policy,
            replay_resume_input=normalized_replay_resume_input,
        )
    predispatch_approval_policy = normalized_approval_policy.policy_for_state(
        predispatch_approval_state
    )
    if not predispatch_approval_policy.dispatchable:
        predispatch_stop_reasons.append(
            "predispatch_approval_not_dispatchable:"
            f"{normalized_predispatch_decision.approval_state}"
        )
    if not predispatch_approval_policy.permits_autonomous_continuation:
        predispatch_stop_reasons.append(
            "predispatch_approval_blocks_autonomous_continuation:"
            f"{normalized_predispatch_decision.approval_state}"
        )
    if normalized_predispatch_decision.decision == "escalate":
        return ContinuationDecision(
            result="escalate",
            continue_automatically=False,
            next_task_id=selected_task.task_id,
            stop_reasons=_dedupe_reasons(
                predispatch_stop_reasons,
                ("predispatch_gate_escalated",),
            ),
            escalation_reason=normalized_predispatch_decision.escalation_reason,
            selection_decision=normalized_selection_decision,
            predispatch_decision=normalized_predispatch_decision,
            posttask_decision=normalized_posttask_decision,
            approval_policy=normalized_approval_policy,
            rollout_policy=normalized_rollout_policy,
            replay_resume_input=normalized_replay_resume_input,
        )

    if normalized_predispatch_decision.decision != "dispatch" or predispatch_stop_reasons:
        return _build_stop_decision(
            stop_reasons=_dedupe_reasons(
                predispatch_stop_reasons,
                ("predispatch_gate_not_dispatchable",),
            ),
            selection_decision=normalized_selection_decision,
            predispatch_decision=normalized_predispatch_decision,
            posttask_decision=normalized_posttask_decision,
            approval_policy=normalized_approval_policy,
            rollout_policy=normalized_rollout_policy,
            replay_resume_input=normalized_replay_resume_input,
        )

    return ContinuationDecision(
        result="continue",
        continue_automatically=True,
        next_task_id=selected_task.task_id,
        selection_decision=normalized_selection_decision,
        predispatch_decision=normalized_predispatch_decision,
        posttask_decision=normalized_posttask_decision,
        approval_policy=normalized_approval_policy,
        rollout_policy=normalized_rollout_policy,
        replay_resume_input=normalized_replay_resume_input,
    )


def build_workflow_request(
    task_name: str,
    backend: str,
    output_dir: str,
    contract: str,
    operation_class: str,
    cycle_root: str,
    *,
    selection_context: TaskSelectionContext | None = None,
    selection_decision: TaskSelectionDecision | None = None,
    predispatch_decision: ContinuationGateDecision | Mapping[str, object] | None = None,
    posttask_decision: ContinuationGateDecision | Mapping[str, object] | None = None,
    continuation_decision: ContinuationDecision | None = None,
    replay_resume_input: ReplayResumeInput | Mapping[str, object] | None = None,
) -> WorkflowRequest:
    return WorkflowRequest(
        task_name=_normalize_task_name(task_name),
        backend=backend,
        output_dir=output_dir,
        contract=contract,
        operation_class=operation_class,
        cycle_root=cycle_root,
        selection_context=selection_context,
        selection_decision=selection_decision,
        predispatch_decision=_coerce_gate_decision(predispatch_decision, gate="predispatch"),
        posttask_decision=_coerce_gate_decision(posttask_decision, gate="posttask"),
        continuation_decision=continuation_decision,
        replay_resume_input=_coerce_replay_resume_input(replay_resume_input),
    )


def build_plan(request: WorkflowRequest) -> WorkflowPlan:
    return WorkflowPlan(
        task_name=request.task_name,
        backend=request.backend,
        output_dir=request.output_dir,
        contract=request.contract,
        operation_class=request.operation_class,
        cycle_root=request.cycle_root,
        selection_context=request.selection_context,
        selection_decision=request.selection_decision,
        predispatch_decision=request.predispatch_decision,
        posttask_decision=request.posttask_decision,
        continuation_decision=request.continuation_decision,
        replay_resume_input=request.replay_resume_input,
    )


def build_selection_plan(
    request: WorkflowRequest,
    *,
    approval_policy: ApprovalPolicy | Mapping[str, object] | None = None,
    rollout_policy: RolloutPolicy | Mapping[str, object] | None = None,
) -> WorkflowPlan:
    if request.selection_context is None:
        raise ValueError("selection_context is required to build a selection-aware plan")
    selection_context = (
        _apply_replay_task_outcomes(request.selection_context, request.replay_resume_input)
        or request.selection_context
    )
    selection_decision = select_next_task(
        selection_context,
        approval_policy=approval_policy,
        rollout_policy=rollout_policy,
    )
    return WorkflowPlan(
        task_name=request.task_name,
        backend=request.backend,
        output_dir=request.output_dir,
        contract=request.contract,
        operation_class=request.operation_class,
        cycle_root=request.cycle_root,
        selection_context=selection_context,
        selection_decision=selection_decision,
        predispatch_decision=request.predispatch_decision,
        posttask_decision=request.posttask_decision,
        continuation_decision=request.continuation_decision,
        replay_resume_input=request.replay_resume_input,
    )


def build_run_payload(plan: WorkflowPlan) -> dict[str, object]:
    payload: dict[str, object] = plan.to_dict()
    payload.update(
        build_backend_payload(
            plan,
            prompt_file="<PROMPT_FILE>",
            include_prompt=False,
        )
    )
    return payload


def build_print_plan_payload(plan: WorkflowPlan) -> dict[str, object]:
    payload: dict[str, object] = plan.to_dict()
    payload.update(
        build_backend_payload(
            plan,
            prompt_file="<PROMPT_FILE>",
            include_prompt=True,
        )
    )
    return payload


def build_workflow_payload(
    task_name: str,
    backend: str,
    output_dir: str,
    contract: str,
    operation_class: str,
    cycle_root: str,
    *,
    mode: str,
    selection_context: TaskSelectionContext | None = None,
    selection_decision: TaskSelectionDecision | None = None,
    predispatch_decision: ContinuationGateDecision | Mapping[str, object] | None = None,
    posttask_decision: ContinuationGateDecision | Mapping[str, object] | None = None,
    continuation_decision: ContinuationDecision | None = None,
    replay_resume_input: ReplayResumeInput | Mapping[str, object] | None = None,
) -> dict[str, object]:
    request = build_workflow_request(
        task_name=task_name,
        backend=backend,
        output_dir=output_dir,
        contract=contract,
        operation_class=operation_class,
        cycle_root=cycle_root,
        selection_context=selection_context,
        selection_decision=selection_decision,
        predispatch_decision=predispatch_decision,
        posttask_decision=posttask_decision,
        continuation_decision=continuation_decision,
        replay_resume_input=replay_resume_input,
    )
    plan = build_plan(request)
    if mode == "run":
        return build_run_payload(plan)
    if mode == "print-plan":
        return build_print_plan_payload(plan)
    raise ValueError(f"unsupported workflow payload mode: {mode}")
