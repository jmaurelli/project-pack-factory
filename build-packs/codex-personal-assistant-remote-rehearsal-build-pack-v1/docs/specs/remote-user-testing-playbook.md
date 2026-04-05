# Remote User Testing Playbook

Use this playbook for the first clean user test of the Codex personal assistant
line on the rehearsed remote target.

## Test Target

- build-pack id:
  `codex-personal-assistant-remote-rehearsal-build-pack-v1`
- remote target:
  `adf@adf-dev`
- remote pack directory:
  `~/packfactory-source__adf-dev__autonomous-build-packs/codex-personal-assistant-remote-rehearsal-build-pack-v1`
- remote-proof evidence:
  `.pack-state/multi-hop-autonomy-rehearsals/multi-hop-autonomy-rehearsal-codex-personal-assistant-remote-rehearsal-build-pack-v1-20260329t162825z/rehearsal-report.json`

## What This Test Is Proving

This pack is ready for remote user testing of the current baseline:

- remote pack startup is understandable
- the supported PackFactory CLI surfaces run cleanly on the remote target
- the pack's machine-readable readiness and work-state remain coherent

This playbook does not assume a full conversational assistant shell yet.
Current user testing is focused on the bounded CLI and control-plane surfaces
that were actually proved on `adf-dev`.

## Preflight

From the factory root, confirm the current canonical state before the session:

```bash
python3 tools/validate_factory.py --factory-root /home/orchadmin/project-pack-factory --output json
```

Optional quick state check:

```bash
sed -n '1,220p' /home/orchadmin/project-pack-factory/build-packs/codex-personal-assistant-remote-rehearsal-build-pack-v1/status/readiness.json
sed -n '1,220p' /home/orchadmin/project-pack-factory/build-packs/codex-personal-assistant-remote-rehearsal-build-pack-v1/status/work-state.json
```

## Session Setup

Open the remote target:

```bash
ssh adf@adf-dev
cd ~/packfactory-source__adf-dev__autonomous-build-packs/codex-personal-assistant-remote-rehearsal-build-pack-v1
python3 --version
pwd
```

The tester should be told up front:

- this is a PackFactory-proved remote rehearsal pack
- the current assistant baseline is intentionally small
- the test is about trust, clarity, and command behavior, not broad autonomy

## Tester Script

Run the steps in order and keep the raw JSON outputs.

### 1. Confirm the pack identity

```bash
sed -n '1,220p' pack.json
```

The tester should be able to answer:

- what pack this is
- that it is a build-pack
- what commands it officially exposes

### 2. Validate the pack contract

```bash
PYTHONPATH=src python3 -m codex_personal_assistant_template_pack validate-project-pack --project-root . --output json
```

Expected result:

- `status = "pass"`
- no missing paths

### 3. Run the smoke benchmark

```bash
PYTHONPATH=src python3 -m codex_personal_assistant_template_pack benchmark-smoke --project-root . --output json
```

Expected result:

- `status = "pass"`
- `benchmark_id = "codex-personal-assistant-template-pack-smoke-small-001"`

### 4. Inspect the ready boundary

```bash
sed -n '1,220p' status/readiness.json
sed -n '1,220p' status/work-state.json
```

Expected result:

- `status/readiness.json.ready_for_deployment = true`
- `status/readiness.json.readiness_state = "ready_for_deploy"`
- `status/work-state.json.autonomy_state = "ready_for_deploy"`
- `status/work-state.json.active_task_id = null`

### 5. Inspect the remote-proof memory pointer

```bash
sed -n '1,220p' .pack-state/agent-memory/latest-memory.json
```

Expected result:

- the pointer exists
- `selected_run_id` is present
- the pointer refers to a feedback-memory artifact under
  `.pack-state/agent-memory/`

## Questions For The Tester

Capture short answers to these:

- Was it obvious what this pack is for?
- Were the supported commands discoverable enough?
- Did the validation and benchmark outputs feel trustworthy?
- Was the readiness state easy to understand?
- Would you feel comfortable using this remote pack as a baseline for the next
  assistant iteration?

## Pass Criteria

Call the session a clean pass when all of these are true:

- remote login and startup are straightforward
- `validate-project-pack` passes
- `benchmark-smoke` passes
- readiness and work-state still show the ready boundary cleanly
- the tester reports no major confusion about what is implemented versus not
  yet implemented

## Failure Conditions

Stop and record a failure if any of these happen:

- either official command fails
- readiness or work-state contradict the expected ready boundary
- the memory pointer is missing
- the tester cannot tell what the current remote baseline actually supports

## Evidence To Save

Save or record:

- the raw JSON from `validate-project-pack`
- the raw JSON from `benchmark-smoke`
- the relevant excerpts from `status/readiness.json`
- the relevant excerpts from `status/work-state.json`
- the tester's short answers to the questions above

## Follow-On Actions

If the session passes:

- use the findings to tighten the assistant UX and command surface
- decide whether to keep iterating on this remote rehearsal pack or carry the
  lessons back into the daily-driver pack

If the session fails:

- log the failure as assistant-line feedback, not as a promotion failure
- fix the smallest blocking issue first
- rerun this same playbook instead of changing the test shape
