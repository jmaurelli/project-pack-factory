# Codex Personal Assistant Workflow Plan

## Current Decision

- planning outcome: `create_new_template`
- target template id: `codex-personal-assistant-template-pack`
- first proving-ground build-pack: `codex-personal-assistant-daily-driver-build-pack-v1`

## Why A New Template Is Justified

- active templates in PackFactory are narrow capability packs, not personal assistant environments
- the retired `ai-native-codex-package-template` proves prior Codex interest but is a package scaffold, not the environment shape this project needs
- the desired product is a Codex-native operating environment with identity, context routing, restart memory, skill overlays, and install/update surfaces

## Suggested V1 Template Scope

- assistant profile and startup guidance
- context router for loading only relevant local surfaces
- memory write/read commands for restart continuity
- skill registry plus customization overlay
- install/bootstrap command
- update/doctor command
- minimal benchmark that proves bootstrap plus restart-memory behavior

## Explicit Deferrals

- voice server parity with the Claude-oriented reference
- GUI installer parity
- broad hook automation that depends on Claude-specific lifecycle events
- one-to-one file layout parity with `.claude`

## Workflow Status

- request artifact staged at `.pack-state/tmp/codex-personal-assistant-template-creation-request.json`
- first materialization request staged at `.pack-state/tmp/codex-personal-assistant-first-materialization-request.json`
- canonical template creation is currently blocked by unrelated existing factory validation failures

## Next Move Once Preflight Is Clean

```bash
python3 tools/create_template_pack.py \
  --factory-root /home/orchadmin/project-pack-factory \
  --request-file /home/orchadmin/project-pack-factory/.pack-state/tmp/codex-personal-assistant-template-creation-request.json \
  --output json
```

Then materialize the first proving-ground build-pack:

```bash
python3 tools/materialize_build_pack.py \
  --factory-root /home/orchadmin/project-pack-factory \
  --request-file /home/orchadmin/project-pack-factory/.pack-state/tmp/codex-personal-assistant-first-materialization-request.json \
  --output json
```
