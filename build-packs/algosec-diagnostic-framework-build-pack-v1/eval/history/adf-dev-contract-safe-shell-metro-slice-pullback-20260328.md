## ADF Dev Contract-Safe Shell-Metro Slice Pullback

Date: 2026-03-28

This note records the first raw bounded `adf-dev` run after the active task was
narrowed to the contract-safe evidence-only shell-versus-Metro slice.

Observed result:

- The local controller timed out after the bounded
  `PACKFACTORY_REMOTE_SSH_TIMEOUT_SECONDS=300` window.
- An immediate pullback attempt did not find `execution-manifest.json` yet.
- A short delayed retry then succeeded and pulled a real exported bundle.

Recovered remote execution result:

- `started_at = 2026-03-28T18:47:37Z`
- `stopped_at = 2026-03-28T18:53:58Z`
- `terminal_outcome = stopped`
- `terminal_reason = current_task_incomplete`
- `export_status = succeeded`

What this proves:

- The contract-safe slice no longer fails with
  `boundary_violation / unauthorized_writable_surface`.
- The narrowed task boundary is usable for the raw bounded loop.
- A controller timeout does not necessarily mean the remote slice failed; the
  remote side can still finish and publish an exportable bundle shortly after.

What still limits autonomy:

- The exported bundle contained `run-summary.json`, `loop-events.jsonl`, and
  feedback memory, but not the expected `adf-remote-checkpoint-bundle.json`
  artifact named in the remote workflow note.
- The loop events showed a checkpoint was recorded remotely at
  `2026-03-28T18:50:31Z`, but the local returned bundle was still measurement
  evidence only rather than a fully useful checkpoint-handoff artifact.

Current implication:

- The next autonomy refinement is checkpoint-handoff completeness and pullback
  timing, not writable-surface drift.
- Keep the contract-safe shell-versus-Metro slice active until the returned
  bundle includes the intended checkpoint artifact or an equivalent explicit
  handoff surface.
