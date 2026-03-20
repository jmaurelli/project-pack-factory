from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field


def _require_non_empty_string(value: object, *, field_name: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string")
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} must not be empty")
    return normalized


def _require_non_negative_integer(value: object, *, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{field_name} must be a non-negative integer")
    if value < 0:
        raise ValueError(f"{field_name} must be a non-negative integer")
    return value


def _optional_non_negative_number(value: object, *, field_name: str) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError(f"{field_name} must be a non-negative number when provided")
    normalized = float(value)
    if normalized < 0:
        raise ValueError(f"{field_name} must be a non-negative number when provided")
    return normalized


def _normalize_string_tuple(value: object, *, field_name: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, Sequence) or isinstance(value, str | bytes):
        raise ValueError(f"{field_name} must be an ordered collection of strings")

    ordered: list[str] = []
    seen: set[str] = set()
    for item in value:
        normalized = _require_non_empty_string(item, field_name=field_name)
        if normalized in seen:
            continue
        seen.add(normalized)
        ordered.append(normalized)
    return tuple(ordered)


def _normalize_string_frozenset(value: object, *, field_name: str) -> frozenset[str]:
    return frozenset(_normalize_string_tuple(value, field_name=field_name))


def _optional_non_empty_string(value: object, *, field_name: str) -> str | None:
    if value is None:
        return None
    return _require_non_empty_string(value, field_name=field_name)


def _dedupe_string_tuple(values: Sequence[str]) -> tuple[str, ...]:
    ordered: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return tuple(ordered)


@dataclass(frozen=True)
class TaskSelectionInput:
    task_id: str
    task_name: str
    declared_order: int
    approval_requirement: str
    approval_state: str
    dependencies: tuple[str, ...] = ()
    dependency_unlock_score: float | None = None
    risk_reduction_score: float | None = None

    @classmethod
    def from_mapping(cls, payload: Mapping[str, object]) -> TaskSelectionInput:
        return cls(
            task_id=_require_non_empty_string(payload.get("task_id"), field_name="task_id"),
            task_name=_require_non_empty_string(payload.get("task_name"), field_name="task_name"),
            declared_order=_require_non_negative_integer(
                payload.get("declared_order"),
                field_name="declared_order",
            ),
            approval_requirement=_require_non_empty_string(
                payload.get("approval_requirement"),
                field_name="approval_requirement",
            ),
            approval_state=_require_non_empty_string(
                payload.get("approval_state"),
                field_name="approval_state",
            ),
            dependencies=_normalize_string_tuple(payload.get("dependencies"), field_name="dependencies"),
            dependency_unlock_score=_optional_non_negative_number(
                payload.get("dependency_unlock_score"),
                field_name="dependency_unlock_score",
            ),
            risk_reduction_score=_optional_non_negative_number(
                payload.get("risk_reduction_score"),
                field_name="risk_reduction_score",
            ),
        )

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "task_id": self.task_id,
            "task_name": self.task_name,
            "declared_order": self.declared_order,
            "approval_requirement": self.approval_requirement,
            "approval_state": self.approval_state,
        }
        if self.dependencies:
            payload["dependencies"] = list(self.dependencies)
        if self.dependency_unlock_score is not None:
            payload["dependency_unlock_score"] = self.dependency_unlock_score
        if self.risk_reduction_score is not None:
            payload["risk_reduction_score"] = self.risk_reduction_score
        return payload


@dataclass(frozen=True)
class TaskSelectionState:
    completed_task_ids: frozenset[str] = field(default_factory=frozenset)
    blocked_task_ids: frozenset[str] = field(default_factory=frozenset)
    blocking_validation_task_ids: frozenset[str] = field(default_factory=frozenset)
    unresolved_scope_mismatch_task_ids: frozenset[str] = field(default_factory=frozenset)
    brief_unready_task_ids: frozenset[str] = field(default_factory=frozenset)

    @classmethod
    def from_mapping(cls, payload: Mapping[str, object]) -> TaskSelectionState:
        return cls(
            completed_task_ids=_normalize_string_frozenset(
                payload.get("completed_task_ids"),
                field_name="completed_task_ids",
            ),
            blocked_task_ids=_normalize_string_frozenset(
                payload.get("blocked_task_ids"),
                field_name="blocked_task_ids",
            ),
            blocking_validation_task_ids=_normalize_string_frozenset(
                payload.get("blocking_validation_task_ids"),
                field_name="blocking_validation_task_ids",
            ),
            unresolved_scope_mismatch_task_ids=_normalize_string_frozenset(
                payload.get("unresolved_scope_mismatch_task_ids"),
                field_name="unresolved_scope_mismatch_task_ids",
            ),
            brief_unready_task_ids=_normalize_string_frozenset(
                payload.get("brief_unready_task_ids"),
                field_name="brief_unready_task_ids",
            ),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "completed_task_ids": sorted(self.completed_task_ids),
            "blocked_task_ids": sorted(self.blocked_task_ids),
            "blocking_validation_task_ids": sorted(self.blocking_validation_task_ids),
            "unresolved_scope_mismatch_task_ids": sorted(self.unresolved_scope_mismatch_task_ids),
            "brief_unready_task_ids": sorted(self.brief_unready_task_ids),
        }


