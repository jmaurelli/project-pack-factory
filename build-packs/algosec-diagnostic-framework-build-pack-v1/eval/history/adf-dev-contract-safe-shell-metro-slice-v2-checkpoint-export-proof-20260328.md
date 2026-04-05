## ADF Dev Contract-Safe Shell-Metro Slice V2 Checkpoint Export Proof

Date: 2026-03-28

This note records the first full remote proof after adding generic checkpoint
bundle writing plus automatic checkpoint-bundle export support.

What changed before the rerun:

- A generic `record-remote-checkpoint-bundle` CLI path was added for
  non-delegated runs.
- The runtime-evidence exporter now auto-includes
  `.pack-state/autonomy-runs/<run-id>/adf-remote-checkpoint-bundle.json` when
  present.
- The bounded remote prompt now explicitly tells the remote agent to write the
  checkpoint bundle before stopping at a meaningful checkpoint.

Observed v2 result:

- The local controller again hit the bounded 300-second SSH timeout.
- A short delayed pullback retry then recovered a succeeded export bundle.
- The pulled bundle now includes:
  - `artifacts/adf-remote-checkpoint-bundle.json`
  - `artifacts/run-summary.json`
  - `artifacts/loop-events.jsonl`
  - `artifacts/agent-memory/...`

Recovered execution result:

- `terminal_outcome = stopped`
- `terminal_reason = current_task_incomplete`
- `export_status = succeeded`

What this proves:

- The checkpoint-bundle handoff gap is fixed end to end for this remote slice.
- The raw bounded loop, delayed pullback pattern, and export path can now
  return the explicit ADF checkpoint manifest expected by the split-host
  contract.

What still limits autonomy quality:

- The returned checkpoint was still meta-level and measurement-oriented.
- The v2 loop events show a checkpoint-only boundary was created before a wider
  rerun, rather than a content-bearing shell-versus-Metro evidence minute.

Current implication:

- The next autonomy refinement is no longer checkpoint-bundle presence.
- The next refinement is to make the same contract-safe slice produce a
  support-useful evidence checkpoint on the shell-versus-Metro boundary without
  widening into source/docs authoring.
