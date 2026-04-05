# ADF adf-dev remote autonomy contract-fix rerun - 2026-03-28

## Purpose

Verify that the two concrete remote-loop contract fixes landed:

- the remote invocation prompt now targets current canonical task continuity
  instead of starter-backlog-only scope
- the writable-surface contract now allows the pack-declared candidate output
  area used by the existing benchmark

## Fixes applied

The factory remote loop in `tools/run_remote_autonomy_loop.py` was updated to:

- build the remote prompt from the current canonical local task scope
- allow the pack-declared `candidate_release_dir` as a bounded writable prefix
- create the candidate artifact directory during remote setup when declared

## Rerun result

The rerun no longer reproduced the two original failures.

Observed wrapper result:

- `boundary_violations = []`
- `export_status = succeeded`
- `export_bundle_path = dist/exports/runtime-evidence/external-runtime-evidence-algosec-diagnostic-framework-build-pack-v1-split-host-smoke-run-v1-20260328T164954Z`

That means:

- the benchmark-output writable-surface violation is fixed
- the remote run now emits an export bundle instead of stopping before export
- the prompt on `adf-dev` now names the current canonical task instead of
  starter-backlog-only scope

## Remaining nuance

The rerun still returned:

- `terminal_outcome = stopped`
- `terminal_reason = starter_backlog_incomplete`

So the original two contract issues are fixed, but the loop's terminal-state
language is still starter-backlog-oriented. That is now a later refinement,
not the same blocker that prevented the first real export.

## Imported evidence

The post-fix rerun bundle was pulled, imported, and reconciled through the
official PackFactory path:

- pull staging:
  `.pack-state/remote-runtime-imports/adf-dev-remote-autonomy-rerun-20260328/`
- import report:
  `eval/history/import-external-runtime-evidence-20260328t165103z/import-report.json`
- reconcile report:
  `eval/history/reconcile-imported-runtime-state-20260328t165118z/reconcile-report.json`

## Conclusion

The two targeted remote-loop contract issues are fixed.

The next useful autonomy proof is to let the now-corrected remote loop target
the next real content task, `deepen_dependency_aware_playbooks`, and judge the
quality of the returned checkpoint without the old prompt-scope or
benchmark-output boundary failures.