@dataclass(frozen=True)
class TaskSelectionContext:
    task_records: tuple[TaskSelectionInput, ...] = ()
    state: TaskSelectionState = field(default_factory=TaskSelectionState)

    @classmethod
    def from_task_records(
        cls,
        task_records: Sequence[TaskSelectionInput | Mapping[str, object]],
        *,
        state: TaskSelectionState | Mapping[str, object] | None = None,
    ) -> TaskSelectionContext:
        normalized_records = tuple(
            record if isinstance(record, TaskSelectionInput) else TaskSelectionInput.from_mapping(record)
            for record in task_records
        )
        if state is None:
            normalized_state = TaskSelectionState()
        elif isinstance(state, TaskSelectionState):
            normalized_state = state
        else:
            normalized_state = TaskSelectionState.from_mapping(state)
        return cls(task_records=normalized_records, state=normalized_state)

    def to_dict(self) -> dict[str, object]:
        return {
            "task_records": [record.to_dict() for record in sorted(self.task_records, key=_task_sort_key)],
            "state": self.state.to_dict(),
        }


@dataclass(frozen=True)
class ApprovalStatePolicy:
    approval_state: str
    dispatchable: bool
    autonomous_continuation: str
    predispatch_outcome: str
    allowed_next_states: tuple[str, ...] = ()

    @classmethod
    def from_mapping(cls, payload: Mapping[str, object]) -> ApprovalStatePolicy:
        dispatchable = payload.get("dispatchable")
        if not isinstance(dispatchable, bool):
            raise ValueError("approval state policy `dispatchable` must be boolean")
        return cls(
            approval_state=_require_non_empty_string(
                payload.get("approval_state"),
                field_name="approval_state",
            ),
            dispatchable=dispatchable,
            autonomous_continuation=_require_non_empty_string(
                payload.get("autonomous_continuation"),
                field_name="autonomous_continuation",
            ),
            predispatch_outcome=_require_non_empty_string(
                payload.get("predispatch_outcome"),
                field_name="predispatch_outcome",
            ),
            allowed_next_states=_normalize_string_tuple(
                payload.get("allowed_next_states"),
                field_name="allowed_next_states",
            ),
        )

    @property
    def permits_autonomous_continuation(self) -> bool:
        return self.dispatchable and self.autonomous_continuation == "allowed"

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "approval_state": self.approval_state,
            "dispatchable": self.dispatchable,
            "autonomous_continuation": self.autonomous_continuation,
            "predispatch_outcome": self.predispatch_outcome,
        }
        if self.allowed_next_states:
            payload["allowed_next_states"] = list(self.allowed_next_states)
        return payload


@dataclass(frozen=True)
class ApprovalPolicy:
    policy_version: str
    non_dispatchable_outcome: str
    state_policies: tuple[ApprovalStatePolicy, ...]

    @classmethod
    def from_mapping(cls, payload: Mapping[str, object]) -> ApprovalPolicy:
        raw_state_policies = payload.get("state_policies")
        if not isinstance(raw_state_policies, Sequence) or isinstance(raw_state_policies, str | bytes):
            raise ValueError("approval policy must declare ordered `state_policies`")
        return cls(
            policy_version=_require_non_empty_string(
                payload.get("policy_version", "unknown"),
                field_name="policy_version",
            ),
            non_dispatchable_outcome=_require_non_empty_string(
                payload.get("non_dispatchable_outcome", "blocked"),
                field_name="non_dispatchable_outcome",
            ),
            state_policies=tuple(
                ApprovalStatePolicy.from_mapping(entry)
                for entry in raw_state_policies
                if isinstance(entry, Mapping)
            ),
        )

    def policy_for_state(self, approval_state: str) -> ApprovalStatePolicy:
        for state_policy in self.state_policies:
            if state_policy.approval_state == approval_state:
                return state_policy
        raise ValueError(f"approval policy does not define approval_state `{approval_state}`")

    @property
    def dispatchable_states(self) -> tuple[str, ...]:
        return tuple(
            sorted(state.approval_state for state in self.state_policies if state.dispatchable)
        )

    @property
    def autonomous_continuation_states(self) -> tuple[str, ...]:
        return tuple(
            sorted(
                state.approval_state
                for state in self.state_policies
                if state.permits_autonomous_continuation
            )
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "policy_version": self.policy_version,
            "non_dispatchable_outcome": self.non_dispatchable_outcome,
            "dispatchable_states": list(self.dispatchable_states),
            "autonomous_continuation_states": list(self.autonomous_continuation_states),
            "state_policies": [state.to_dict() for state in self.state_policies],
        }


