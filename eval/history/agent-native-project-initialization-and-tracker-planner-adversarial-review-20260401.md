# Agent-Native Project Initialization And Tracker/Planner Adversarial Review

Date: 2026-04-01

## Review Scope

Reviewed:

- [PROJECT-PACK-FACTORY-AGENT-NATIVE-PROJECT-INITIALIZATION-TECH-SPEC.md](/home/orchadmin/project-pack-factory/docs/specs/project-pack-factory/PROJECT-PACK-FACTORY-AGENT-NATIVE-PROJECT-INITIALIZATION-TECH-SPEC.md)
- [PROJECT-PACK-FACTORY-TASK-TRACKER-AND-PLANNER-FORMALIZATION-TECH-SPEC.md](/home/orchadmin/project-pack-factory/docs/specs/project-pack-factory/PROJECT-PACK-FACTORY-TASK-TRACKER-AND-PLANNER-FORMALIZATION-TECH-SPEC.md)
- [PROJECT-PACK-FACTORY-AUTONOMY-PLANNING-LIST.md](/home/orchadmin/project-pack-factory/docs/specs/project-pack-factory/PROJECT-PACK-FACTORY-AUTONOMY-PLANNING-LIST.md)
- [tasks/active-backlog.json](/home/orchadmin/project-pack-factory/tasks/active-backlog.json)
- [status/work-state.json](/home/orchadmin/project-pack-factory/status/work-state.json)

## Main Findings

1. The agent-native spec could still be read as a runtime subsystem because the
   profile shape is concrete enough to look executable. V1 needed explicit
   declaration-only language and a reminder that the profile is optional.
2. The agent-native spec’s startup-surface language needed a stronger
   "do not repeat the tracker" boundary so generated docs stay short and do
   not become a shadow control plane.
3. The tracker/planner spec needed to keep `advisory_planning_context`
   optional and absent by default when there is no bounded planning summary,
   otherwise it risks becoming a placeholder document.
4. Task provenance needed to stay diagnostic only. If it looks like execution
   metadata, it could be misused as a routing signal, so the spec had to say it
   does not affect next-task selection or execution authority.
5. The root planning surfaces needed matching tracker entries so the docs did
   not describe an initiative that the backlog and work-state failed to record.

## Tightenings Applied

- added declaration-only wording to the agent-native spec
- kept the generated startup section short and tracker-centric
- narrowed the tracker/planner spec so advisory context stays optional and
  bounded
- marked planner provenance as non-authoritative metadata only
- recorded the matching root planner tasks in backlog and work-state

## Outcome

The v1 model is now cleanly bounded:

- agent-native initialization is a declared profile, not a new runtime plane
- planning remains advisory context around the canonical tracker
- the root tracker reflects the initiative explicitly instead of relying on
  chat memory
