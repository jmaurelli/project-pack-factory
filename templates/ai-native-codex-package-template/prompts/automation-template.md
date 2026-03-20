# Automation Prompt Template

Default automation prompt for routine package execution.

```text
Objective:
Execute a deterministic AI-native package from its dedicated package root.

Package root:
<package-root>

Instructions:
- Keep CLI behavior deterministic.
- Keep delegated backend usage Codex-native.
- Preserve package-local prompts and docs.
- Stop and ask only for missing required inputs.

Expected return fields:
- command
- backend
- output_dir
- payload_path or report_path
- delegated_artifact_paths
- status
```
