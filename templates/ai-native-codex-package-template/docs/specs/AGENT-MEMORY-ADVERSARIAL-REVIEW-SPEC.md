# Agent Memory Adversarial Review Spec

## Purpose

Convert the initial local agent-memory implementation into a restart-optimized
state surface for future agents.

This review treats agent memory as an agent-facing restart-state surface, not a
human-facing note system.

The core question is:

- can a future agent reconstruct its environment, history, and current goal path
  from memory without re-inferring them from prose?

## Review Inputs

- local code review of the current memory implementation
- adversarial review focused on environment understanding
- adversarial review focused on goal alignment

## Synthesis

The current implementation is useful as prioritized local notes, but it is not
yet strong enough as agent restart state.

It prioritizes summaries, actions, and files, but it still forces a future
agent to infer too much about:

- the environment it is operating in
- the authoritative task/goal contract it should follow
- the history lineage of a memory item
- whether a memory item is fresh, superseded, or conflicting

## Findings

### F1. Critical: Memory artifacts are note-shaped instead of state-shaped

Current memory artifacts store:

- `summary`
- `details`
- `next_actions`
- `file_paths`
- `evidence_paths`

That is insufficient for agent restart optimization because goal state,
validation state, and environment anchors are still implicit in prose.

Required remediation:

- add structured `goal_state`
- add structured `environment_context`
- add structured `history_context`

### F2. Critical: The reader snapshot does not expose enough environment context

The current reader returns `project_root`, counts, cards, and summaries, but it
does not expose machine-usable environment surfaces such as:

- pack memory root
- task-goal telemetry root
- run-manifest root
- operating roots referenced by memory
- task-record paths
- delegation-brief paths
- prioritized evidence paths to inspect next

Required remediation:

- add a structured `environment_context` section to the reader payload
- promote inspection surfaces into an explicit `inspect_next` list

### F3. Critical: History continuity is lossy

Reusing the same `memory_id` silently overwrites prior state.

That breaks agent continuity because the next agent can lose the exact memory
state that explained why work was paused or redirected.

Required remediation:

- fail closed on duplicate `memory_id`
- add lineage via `supersedes_memory_id`
- preserve prior artifacts instead of replacing them in place

### F4. High: Goal alignment remains implicit

The next agent cannot directly read:

- the current objective
- the completion signals
- the primary validation command
- the recommended next command
- blocker dependencies

Required remediation:

- add structured goal fields to each memory artifact
- aggregate those fields into a reader-level `restart_state`

### F5. High: Reader ranking can mislead execution

The current ranking favors memory type before importance.

That can bury a critical goal or decision under lower-importance blockers.

Required remediation:

- rank active memories by importance before type
- retain type-based grouping in the reader summary

### F6. High: Handoff summaries lose provenance

The current handoff summary collapses many items into plain strings.

That removes the machine-usable path back to:

- the source memory artifact
- the relevant files
- the supporting evidence

Required remediation:

- surface structured handoff items with `memory_id`, `source_path`,
  `file_paths`, and `evidence_paths`
- keep compact strings only as a secondary convenience layer

### F7. Medium: Navigation context is truncated too early

The current reader computes several handoff surfaces from the top-N prioritized
memories only.

That can hide still-relevant files and evidence from active memory outside the
selected limit.

Required remediation:

- compute navigation-oriented surfaces from all active memories
- expose truncation metadata for prioritized card selection

### F8. Medium: Freshness and timestamp guarantees are too weak

The current schema allows non-empty `generated_at` strings, but read-time logic
expects parseable timestamps.

Required remediation:

- enforce an ISO-style timestamp pattern in schema
- revalidate timestamps during load
- surface freshness warnings when superseded or contradictory memories remain
  active

## Required Implementation Scope

### Artifact Contract Changes

Add structured fields to each memory artifact:

- `goal_state`
  - `goal`
  - `completion_signals`
  - `primary_validation_command`
  - `recommended_next_command`
  - `blocked_by`
  - `goal_artifact_paths`
- `environment_context`
  - `operating_root`
  - `task_record_path`
  - `delegation_brief_path`
  - `build_run_manifest_path`
  - `task_goal_telemetry_path`
  - `project_context_references`
  - `relevant_commands`
  - `recommended_read_order`
- `history_context`
  - `supersedes_memory_id`
  - `conflicts_with`
  - `confidence`

### Reader Contract Changes

Add structured reader sections:

- `environment_context`
  - resolved memory root
  - referenced operating roots
  - referenced task-record paths
  - referenced delegation-brief paths
  - referenced project-context, telemetry, and run-manifest paths
- `restart_state`
  - active objectives
  - completion signals
  - primary validation commands
  - recommended next commands
- `history_warnings`
  - superseded memories
  - active lineage warnings
  - contradiction warnings when active memories disagree on key goal fields

Update handoff items to be structured and provenance-preserving.

### CLI Changes

Update `record-agent-memory` so it can write the new structured fields.

It must:

- fail on duplicate `memory_id`
- support `--replace-existing` for explicit archive-and-rewrite flows
- support `--supersedes-memory-id`
- accept goal, environment, and history fields as explicit CLI inputs, including task record, delegation brief, telemetry, run-manifest, completion signals, blocked-by, and lineage confidence

Update `read-agent-memory` so it returns the richer environment/goal/history
sections.

## Validation Requirements

The updated implementation must add or revise tests for:

- duplicate-memory-id rejection
- structured goal context persistence and retrieval
- structured environment context persistence and retrieval
- supersession lineage visibility
- importance-first ranking over type-first ranking
- handoff provenance preservation
- navigation surfaces computed from all active memories
- timestamp validation at read time

## Delivery Notes

This remediation is intentionally agent-first.

The target outcome is not “better readable notes.”

The target outcome is:

- lower restart ambiguity
- less re-inference from prose
- stronger environment reconstruction
- stronger history continuity
- clearer goal path for the next agent