@dataclass(frozen=True)
class RolloutStep:
    sequence: int
    step_id: str
    step_type: str
    enforcement_point: str
    depends_on: tuple[str, ...] = ()

    @classmethod
    def from_mapping(cls, payload: Mapping[str, object]) -> RolloutStep:
        return cls(
            sequence=_require_non_negative_integer(payload.get("sequence"), field_name="sequence"),
            step_id=_require_non_empty_string(payload.get("step_id"), field_name="step_id"),
            step_type=_require_non_empty_string(payload.get("step_type"), field_name="step_type"),
            enforcement_point=_require_non_empty_string(
                payload.get("enforcement_point"),
                field_name="enforcement_point",
            ),
            depends_on=_normalize_string_tuple(payload.get("depends_on"), field_name="depends_on"),
        )

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "sequence": self.sequence,
            "step_id": self.step_id,
            "step_type": self.step_type,
            "enforcement_point": self.enforcement_point,
        }
        if self.depends_on:
            payload["depends_on"] = list(self.depends_on)
        return payload


@dataclass(frozen=True)
class RolloutPolicy:
    policy_version: str
    ordered_steps: tuple[RolloutStep, ...]

    @classmethod
    def from_mapping(cls, payload: Mapping[str, object]) -> RolloutPolicy:
        raw_ordered_steps = payload.get("ordered_steps")
        if not isinstance(raw_ordered_steps, Sequence) or isinstance(raw_ordered_steps, str | bytes):
            raise ValueError("rollout policy must declare ordered `ordered_steps`")
        ordered_steps = tuple(
            sorted(
                (
                    RolloutStep.from_mapping(entry)
                    for entry in raw_ordered_steps
                    if isinstance(entry, Mapping)
                ),
                key=lambda step: (step.sequence, step.step_id),
            )
        )
        return cls(
            policy_version=_require_non_empty_string(
                payload.get("policy_version", "unknown"),
                field_name="policy_version",
            ),
            ordered_steps=ordered_steps,
        )

    @property
    def ordered_step_ids(self) -> tuple[str, ...]:
        return tuple(step.step_id for step in self.ordered_steps)

    @property
    def pre_dispatch_step_ids(self) -> tuple[str, ...]:
        return tuple(
            step.step_id for step in self.ordered_steps if step.enforcement_point == "pre_dispatch"
        )

    @property
    def post_execution_step_ids(self) -> tuple[str, ...]:
        return tuple(
            step.step_id
            for step in self.ordered_steps
            if step.enforcement_point.startswith("post_execution")
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "policy_version": self.policy_version,
            "ordered_step_ids": list(self.ordered_step_ids),
            "pre_dispatch_step_ids": list(self.pre_dispatch_step_ids),
            "post_execution_step_ids": list(self.post_execution_step_ids),
            "ordered_steps": [step.to_dict() for step in self.ordered_steps],
        }


@dataclass(frozen=True)
class TaskSelectionEvaluation:
    task_id: str
    task_name: str
    declared_order: int
    approval_state: str
    approval_dispatchable: bool
    approval_allows_autonomous_continuation: bool
    dependencies_satisfied: bool
    missing_dependencies: tuple[str, ...]
    dependency_unlock_score: float | None
    risk_reduction_score: float | None
    is_completed: bool
    is_blocked: bool
    is_fully_specified: bool
    eligible: bool
    reasons: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "task_id": self.task_id,
            "task_name": self.task_name,
            "declared_order": self.declared_order,
            "approval_state": self.approval_state,
            "approval_dispatchable": self.approval_dispatchable,
            "approval_allows_autonomous_continuation": self.approval_allows_autonomous_continuation,
            "dependencies_satisfied": self.dependencies_satisfied,
            "missing_dependencies": list(self.missing_dependencies),
            "is_completed": self.is_completed,
            "is_blocked": self.is_blocked,
            "is_fully_specified": self.is_fully_specified,
            "eligible": self.eligible,
            "reasons": list(self.reasons),
        }
        if self.dependency_unlock_score is not None:
            payload["dependency_unlock_score"] = self.dependency_unlock_score
        if self.risk_reduction_score is not None:
            payload["risk_reduction_score"] = self.risk_reduction_score
        return payload


@dataclass(frozen=True)
class TaskSelectionDecision:
    result: str
    selected_task: TaskSelectionInput | None
    eligible_task_ids: tuple[str, ...]
    ordered_candidate_task_ids: tuple[str, ...]
    applied_ordering: tuple[str, ...]
    skipped_ordering: tuple[str, ...]
    blocked_reasons: tuple[str, ...]
    fallback_ordering: tuple[str, ...]
    approval_policy: ApprovalPolicy
    rollout_policy: RolloutPolicy
    task_evaluations: tuple[TaskSelectionEvaluation, ...]

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "result": self.result,
            "selected_task_id": self.selected_task.task_id if self.selected_task is not None else None,
            "eligible_task_ids": list(self.eligible_task_ids),
            "ordered_candidate_task_ids": list(self.ordered_candidate_task_ids),
            "applied_ordering": list(self.applied_ordering),
            "skipped_ordering": list(self.skipped_ordering),
            "blocked_reasons": list(self.blocked_reasons),
            "fallback_ordering": list(self.fallback_ordering),
            "approval_policy": self.approval_policy.to_dict(),
            "rollout_policy": self.rollout_policy.to_dict(),
            "task_evaluations": [evaluation.to_dict() for evaluation in self.task_evaluations],
        }
        if self.selected_task is not None:
            payload["selected_task"] = self.selected_task.to_dict()
        return payload


