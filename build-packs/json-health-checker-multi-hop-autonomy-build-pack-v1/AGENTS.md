# JSON Health Checker Multi Hop Autonomy Build Pack V1 Build Pack Agent Context

This directory is a PackFactory build pack, not a source template.

Read `status/lifecycle.json`, `status/readiness.json`, and `status/deployment.json` first.
Then read `pack.json` and use `pack.json.post_bootstrap_read_order` as the canonical post-bootstrap traversal contract.
When `pack.json.directory_contract` declares `contracts/project-objective.json`, `tasks/active-backlog.json`, or `status/work-state.json`, read those files as canonical pack-local control-plane handoff files.
Treat `project-context.md` as inherited background context unless the manifest and status files say otherwise.
When present, inspect `.pack-state/agent-memory/latest-memory.json` first, then treat other `.pack-state/agent-memory/*.json` files as supplementary restart memory distilled from prior autonomy runs.

This build pack can export bounded runtime evidence when running externally.
Use `pack.json.entrypoints.export_runtime_evidence_command` when that capability is present.
From the factory root, use `python3 tools/run_multi_hop_autonomy_rehearsal.py ...` when you want a single fresh-pack rehearsal that materializes a proving ground, checkpoints mid-backlog memory, runs the remote continuity hops, reconciles canonical state, and verifies the ready-boundary loop end to end.
From the factory root, use `python3 tools/run_local_mid_backlog_checkpoint.py ...` when you want to stop after the current active task, write local feedback memory, and activate a resumable mid-backlog handoff pointer.
From the factory root, use `python3 tools/run_remote_active_task_continuity_test.py ...` when the pack is already at a compatible active-task boundary and you want to verify the next task resumes remotely from feedback memory.
From the factory root, use `python3 tools/run_remote_memory_continuity_test.py ...` after the pack reaches `ready_for_deploy` and `.pack-state/agent-memory/latest-memory.json` is active if you want to verify default feedback-memory continuity on a remote target.
Export bundles remain supplementary runtime evidence only.

Derived from template `json-health-checker-template-pack`.
Pack id: `json-health-checker-multi-hop-autonomy-build-pack-v1`.
