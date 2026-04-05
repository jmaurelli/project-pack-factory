# Project Pack Factory Backup And Git Strategy Tech Spec

## Purpose

Define the PackFactory root strategy for:

- what belongs in git as the primary recovery path
- what needs separate host-local or external backup
- what should remain transient and disposable
- how to restore each class of state after loss, corruption, or an unsafe local experiment

This spec is adjacent to:

- [PROJECT-PACK-FACTORY-TRANSIENT-LOCAL-SCRATCH-ROOT-AND-STAGING-LIFECYCLE-TECH-SPEC.md](/home/orchadmin/project-pack-factory/docs/specs/project-pack-factory/PROJECT-PACK-FACTORY-TRANSIENT-LOCAL-SCRATCH-ROOT-AND-STAGING-LIFECYCLE-TECH-SPEC.md)
- [PROJECT-PACK-FACTORY-AUTONOMY-OPERATIONS-NOTE.md](/home/orchadmin/project-pack-factory/docs/specs/project-pack-factory/PROJECT-PACK-FACTORY-AUTONOMY-OPERATIONS-NOTE.md)
- [PROJECT-PACK-FACTORY-AUTONOMY-STATE-BRIEF.md](/home/orchadmin/project-pack-factory/docs/specs/project-pack-factory/PROJECT-PACK-FACTORY-AUTONOMY-STATE-BRIEF.md)

## Why This Matters

PackFactory now carries several kinds of state at once:

- canonical repo truth such as registry entries, pack control-plane files, and specs
- preserved evidence and operator briefing layers under `.pack-state/`
- host-local operational prerequisites such as remote access setup
- transient scratch and runtime payloads that should not be treated like durable history

Without an explicit strategy, git can become either too weak or too broad:

- too weak if canonical state is left uncommitted or unpushed
- too broad if transient scratch, staged payloads, or large rebuildable runtimes are treated like first-class recovery artifacts

PackFactory needs one bounded rule set so operators know what to commit, what
to back up separately, and what to let die.

## Decision

PackFactory should use a three-class model:

1. `git_primary`
   Use git as the main preservation and restore path for canonical repo truth
   and small preserved evidence that the repo intentionally keeps.
2. `separate_backup`
   Back up host-local operator state that PackFactory depends on operationally
   but does not fully own or should not reconstruct from repo history alone.
3. `transient_disposable`
   Do not treat scratch, staged payloads, caches, or runtime downloads as
   backup targets unless an operator intentionally copies a specific artifact
   out for durable retention first.

## State Classification

### 1. `git_primary`

These surfaces belong in normal git history and should be pushed to the
authoritative remote after meaningful changes:

- root control-plane files:
  `contracts/project-objective.json`, `tasks/active-backlog.json`,
  `status/work-state.json`
- factory registry and deployment board:
  `registry/`, `deployments/`
- source templates and build-pack trees that are intentionally preserved in the
  repo:
  `templates/`, `build-packs/`
- factory docs, specs, tools, and schemas:
  `AGENTS.md`, `README.md`, `docs/specs/project-pack-factory/`, `tools/`
- preserved evaluation notes and history that the repo intentionally keeps:
  `eval/history/` and pack-local `eval/history/`
- small `.pack-state/` artifacts that function as preserved evidence or current
  operator briefing surfaces rather than scratch:
  `.pack-state/agent-memory/`,
  `.pack-state/factory-dashboard/`,
  `.pack-state/startup-benchmarks/`,
  `.pack-state/autonomy-memory-distillations/`,
  `.pack-state/autonomy-quality-scores/`,
  `.pack-state/cross-template-transfer-matrices/`,
  `.pack-state/browser-proofs/`

Rationale:

- these surfaces either are the canonical truth layer
- or they are intentionally preserved PackFactory evidence
- or they are small generated summaries that materially help restart and review

Important boundary:

- if a `.pack-state/` surface is preserved in git, that does not make it the
  source of truth over registry, deployment, or control-plane JSON
- memory pointers and dashboard `latest/` are convenience surfaces; they may be
  committed, but they remain derived from deeper canonical inputs

### 2. `separate_backup`

These surfaces require host-local or external backup outside normal git usage:

- remote access prerequisites not stored in the repo:
  SSH config, SSH keys, host aliases, agent/socket setup, and any host-local
  connection notes
- local environment configuration needed to run PackFactory on a fresh machine:
  interpreter/toolchain bootstrap notes, local package mirrors if used, and any
  operator-maintained wrapper scripts outside the repo
- any PackFactory-managed scratch-root selection or host-local runtime
  configuration that lives outside the repo path
- any operator-visible roundtrip or export artifacts intentionally copied out of
  transient scratch before cleanup

Rationale:

- PackFactory depends on these operationally
- git inside this repo does not fully protect them
- workstation loss can break practical recovery even when the repo itself is safe

Important boundary:

- secrets, credentials, and private connection material should not be copied
  into the repo just to simplify backup
- they need a separate secure backup path consistent with host policy

### 3. `transient_disposable`

These surfaces should stay out of routine backup and should not drive recovery
planning:

- PackFactory-managed local scratch roots such as
  `.pack-state/local-scratch/`
- hard-wired transient staging trees such as
  `.pack-state/remote-autonomy-staging/`
- transient scratch roots and roundtrip staging trees described in the
  transient-scratch spec