@dataclass(frozen=True)
class ArtifactReference:
    artifact_role: str
    reference: str
    content_digest: str

    @classmethod
    def from_mapping(cls, payload: Mapping[str, object]) -> ArtifactReference:
        return cls(
            artifact_role=_require_non_empty_string(
                payload.get("artifact_role"),
                field_name="artifact_role",
            ),
            reference=_require_non_empty_string(payload.get("reference"), field_name="reference"),
            content_digest=_require_non_empty_string(
                payload.get("content_digest"),
                field_name="content_digest",
            ),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "artifact_role": self.artifact_role,
            "reference": self.reference,
            "content_digest": self.content_digest,
        }


@dataclass(frozen=True)
class PersistedDecisionArtifacts:
    decision_artifact_reference: ArtifactReference
    validator_result_references: tuple[ArtifactReference, ...] = ()
    approval_policy_reference: ArtifactReference | None = None
    input_artifacts: tuple[ArtifactReference, ...] = ()
    evaluated_inputs: tuple[ArtifactReference, ...] = ()

    @classmethod
    def from_mapping(cls, payload: Mapping[str, object]) -> PersistedDecisionArtifacts:
        decision_artifact_reference = payload.get("decision_artifact_reference")
        if not isinstance(decision_artifact_reference, Mapping):
            raise ValueError("decision_artifact_reference must be an object")

        raw_validator_result_references = payload.get("validator_result_references")
        if raw_validator_result_references is None:
            normalized_validator_result_references: tuple[ArtifactReference, ...] = ()
        elif not isinstance(raw_validator_result_references, Sequence) or isinstance(
            raw_validator_result_references,
            str | bytes,
        ):
            raise ValueError("validator_result_references must be an ordered collection")
        else:
            normalized_validator_result_references = tuple(
                ArtifactReference.from_mapping(entry)
                for entry in raw_validator_result_references
                if isinstance(entry, Mapping)
            )

        approval_policy_reference = payload.get("approval_policy_reference")
        if approval_policy_reference is not None and not isinstance(approval_policy_reference, Mapping):
            raise ValueError("approval_policy_reference must be an object when provided")

        raw_input_artifacts = payload.get("input_artifacts")
        if raw_input_artifacts is None:
            normalized_input_artifacts: tuple[ArtifactReference, ...] = ()
        elif not isinstance(raw_input_artifacts, Sequence) or isinstance(
            raw_input_artifacts,
            str | bytes,
        ):
            raise ValueError("input_artifacts must be an ordered collection")
        else:
            normalized_input_artifacts = tuple(
                ArtifactReference.from_mapping(entry)
                for entry in raw_input_artifacts
                if isinstance(entry, Mapping)
            )

        raw_evaluated_inputs = payload.get("evaluated_inputs")
        if raw_evaluated_inputs is None:
            normalized_evaluated_inputs: tuple[ArtifactReference, ...] = ()
        elif not isinstance(raw_evaluated_inputs, Sequence) or isinstance(
            raw_evaluated_inputs,
            str | bytes,
        ):
            raise ValueError("evaluated_inputs must be an ordered collection")
        else:
            normalized_evaluated_inputs = tuple(
                ArtifactReference.from_mapping(entry)
                for entry in raw_evaluated_inputs
                if isinstance(entry, Mapping)
            )

        return cls(
            decision_artifact_reference=ArtifactReference.from_mapping(decision_artifact_reference),
            validator_result_references=normalized_validator_result_references,
            approval_policy_reference=(
                ArtifactReference.from_mapping(approval_policy_reference)
                if isinstance(approval_policy_reference, Mapping)
                else None
            ),
            input_artifacts=normalized_input_artifacts,
            evaluated_inputs=normalized_evaluated_inputs,
        )

    @property
    def replay_input_references(self) -> tuple[ArtifactReference, ...]:
        references: list[ArtifactReference] = []
        if self.approval_policy_reference is not None:
            references.append(self.approval_policy_reference)
        references.extend(self.input_artifacts)
        references.extend(self.evaluated_inputs)
        return tuple(references)

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "decision_artifact_reference": self.decision_artifact_reference.to_dict(),
            "validator_result_references": [
                reference.to_dict() for reference in self.validator_result_references
            ],
        }
        if self.approval_policy_reference is not None:
            payload["approval_policy_reference"] = self.approval_policy_reference.to_dict()
        if self.input_artifacts:
            payload["input_artifacts"] = [
                reference.to_dict() for reference in self.input_artifacts
            ]
        if self.evaluated_inputs:
            payload["evaluated_inputs"] = [
                reference.to_dict() for reference in self.evaluated_inputs
            ]
        return payload


