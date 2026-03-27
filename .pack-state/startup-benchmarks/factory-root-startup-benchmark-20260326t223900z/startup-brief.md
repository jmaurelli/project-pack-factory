# Factory-Root Startup Benchmark Brief

Generated from canonical startup surfaces on March 26, 2026.

## What Matters Most Now
release-evidence-summarizer-build-pack-v3 is the live path in production.

## Canonical Factory State
- High priority: release-evidence-summarizer-build-pack-v3
- Medium priority: factory-native-smoke-build-pack, json-health-checker-build-pack, config-drift-checker-build-pack, json-health-checker-promotion-gate-build-pack-v1, json-health-checker-one-pass-promotion-proof-build-pack-v1, json-health-checker-autonomy-to-promotion-build-pack-v1
- Worth watching: release-evidence-summarizer-build-pack, api-contract-sentinel-build-pack, release-evidence-summarizer-build-pack-v2, release-evidence-summarizer-build-pack-v4, json-health-checker-live-roundtrip-build-pack-v1, json-health-checker-memory-resume-build-pack-v1, json-health-checker-memory-resume-build-pack-v2, json-health-checker-resume-correctness-build-pack-v1, json-health-checker-unified-memory-resume-build-pack-v1, json-health-checker-resume-success-build-pack-v1, algosec-diagnostic-framework-build-pack-v1, json-health-checker-feedback-baseline-build-pack-v1, json-health-checker-active-task-continuity-build-pack-v1, json-health-checker-multi-hop-autonomy-build-pack-v1, json-health-checker-memory-block-reporting-build-pack-v1, json-health-checker-block-reporting-build-pack-v1, json-health-checker-drift-exercise-build-pack-v1, json-health-checker-longer-backlog-build-pack-v4, json-health-checker-branching-build-pack-v1, json-health-checker-degraded-connectivity-build-pack-v1, json-health-checker-ambiguous-branch-build-pack-v2, json-health-checker-semantic-branch-build-pack-v1, json-health-checker-operator-hint-branch-build-pack-v1, json-health-checker-operator-avoid-branch-build-pack-v1, json-health-checker-operator-avoid-branch-build-pack-v2, json-health-checker-operator-hint-conflict-build-pack-v1, json-health-checker-ordered-hint-lifecycle-build-pack-v1, json-health-checker-hint-audit-cleanup-build-pack-v1, json-health-checker-hint-audit-cleanup-build-pack-v2, json-health-checker-hint-audit-cleanup-build-pack-v3, json-health-checker-hint-status-surfacing-build-pack-v1, json-health-checker-hint-status-surfacing-build-pack-v2, json-health-checker-hint-briefing-build-pack-v1, json-health-checker-startup-compliance-build-pack-v1, json-health-checker-startup-compliance-rehearsal-build-pack-v1, config-drift-autonomy-transfer-build-pack-v1, release-evidence-autonomy-transfer-build-pack-v1, api-contract-autonomy-transfer-build-pack-v1, json-health-checker-adversarial-restart-build-pack-v1, json-health-checker-adversarial-restart-conflicting-memory-build-pack-v1
- Historical baseline: ai-native-codex-build-pack, agent-memory-first-build-pack, json-health-checker-one-pass-promotion-build-pack-v1, json-health-checker-longer-backlog-build-pack-v1, json-health-checker-longer-backlog-build-pack-v2, json-health-checker-longer-backlog-build-pack-v3
- Live now: release-evidence-summarizer-build-pack-v3
- Testing now: json-health-checker-autonomy-to-promotion-build-pack-v1
- Ready but unassigned: factory-native-smoke-build-pack, json-health-checker-build-pack, config-drift-checker-build-pack, json-health-checker-promotion-gate-build-pack-v1, json-health-checker-one-pass-promotion-proof-build-pack-v1

## Agent Memory
- Current focus: Track PackFactory root work through canonical objective, backlog, and work-state files., Advance the top-priority operator dashboard so it becomes the fast normal briefing surface for PackFactory state., Define and adopt the build-pack source-of-truth mode so local and remote-managed lines do not behave like competing primaries.
- Next action items: Advance the top-priority operator dashboard so it becomes the fast normal briefing surface for PackFactory state., Define and adopt the build-pack source-of-truth mode so local and remote-managed lines do not behave like competing primaries., Design the optional agent-personality template system as a reusable overlay rather than a one-template identity lock-in.
- Pending items: Advance the top-priority operator dashboard so it becomes the fast normal briefing surface for PackFactory state., Define and adopt the build-pack source-of-truth mode so local and remote-managed lines do not behave like competing primaries., Design the optional agent-personality template system as a reusable overlay rather than a one-template identity lock-in., Review and optimize PackFactory instruction surfaces for scan speed, retention, and startup compliance.
- Overdue items: none recorded
- Blockers: Autonomy is strongest in bounded PackFactory workflows, not broad unscripted project work., Advance the top-priority operator dashboard so it becomes the fast normal briefing surface for PackFactory state.
- Latest autonomy proof: Latest autonomy proof includes a completed multi-hop rehearsal and a promotion-backed follow-through: .pack-state/multi-hop-autonomy-rehearsals/multi-hop-autonomy-rehearsal-api-contract-autonomy-transfer-build-pack-v1-20260325t231545z/rehearsal-report.json; eval/history/promote-json-health-checker-autonomy-to-promotion-build-pack-v1-testing-20260325t173309z/promotion-report.json.
- Recommended next step: Advance the top-priority operator dashboard so it becomes the fast normal briefing surface for PackFactory state.

## Recent Motion
- 2026-03-25 22:45:50Z: `materialized` `config-drift-autonomy-transfer-build-pack-v1`.
- 2026-03-25 23:15:44Z: `materialized` `release-evidence-autonomy-transfer-build-pack-v1`.
- 2026-03-25 23:15:45Z: `materialized` `api-contract-autonomy-transfer-build-pack-v1`.
- 2026-03-26 12:02:33Z: `materialized` `json-health-checker-adversarial-restart-build-pack-v1`.
- 2026-03-26 12:02:34Z: `materialized` `json-health-checker-adversarial-restart-conflicting-memory-build-pack-v1`.

## Practical Next Steps
- Review the current startup benchmark score and close any weak dimension before changing the startup contract again.
- Expand the cross-template transfer proof beyond config drift so the autonomy baseline is not treated as JSON-health-only.
- Use the latest root memory as restart context, but keep registry, deployment, readiness, and promotion state as the truth layer.