- transient runtime pull caches such as
  `.pack-state/remote-runtime-pulls/`
- staged remote payloads, pulled runtime bundles, and temporary incoming or
  unpacked roundtrip work areas unless an operator explicitly preserves a copy
- temporary request staging such as
  `.pack-state/tmp/`
- runtime download/install trees such as
  `.pack-state/browser-proof-runtime/`
- local app build outputs and dependency caches such as
  `apps/factory-dashboard/.astro/`,
  `apps/factory-dashboard/dist/`,
  `apps/factory-dashboard/node_modules/`
- Python caches and local virtual environments
- `requests/` and other convenience request staging areas unless a request file
  is intentionally promoted into durable evidence or docs
- scratch-only incoming payload subtrees inside mixed roundtrip history such as
  `.pack-state/remote-autonomy-roundtrips/**/incoming/`

Rationale:

- these are rebuildable
- they create avoidable storage pressure
- they blur the line between durable evidence and temporary execution workspace

## Git Hygiene Rules

### Commit Rules

- commit canonical control-plane changes together with the docs or specs that
  explain them
- commit preserved evidence only when it is part of the intended audit trail,
  restart path, or operator briefing path
- do not commit transient scratch, runtime downloads, or dependency caches
- do not rely on an unpushed local branch as the only recovery path for
  important PackFactory state

### Pre-Commit Baseline

For root-level PackFactory changes, the normal bounded check is:

```bash
python3 tools/validate_factory.py \
  --factory-root /home/orchadmin/project-pack-factory \
  --output json
```

If the change affects a generated convenience surface, regenerate it before
commit rather than hand-editing derivatives:

- root memory:
  `python3 tools/refresh_factory_autonomy_memory.py ...`
- dashboard latest:
  `python3 tools/build_factory_dashboard_astro.py ...` or
  `python3 tools/generate_factory_dashboard.py ...`

### Commit Cadence

- commit after each bounded design or tooling slice that changes canonical
  behavior
- push the authoritative branch after any change that would be painful to
  reconstruct from memory
- avoid long-lived local-only drift for registry, task tracker, deployment
  pointers, or pack-local control-plane files

## Backup Cadence

### Git-Primary Cadence

- push meaningful PackFactory work at least at the end of each active session
  that changes canonical state
- push before risky local experiments, large refactors, or machine maintenance
- prefer small recoverable commits over large infrequent dumps

### Separate-Backup Cadence

- back up host-local SSH and remote-access prerequisites whenever they change
- maintain at least one restorable secure copy of operator-local access
  material outside the workstation
- if a workflow produces operator-visible artifacts that must survive scratch
  cleanup, copy them to a durable non-scratch location immediately

## Restore Workflows

### Restore Workflow A: Repo Recovery From Git

Use this when the local repo is corrupted, deleted, or badly drifted.

1. restore or reclone the repository from the authoritative remote
2. restore the intended branch or commit
3. reinstall the local runtime dependencies needed to run PackFactory
4. run root validation:

```bash
python3 tools/validate_factory.py \
  --factory-root /home/orchadmin/project-pack-factory \
  --output json
```

5. regenerate convenience surfaces if needed:

```bash
python3 tools/refresh_factory_autonomy_memory.py \
  --factory-root /home/orchadmin/project-pack-factory \
  --actor restore \
  --output json
```

```bash
python3 tools/build_factory_dashboard_astro.py \
  --factory-root /home/orchadmin/project-pack-factory \
  --output-dir /home/orchadmin/project-pack-factory/.pack-state/factory-dashboard/latest \
  --app-dir /home/orchadmin/project-pack-factory/apps/factory-dashboard \
  --staging-root /home/orchadmin/project-pack-factory/.pack-state/factory-dashboard/astro-staging \
  --report-format json
```

Success condition:

- canonical repo truth is present
- validation passes
- derived startup surfaces are available again

### Restore Workflow B: Host-Local Operational Recovery

Use this when the repo is intact but the operator loses local access setup or a
machine and needs PackFactory to function again.

1. restore SSH keys, SSH config, host aliases, and any approved secret material
   from the secure host-local backup path
2. restore any operator-maintained non-repo wrapper scripts or environment
   configuration required for PackFactory remote workflows
3. if PackFactory uses a non-default scratch-root location outside the repo,
   restore or recreate that host-local configuration
4. confirm the repo still validates
5. rerun the specific PackFactory remote workflow or bounded proof that depends
   on the restored access path

Success condition:

- the repo was not treated as the storage location for secrets
- remote workflow prerequisites are functional again
- PackFactory can resume bounded remote operations without ad hoc reconstruction

## Non-Goals

- treating every `.pack-state/` subtree as scratch
- treating every `.pack-state/` artifact as canonical truth
- storing secrets or private access material in the repo
- using git as a substitute for transient workspace cleanup
- backing up bulky staged payloads merely because they exist locally once

## Practical Rule Of Thumb

When unsure, classify a surface in this order:

1. if it is canonical PackFactory truth or intentionally preserved evidence,
   keep it in git
2. if it is host-local access or machine configuration outside repo authority,
   back it up separately
3. if it is rebuildable runtime, staging, or scratch, let it stay disposable

That keeps recovery simple:

- git restores the factory
- secure host backup restores operator access
- transient scratch gets rebuilt or ignored