@dataclass(frozen=True)
class GateValidatorResult:
    validator_name: str
    outcome: str
    validation_stage: str | None = None
    result_reference: ArtifactReference | None = None
    summary: str | None = None

    @classmethod
    def from_mapping(cls, payload: Mapping[str, object]) -> GateValidatorResult:
        result_reference = payload.get("result_reference")
        if result_reference is not None and not isinstance(result_reference, Mapping):
            raise ValueError("result_reference must be an object when provided")
        return cls(
            validator_name=_require_non_empty_string(
                payload.get("validator_name"),
                field_name="validator_name",
            ),
            outcome=_require_non_empty_string(payload.get("outcome"), field_name="outcome"),
            validation_stage=_optional_non_empty_string(
                payload.get("validation_stage"),
                field_name="validation_stage",
            ),
            result_reference=(
                ArtifactReference.from_mapping(result_reference)
                if isinstance(result_reference, Mapping)
                else None
            ),
            summary=_optional_non_empty_string(payload.get("summary"), field_name="summary"),
        )

    @property
    def passed(self) -> bool:
        return self.outcome == "pass"

    @property
    def label(self) -> str:
        return self.validation_stage or self.validator_name

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "validator_name": self.validator_name,
            "outcome": self.outcome,
        }
        if self.validation_stage is not None:
            payload["validation_stage"] = self.validation_stage
        if self.result_reference is not None:
            payload["result_reference"] = self.result_reference.to_dict()
        if self.summary is not None:
            payload["summary"] = self.summary
        return payload


