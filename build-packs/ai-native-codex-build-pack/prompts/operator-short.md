# Operator Prompt Example

Short reference prompt for human-triggered runs.

```text
Use the package root:
<package-root>

If the task is a code change, use:
<control-root>/project-context.md

Ask only for the missing runtime inputs:
1. What target or task should be executed?
2. Is delegated execution required?
3. Where should resulting artifacts be written?

Keep execution deterministic and package-root local.
```
