# Project Context

## Project Goal

Deploy Codex into a controlled AlgoSec Security Management Suite lab appliance
on Rocky Linux 8, collect bounded runtime evidence, generate a trustworthy
machine-readable baseline and support comparison playbooks, and render a simple
HTML view for remote support sessions.

## Primary User

Support engineers working live with customers over screen share or remote
session, mostly at a junior level.

The playbooks should assume:

- the engineer can use basic Linux and network commands
- the engineer follows explicit step-by-step instructions well
- the engineer may not know deeper Linux internals
- English may be the engineer's second language
- the wording should stay plain, short, and direct
- Linux terms should stay consistent across playbooks so engineers learn and
  reuse the same support language with customers
- when a Linux term may be unfamiliar, the playbook should give a brief plain
  explanation close to the command instead of assuming deep OS knowledge

## V1 Scope

- One controlled AlgoSec lab appliance on Rocky Linux 8.
- Machine-readable runtime evidence as the canonical source of truth.
- A complete service inventory with deeper playbooks for the highest-value
  service paths first.
- Simple HTML output for human use during support sessions.
- AI inference as a secondary layer over collected evidence, not the primary
  product output.

## V1 Non-Goals

- Full coverage of every service at equal depth.
- Direct automation inside customer environments.
- Broad test expansion or large fixture matrices.
- A polished portal or generalized reverse-engineering platform.

## Success Criteria

- The output gives support engineers a trusted baseline and clear diagnostic
  steps they can use in a customer environment.
- The baseline clearly separates observed facts, inference, and unknowns.
- The first playbooks help narrow likely issue areas during live support.
- HTML output is useful during a remote support session without becoming the
  source of truth.

## Execution Topology

- Local PackFactory is the canonical planning, acceptance, and durable-evidence
  owner for this project.
- `adf-dev` is the remote execution worker and review surface for bounded ADF
  autonomy runs.
- The AlgoSec target lab is the runtime evidence source.
- Imported evidence preserved under `eval/history/` is the durable evidence
  line.
- Local scratch staging, pulled roundtrip `incoming/` trees, and similar
  transport artifacts support workflow execution but are not canonical evidence
  by themselves.

## Working Priorities

1. Collect trustworthy runtime evidence.
2. Turn that evidence into simple support playbooks written in plain language.
3. Keep the scope small enough to stay manageable.
4. Keep testing minimal and high-signal.