@dataclass(frozen=True)
class ContinuationGateDecision:
    gate: str
    task_id: str
    decision: str
    resulting_task_state: str
    validator_results: tuple[GateValidatorResult, ...]
    approval_state: str | None = None
    worker_result_status: str | None = None
    task_record_reference: ArtifactReference | None = None
    delegation_brief_reference: ArtifactReference | None = None
    worker_result_reference: ArtifactReference | None = None
    persisted_artifacts: PersistedDecisionArtifacts | None = None
    blocking_reasons: tuple[str, ...] = ()
    retry_reason: str | None = None
    escalation_reason: str | None = None

    @classmethod
    def from_mapping(
        cls,
        payload: Mapping[str, object],
        *,
        gate: str,
    ) -> ContinuationGateDecision:
        if gate not in {"predispatch", "posttask"}:
            raise ValueError(f"unsupported continuation gate `{gate}`")
        raw_validator_results = payload.get("validator_results")
        if not isinstance(raw_validator_results, Sequence) or isinstance(
            raw_validator_results,
            str | bytes,
        ):
            raise ValueError(f"{gate} decision must declare ordered `validator_results`")
        decision = _require_non_empty_string(payload.get("decision"), field_name="decision")
        allowed_decisions = {
            "predispatch": {"dispatch", "blocked", "escalate"},
            "posttask": {"complete", "blocked", "retry", "escalate"},
        }[gate]
        if decision not in allowed_decisions:
            raise ValueError(f"{gate} decision `{decision}` is not supported")
        task_record_reference = payload.get("task_record_reference")
        if task_record_reference is not None and not isinstance(task_record_reference, Mapping):
            raise ValueError("task_record_reference must be an object when provided")
        delegation_brief_reference = payload.get("delegation_brief_reference")
        if delegation_brief_reference is not None and not isinstance(
            delegation_brief_reference,
            Mapping,
        ):
            raise ValueError("delegation_brief_reference must be an object when provided")
        worker_result_reference = payload.get("worker_result_reference")
        if worker_result_reference is not None and not isinstance(worker_result_reference, Mapping):
            raise ValueError("worker_result_reference must be an object when provided")
        persisted_artifacts = payload.get("persisted_artifacts")
        if persisted_artifacts is not None and not isinstance(persisted_artifacts, Mapping):
            raise ValueError("persisted_artifacts must be an object when provided")
        return cls(
            gate=gate,
            task_id=_require_non_empty_string(payload.get("task_id"), field_name="task_id"),
            decision=decision,
            resulting_task_state=_require_non_empty_string(
                payload.get("resulting_task_state"),
                field_name="resulting_task_state",
            ),
            validator_results=tuple(
                GateValidatorResult.from_mapping(entry)
                for entry in raw_validator_results
                if isinstance(entry, Mapping)
            ),
            approval_state=(
                _require_non_empty_string(payload.get("approval_state"), field_name="approval_state")
                if gate == "predispatch"
                else None
            ),
            worker_result_status=(
                _require_non_empty_string(
                    payload.get("worker_result_status"),
                    field_name="worker_result_status",
                )
                if gate == "posttask"
                else None
            ),
            task_record_reference=(
                ArtifactReference.from_mapping(task_record_reference)
                if isinstance(task_record_reference, Mapping)
                else None
            ),
            delegation_brief_reference=(
                ArtifactReference.from_mapping(delegation_brief_reference)
                if isinstance(delegation_brief_reference, Mapping)
                else None
            ),
            worker_result_reference=(
                ArtifactReference.from_mapping(worker_result_reference)
                if isinstance(worker_result_reference, Mapping)
                else None
            ),
            persisted_artifacts=(
                PersistedDecisionArtifacts.from_mapping(persisted_artifacts)
                if isinstance(persisted_artifacts, Mapping)
                else None
            ),
            blocking_reasons=_normalize_string_tuple(
                payload.get("blocking_reasons"),
                field_name="blocking_reasons",
            ),
            retry_reason=_optional_non_empty_string(
                payload.get("retry_reason"),
                field_name="retry_reason",
            ),
            escalation_reason=_optional_non_empty_string(
                payload.get("escalation_reason"),
                field_name="escalation_reason",
            ),
        )

    @property
    def required_validator_labels(self) -> tuple[str, ...]:
        if self.gate == "predispatch":
            return ("validate-task-brief", "validate-task-order-and-approval")
        return ("worker-result-contract", "validate-task-scope")

    @property
    def missing_required_validators(self) -> tuple[str, ...]:
        seen = {result.validator_name for result in self.validator_results}
        seen.update(
            result.validation_stage for result in self.validator_results if result.validation_stage
        )
        return tuple(
            label for label in self.required_validator_labels if label not in seen
        )

    @property
    def failing_validator_labels(self) -> tuple[str, ...]:
        return tuple(result.label for result in self.validator_results if not result.passed)

    @property
    def decision_artifact_reference(self) -> ArtifactReference | None:
        if self.persisted_artifacts is None:
            return None
        return self.persisted_artifacts.decision_artifact_reference

    @property
    def audit_reason_codes(self) -> tuple[str, ...]:
        reasons: list[str] = [f"{self.gate}_decision:{self.decision}"]
        if self.approval_state is not None:
            reasons.append(f"{self.gate}_approval_state:{self.approval_state}")
        if self.worker_result_status is not None:
            reasons.append(f"{self.gate}_worker_result_status:{self.worker_result_status}")
        reasons.extend(
            f"{self.gate}_required_validator_missing:{validator}"
            for validator in self.missing_required_validators
        )
        reasons.extend(
            f"{self.gate}_validator_failed:{validator}"
            for validator in self.failing_validator_labels
        )
        reasons.extend(f"{self.gate}_blocking_reason:{reason}" for reason in self.blocking_reasons)
        if self.decision in {"dispatch", "complete"} and not self.missing_required_validators:
            if not self.failing_validator_labels and not self.blocking_reasons:
                reasons.append(f"{self.gate}_required_validators_passed")
        if self.retry_reason is not None:
            reasons.append(f"{self.gate}_retry_reason:{self.retry_reason}")
        if self.escalation_reason is not None:
            reasons.append(f"{self.gate}_escalation_reason:{self.escalation_reason}")
        return _dedupe_string_tuple(reasons)

    def explanation(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "gate": self.gate,
            "task_id": self.task_id,
            "decision": self.decision,
            "resulting_task_state": self.resulting_task_state,
            "reason_codes": list(self.audit_reason_codes),
            "missing_required_validators": list(self.missing_required_validators),
            "failing_validator_labels": list(self.failing_validator_labels),
        }
        if self.decision_artifact_reference is not None:
            payload["decision_artifact_reference"] = self.decision_artifact_reference.to_dict()
        return payload

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "gate": self.gate,
            "task_id": self.task_id,
            "decision": self.decision,
            "resulting_task_state": self.resulting_task_state,
            "validator_results": [result.to_dict() for result in self.validator_results],
            "missing_required_validators": list(self.missing_required_validators),
            "failing_validator_labels": list(self.failing_validator_labels),
            "explanation": self.explanation(),
        }
        if self.approval_state is not None:
            payload["approval_state"] = self.approval_state
        if self.worker_result_status is not None:
            payload["worker_result_status"] = self.worker_result_status
        if self.task_record_reference is not None:
            payload["task_record_reference"] = self.task_record_reference.to_dict()
        if self.delegation_brief_reference is not None:
            payload["delegation_brief_reference"] = self.delegation_brief_reference.to_dict()
        if self.worker_result_reference is not None:
            payload["worker_result_reference"] = self.worker_result_reference.to_dict()
        if self.persisted_artifacts is not None:
            payload["persisted_artifacts"] = self.persisted_artifacts.to_dict()
        if self.blocking_reasons:
            payload["blocking_reasons"] = list(self.blocking_reasons)
        if self.retry_reason is not None:
            payload["retry_reason"] = self.retry_reason
        if self.escalation_reason is not None:
            payload["escalation_reason"] = self.escalation_reason
        return payload


def _task_sort_key(task: TaskSelectionInput) -> tuple[int, str]:
    return (task.declared_order, task.task_id)


