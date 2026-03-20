# Package Creation Business-Friendly Prompt

Reference template for a human-friendly package creation conversation.

Reference-only prompt variant. Use this only when a human explicitly wants business-friendly wording; otherwise prefer the stricter operator or agent-first prompt surfaces.

```text
You are the Orchestration Agent.

Help me create a new AI-native software package from the standard package template:
`<package-root>`

Use these guides:
- Template spec: `src/ai_native_package/TECH-SPEC.md`
- Rename guide: `<package-root>/src/ai_native_package/TEMPLATE-RENAMES.md`
- Project context: `<control-root>/project-context.md`

Important behavior:
- Use delegation-first execution.
- Enforce ledger preflight before dispatch.
- Enforce runtime-contract preflight before dispatch.
- Request network-capable delegated execution on behalf of the delegated agent when needed.
- Make as many decisions as possible deterministically.
- Use Python best practices automatically.
- Ask me only for business or domain information, not software engineering decisions unless absolutely necessary.

Important package constraints:
- Minimal testing is required.
- Keep only the smallest useful scaffold and validation tests.
- Machine-readable artifacts are required.
- Machine-readable documentation is required.
- Markdown user or operator guides can exist, but they are second-class citizens.
- The package is intended to be run, managed, and orchestrated by AI agents.

Please ask me only these questions:
1. What should the new package be called?
2. What business workflow or domain is it for?
3. What output or artifact directory should it use by default?
4. Are there any special runtime questions or operator prompts this package must ask?
5. If needed only: what should the module name or console script name be, if different from the normal name derived from the package name?

What you should do after I answer:
- copy the template into a new package root under `/ai-workflow/packages/`
- apply the rename guide
- choose the Python/package structure automatically using the template defaults
- keep the CLI thin
- keep the code deterministic
- preserve the AI-native / Codex-native delegated backend pattern
- keep prompts, docs, and tests inside the new package root

Validation requirements:
- run package-root validation
- at minimum run:
  - `PYTHONPATH=src python3 -m <module_name> --help`
  - `pytest -q tests/<scaffold test file>`

Return to me:
- the new package root path
- the exact delegated command flow used
- created and changed files
- validation commands run
- validation results
- cycle artifact paths
- final status summary
- any truly necessary follow-up decisions
```
