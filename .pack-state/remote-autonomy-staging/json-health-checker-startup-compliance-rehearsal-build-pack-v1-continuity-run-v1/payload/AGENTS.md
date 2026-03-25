# JSON Health Checker Startup Compliance Rehearsal Build Pack Build Pack Agent Context

This directory is a PackFactory build pack, not a source template.

Read `status/lifecycle.json`, `status/readiness.json`, and `status/deployment.json` first.
If `status/readiness.json.operator_hint_status` exists, surface it in your pack-level startup or continuation briefing before going deeper so active, exhausted, cleanup-candidate, and recently consumed operator hints are visible immediately.
Then read `pack.json` and use `pack.json.post_bootstrap_read_order` as the canonical post-bootstrap traversal contract.
When `pack.json.directory_contract` declares `contracts/project-objective.json`, `tasks/active-backlog.json`, or `status/work-state.json`, read those files as canonical pack-local control-plane handoff files.
Treat `status/work-state.json.branch_selection_hints` as the canonical operator-guidance source even when readiness has not been refreshed yet, and surface any active, exhausted, or cleanup-relevant hint state during pack entry when it matters.
Treat `project-context.md` as inherited background context unless the manifest and status files say otherwise.
When present, inspect `.pack-state/agent-memory/latest-memory.json` first, then treat other `.pack-state/agent-memory/*.json` files as supplementary restart memory distilled from prior autonomy runs.

This build pack can export bounded runtime evidence when running externally.
Use `pack.json.entrypoints.export_runtime_evidence_command` when that capability is present.
For workflow or remote-session compliance questions, return to the factory root and read `AGENTS.md` plus `docs/specs/project-pack-factory/PROJECT-PACK-FACTORY-AUTONOMY-OPERATIONS-NOTE.md` before inventing a pack-local alternative.
From the factory root, use `python3 tools/run_multi_hop_autonomy_rehearsal.py ...` when you want a single fresh-pack rehearsal that materializes a proving ground, checkpoints mid-backlog memory, runs the remote continuity hops, reconciles canonical state, and verifies the ready-boundary loop end to end.
From the factory root, use `python3 tools/run_local_mid_backlog_checkpoint.py ...` when you want to stop after the current active task, write local feedback memory, and activate a resumable mid-backlog handoff pointer.
From the factory root, use `python3 tools/run_remote_active_task_continuity_test.py ...` when the pack is already at a compatible active-task boundary and you want to verify the next task resumes remotely from feedback memory.
From the factory root, use `python3 tools/run_remote_memory_continuity_test.py ...` after the pack reaches `ready_for_deploy` and `.pack-state/agent-memory/latest-memory.json` is active if you want to verify default feedback-memory continuity on a remote target.
For remote Codex session management, use the PackFactory-local workflows from the factory root. Do not improvise ad hoc `ssh` prompts, handcrafted remote-session runners, or raw stdout/stderr logging loops when an official PackFactory workflow exists for the same job.
When multiple next tasks are eligible, prefer lower `selection_priority` first. If the top candidates remain tied, honor any operator branch-selection hints recorded in `status/work-state.json.branch_selection_hints` in canonical hint order: apply active avoid-task guidance first so it can narrow the tied set safely, then apply active preferred-task guidance within the remaining tied set, then use bounded semantic alignment to `contracts/project-objective.json`, `status/work-state.json.resume_instructions`, and optional task `selection_signals`; otherwise stop fail-closed for operator review. Hints may also declare `remaining_applications` when they should expire automatically after bounded use.
From the factory root, use `python3 tools/audit_branch_selection_hints.py ...` when you need one bounded view of active, exhausted, and cleanup-candidate hints plus recent consumed/deactivated hint evidence.
Export bounded runtime evidence from the pack when needed, but import it only from the factory root through `python3 tools/import_external_runtime_evidence.py ...` or a higher-level PackFactory workflow that wraps that import.
For newly materialized build-packs, promotion readiness also expects one completed `run_multi_hop_autonomy_rehearsal.py` report that still matches the pack's current readiness, work-state, and latest-memory pointer.
Export bundles remain supplementary runtime evidence only, and raw remote stdout/stderr is supplementary debugging rather than canonical PackFactory evidence.

Derived from template `json-health-checker-template-pack`.
Pack id: `json-health-checker-startup-compliance-rehearsal-build-pack-v1`.