@dataclass(frozen=True)
class TaskOutcome:
    task_id: str
    resulting_task_state: str
    decision: str | None = None
    source_gate: str | None = None
    decision_artifact_reference: ArtifactReference | None = None
    worker_result_reference: ArtifactReference | None = None
    worker_result_status: str | None = None

    @classmethod
    def from_mapping(cls, payload: Mapping[str, object]) -> TaskOutcome:
        decision_artifact_reference = payload.get("decision_artifact_reference")
        if decision_artifact_reference is not None and not isinstance(
            decision_artifact_reference,
            Mapping,
        ):
            raise ValueError("decision_artifact_reference must be an object when provided")
        worker_result_reference = payload.get("worker_result_reference")
        if worker_result_reference is not None and not isinstance(worker_result_reference, Mapping):
            raise ValueError("worker_result_reference must be an object when provided")
        return cls(
            task_id=_require_non_empty_string(payload.get("task_id"), field_name="task_id"),
            resulting_task_state=_require_non_empty_string(
                payload.get("resulting_task_state"),
                field_name="resulting_task_state",
            ),
            decision=_optional_non_empty_string(payload.get("decision"), field_name="decision"),
            source_gate=_optional_non_empty_string(
                payload.get("source_gate"),
                field_name="source_gate",
            ),
            decision_artifact_reference=(
                ArtifactReference.from_mapping(decision_artifact_reference)
                if isinstance(decision_artifact_reference, Mapping)
                else None
            ),
            worker_result_reference=(
                ArtifactReference.from_mapping(worker_result_reference)
                if isinstance(worker_result_reference, Mapping)
                else None
            ),
            worker_result_status=_optional_non_empty_string(
                payload.get("worker_result_status"),
                field_name="worker_result_status",
            ),
        )

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "task_id": self.task_id,
            "resulting_task_state": self.resulting_task_state,
        }
        if self.decision is not None:
            payload["decision"] = self.decision
        if self.source_gate is not None:
            payload["source_gate"] = self.source_gate
        if self.decision_artifact_reference is not None:
            payload["decision_artifact_reference"] = self.decision_artifact_reference.to_dict()
        if self.worker_result_reference is not None:
            payload["worker_result_reference"] = self.worker_result_reference.to_dict()
        if self.worker_result_status is not None:
            payload["worker_result_status"] = self.worker_result_status
        return payload


@dataclass(frozen=True)
class ReplayResumeInput:
    task_outcomes: tuple[TaskOutcome, ...] = ()
    predispatch_decision: ContinuationGateDecision | None = None
    posttask_decision: ContinuationGateDecision | None = None

    @classmethod
    def from_mapping(cls, payload: Mapping[str, object]) -> ReplayResumeInput:
        raw_task_outcomes = payload.get("task_outcomes")
        if raw_task_outcomes is None:
            normalized_task_outcomes: tuple[TaskOutcome, ...] = ()
        elif not isinstance(raw_task_outcomes, Sequence) or isinstance(
            raw_task_outcomes,
            str | bytes,
        ):
            raise ValueError("task_outcomes must be an ordered collection when provided")
        else:
            normalized_task_outcomes = tuple(
                TaskOutcome.from_mapping(entry)
                for entry in raw_task_outcomes
                if isinstance(entry, Mapping)
            )

        predispatch_decision = payload.get("predispatch_decision")
        if predispatch_decision is not None and not isinstance(predispatch_decision, Mapping):
            raise ValueError("predispatch_decision must be an object when provided")
        posttask_decision = payload.get("posttask_decision")
        if posttask_decision is not None and not isinstance(posttask_decision, Mapping):
            raise ValueError("posttask_decision must be an object when provided")

        return cls(
            task_outcomes=normalized_task_outcomes,
            predispatch_decision=(
                ContinuationGateDecision.from_mapping(predispatch_decision, gate="predispatch")
                if isinstance(predispatch_decision, Mapping)
                else None
            ),
            posttask_decision=(
                ContinuationGateDecision.from_mapping(posttask_decision, gate="posttask")
                if isinstance(posttask_decision, Mapping)
                else None
            ),
        )

    @property
    def decision_artifact_references(self) -> tuple[ArtifactReference, ...]:
        references: list[ArtifactReference] = []
        for decision in (self.predispatch_decision, self.posttask_decision):
            if decision is None or decision.decision_artifact_reference is None:
                continue
            references.append(decision.decision_artifact_reference)
        return tuple(references)

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "task_outcomes": [outcome.to_dict() for outcome in self.task_outcomes],
        }
        if self.predispatch_decision is not None:
            payload["predispatch_decision"] = self.predispatch_decision.to_dict()
        if self.posttask_decision is not None:
            payload["posttask_decision"] = self.posttask_decision.to_dict()
        if self.decision_artifact_references:
            payload["decision_artifact_references"] = [
                reference.to_dict() for reference in self.decision_artifact_references
            ]
        return payload


