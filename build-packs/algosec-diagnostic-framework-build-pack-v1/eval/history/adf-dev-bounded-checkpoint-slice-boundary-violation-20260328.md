## ADF Dev Bounded Checkpoint Slice Boundary Violation — 2026-03-28

Purpose:
Record what happened when ADF tried a bounded remote checkpoint slice for the
in-progress `deepen_dependency_aware_playbooks` task through the raw PackFactory
remote loop surfaces instead of the completion-oriented active-task continuity
wrapper.

What happened:
- The original bounded slice request `algosec-diagnostic-framework-build-pack-v1-bounded-checkpoint-slice-v1`
  was launched through the official `run_remote_autonomy_test.py` roundtrip
  path.
- The local wrapper later had to be stopped because the loop has no built-in
  execution timeout or in-flight status surface, so the run looked hung from
  the local side.
- The supported pullback path against the same request then recovered the
  remote `execution-manifest.json` and proved the remote side had actually
  finished.

Recovered remote result:
- `terminal_outcome = boundary_violation`
- `terminal_reason = unauthorized_writable_surface`
- `export_status = not_attempted`
- no bundle export was available to import

Why this matters:
- This was not another startup-memory problem.
- It was not a completion-style task-selection problem either.
- The raw bounded remote loop still is not the right execution surface for this
  broad in-progress authoring task under the current writable-surface contract.

Additional tooling improvement:
- `tools/run_remote_autonomy_loop.py` now honors optional environment variable
  `PACKFACTORY_REMOTE_SSH_TIMEOUT_SECONDS` so future bounded remote slices can
  fail closed instead of waiting indefinitely on `ssh ... python3 -`.

Plain-language conclusion:
For `deepen_dependency_aware_playbooks`, the next autonomy question is no
longer “can the remote loop start?” It can. The real blocker is that the raw
remote loop still stops on unauthorized writable-surface policy before it can
return a usable authoring checkpoint for this task.
