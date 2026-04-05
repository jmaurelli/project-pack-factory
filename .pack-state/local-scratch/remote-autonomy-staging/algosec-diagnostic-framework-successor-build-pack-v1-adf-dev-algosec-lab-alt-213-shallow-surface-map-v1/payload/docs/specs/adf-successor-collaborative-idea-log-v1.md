# ADF Successor Collaborative Idea Log v1

## Purpose

Provide one machine-readable, agent-optimized place to capture successor-local:

- product ideas
- behavioral notes
- cookbook candidates
- operator theories
- workflow observations

without forcing those items into the active backlog or the autonomy-memory
surfaces too early.

## Canonical Artifact

- `notes/idea-log.json`

This file is meant to stay in the build-pack repository, not under transient
scratch.

## Why This Surface Exists

The successor already has strong surfaces for:

- execution truth:
  `contracts/project-objective.json`,
  `tasks/active-backlog.json`,
  `status/work-state.json`
- restart continuity:
  `.pack-state/agent-memory/latest-memory.json`
- derived runtime learning:
  the shallow-surface-map artifacts and the engineer-facing cookbook outputs

What it did not have yet was a stable place for collaborative ideas that are:

- relevant to the successor
- worth preserving
- not yet action items
- not yet proven enough to look like formal memory truth

The idea log fills that gap.

## Data Model

Each note records:

- stable `note_id`
- timestamps
- `note_kind`
- `evidence_state`
- `review_state`
- title and short summary
- optional details
- tags, related topics, related paths, and related task ids

## Intended Usage

Use the idea log when the operator or agent wants to capture something like:

- "this looks like a product behavior worth remembering"
- "this may belong in a future cookbook"
- "this feels operationally important but is not yet a task"
- "this is a theory we want to review together later"

Do not use the idea log for:

- active execution tracking that belongs in backlog or work-state
- restart memory that belongs in `.pack-state/agent-memory/`
- proof claims that should instead be written into a bounded review artifact

## Commands

Record a note:

```bash
PYTHONPATH=src python3 -m algosec_diagnostic_framework_successor_template_pack record-idea-note \
  --project-root . \
  --title "<title>" \
  --summary "<summary>" \
  --detail "<detail>" \
  --tag "<tag>" \
  --related-topic "<topic>" \
  --output json
```

Review recent notes:

```bash
PYTHONPATH=src python3 -m algosec_diagnostic_framework_successor_template_pack list-idea-notes \
  --project-root . \
  --limit 20 \
  --output json
```

Update note review or lifecycle state:

```bash
PYTHONPATH=src python3 -m algosec_diagnostic_framework_successor_template_pack update-idea-note \
  --project-root . \
  --note-id "<note-id>" \
  --review-state in_review \
  --output json
```

## Compatibility Rules

To stay compatible with the current memory and tracking model, the idea log
should remain:

- machine-readable
- append-friendly
- update-friendly without manual JSON editing
- explicit about evidence state
- separate from canonical execution truth
- easy for a future agent to inspect during pack entry