@dataclass(frozen=True)
class ContinuationDecision:
    result: str
    continue_automatically: bool
    next_task_id: str | None
    stop_reasons: tuple[str, ...] = ()
    retry_reason: str | None = None
    escalation_reason: str | None = None
    selection_decision: TaskSelectionDecision | None = None
    predispatch_decision: ContinuationGateDecision | None = None
    posttask_decision: ContinuationGateDecision | None = None
    approval_policy: ApprovalPolicy | None = None
    rollout_policy: RolloutPolicy | None = None
    replay_resume_input: ReplayResumeInput | None = None

    def explanation(self) -> dict[str, object]:
        reason_codes: list[str] = [f"continuation_result:{self.result}"]
        if self.selection_decision is not None:
            reason_codes.append(f"selection_result:{self.selection_decision.result}")
            if self.selection_decision.selected_task is not None:
                reason_codes.append(
                    f"selection_selected_task:{self.selection_decision.selected_task.task_id}"
                )
                reason_codes.append(
                    "selection_selected_task_approval_state:"
                    f"{self.selection_decision.selected_task.approval_state}"
                )
        if self.predispatch_decision is not None:
            reason_codes.append(f"predispatch_decision:{self.predispatch_decision.decision}")
        if self.posttask_decision is not None:
            reason_codes.append(f"posttask_decision:{self.posttask_decision.decision}")
        if self.result == "continue":
            reason_codes.extend(
                (
                    "continuation_ready_for_dispatch",
                    "continuation_posttask_complete",
                    "continuation_predispatch_dispatch",
                )
            )
        reason_codes.extend(self.stop_reasons)
        if self.retry_reason is not None:
            reason_codes.append(f"continuation_retry_reason:{self.retry_reason}")
        if self.escalation_reason is not None:
            reason_codes.append(f"continuation_escalation_reason:{self.escalation_reason}")

        payload: dict[str, object] = {
            "result": self.result,
            "continue_automatically": self.continue_automatically,
            "next_task_id": self.next_task_id,
            "reason_codes": list(_dedupe_string_tuple(reason_codes)),
            "stop_reasons": list(self.stop_reasons),
        }
        if self.selection_decision is not None and self.selection_decision.selected_task is not None:
            payload["selected_task_id"] = self.selection_decision.selected_task.task_id
        if self.predispatch_decision is not None:
            payload["predispatch"] = self.predispatch_decision.explanation()
        if self.posttask_decision is not None:
            payload["posttask"] = self.posttask_decision.explanation()
        return payload

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "result": self.result,
            "continue_automatically": self.continue_automatically,
            "next_task_id": self.next_task_id,
            "stop_reasons": list(self.stop_reasons),
            "explanation": self.explanation(),
        }
        if self.retry_reason is not None:
            payload["retry_reason"] = self.retry_reason
        if self.escalation_reason is not None:
            payload["escalation_reason"] = self.escalation_reason
        if self.selection_decision is not None:
            payload["selection_decision"] = self.selection_decision.to_dict()
        if self.predispatch_decision is not None:
            payload["predispatch_decision"] = self.predispatch_decision.to_dict()
        if self.posttask_decision is not None:
            payload["posttask_decision"] = self.posttask_decision.to_dict()
        if self.approval_policy is not None:
            payload["approval_policy"] = self.approval_policy.to_dict()
        if self.rollout_policy is not None:
            payload["rollout_policy"] = self.rollout_policy.to_dict()
        if self.replay_resume_input is not None:
            payload["replay_resume_input"] = self.replay_resume_input.to_dict()
        return payload


@dataclass(frozen=True)
class WorkflowRequest:
    task_name: str
    backend: str
    output_dir: str
    contract: str
    operation_class: str
    cycle_root: str
    selection_context: TaskSelectionContext | None = None
    selection_decision: TaskSelectionDecision | None = None
    predispatch_decision: ContinuationGateDecision | None = None
    posttask_decision: ContinuationGateDecision | None = None
    continuation_decision: ContinuationDecision | None = None
    replay_resume_input: ReplayResumeInput | None = None


@dataclass(frozen=True)
class WorkflowPlan:
    task_name: str
    backend: str
    output_dir: str
    contract: str
    operation_class: str
    cycle_root: str
    intent: str = "execution_only"
    delegation_mode: str = "codex_worker"
    selection_context: TaskSelectionContext | None = None
    selection_decision: TaskSelectionDecision | None = None
    predispatch_decision: ContinuationGateDecision | None = None
    posttask_decision: ContinuationGateDecision | None = None
    continuation_decision: ContinuationDecision | None = None
    replay_resume_input: ReplayResumeInput | None = None

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "task_name": self.task_name,
            "backend": self.backend,
            "output_dir": self.output_dir,
            "contract": self.contract,
            "operation_class": self.operation_class,
            "cycle_root": self.cycle_root,
            "intent": self.intent,
            "delegation_mode": self.delegation_mode,
        }
        if self.selection_context is not None:
            payload["selection_context"] = self.selection_context.to_dict()
        if self.selection_decision is not None:
            payload["selection_decision"] = self.selection_decision.to_dict()
        if self.predispatch_decision is not None:
            payload["predispatch_decision"] = self.predispatch_decision.to_dict()
        if self.posttask_decision is not None:
            payload["posttask_decision"] = self.posttask_decision.to_dict()
        if self.continuation_decision is not None:
            payload["continuation_decision"] = self.continuation_decision.to_dict()
        if self.replay_resume_input is not None:
            payload["replay_resume_input"] = self.replay_resume_input.to_dict()
        return payload
