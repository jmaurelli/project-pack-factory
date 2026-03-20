# Packaging Notes

`packages/ai-native-codex-package-template/pyproject.toml` is the dedicated packaging surface for this template.

Rules for copied packages:

- keep package metadata inside the copied package root
- keep the console script pointed at the copied package module
- avoid pointing packaging back to a shared repo `src/` tree
- validate from the package root after renaming

This template is intentionally small. It is a starting point for future packages, not a shared runtime framework.
