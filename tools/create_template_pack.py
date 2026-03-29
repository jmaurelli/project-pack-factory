#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import keyword
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from factory_ops import (
    PERSONALITY_TEMPLATE_CATALOG_PATH,
    PROMOTION_LOG_PATH,
    REGISTRY_TEMPLATE_PATH,
    isoformat_z,
    load_json,
    resolve_personality_template,
    read_now,
    relative_path,
    resolve_factory_root,
    schema_path,
    timestamp_token,
    validate_json_document,
    write_json,
)
from validate_factory import validate_factory


def _load_object(path: Path) -> dict[str, Any]:
    payload = load_json(path)
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: JSON document must contain an object")
    return payload


def _load_request(request_path: Path, factory_root: Path) -> dict[str, Any]:
    errors = validate_json_document(
        request_path,
        schema_path(factory_root, "template-creation-request.schema.json"),
    )
    if errors:
        raise ValueError("; ".join(errors))
    return _load_object(request_path)


def _module_name(template_pack_id: str) -> str:
    candidate = template_pack_id.replace("-", "_")
    if not candidate.isidentifier() or keyword.iskeyword(candidate):
        candidate = f"pack_{candidate}"
    if not candidate.isidentifier() or keyword.iskeyword(candidate):
        raise ValueError(f"could not derive a valid Python module name from `{template_pack_id}`")
    return candidate


def _gate_id(benchmark_id: str) -> str:
    return benchmark_id.replace("-", "_")


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _directory_contract() -> dict[str, Any]:
    return {
        "docs_dir": "docs",
        "prompts_dir": "prompts",
        "contracts_dir": "contracts",
        "source_dir": "src",
        "tests_dir": "tests",
        "benchmarks_dir": "benchmarks",
        "benchmark_active_set_file": "benchmarks/active-set.json",
        "eval_dir": "eval",
        "eval_latest_index_file": "eval/latest/index.json",
        "eval_history_dir": "eval/history",
        "status_dir": "status",
        "lifecycle_file": "status/lifecycle.json",
        "readiness_file": "status/readiness.json",
        "retirement_file": "status/retirement.json",
        "deployment_file": "status/deployment.json",
        "lineage_dir": None,
        "lineage_file": None,
        "dist_dir": "dist",
        "candidate_release_dir": None,
        "immutable_release_dir": None,
        "template_export_dir": "dist/exports",
        "local_state_dir": ".pack-state",
    }


def _pack_manifest(
    *,
    template_pack_id: str,
    display_name: str,
    owning_team: str,
    module_name: str,
    creation_id: str,
    project_goal: str,
    capability_family: str,
    personality_template: dict[str, Any] | None,
) -> dict[str, Any]:
    manifest = {
        "schema_version": "pack-manifest/v2",
        "pack_id": template_pack_id,
        "pack_kind": "template_pack",
        "display_name": display_name,
        "owning_team": owning_team,
        "runtime": "python",
        "bootstrap_read_order": [
            "AGENTS.md",
            "project-context.md",
            "pack.json",
        ],
        "post_bootstrap_read_order": [
            "status/lifecycle.json",
            "status/readiness.json",
            "status/retirement.json",
            "status/deployment.json",
            "benchmarks/active-set.json",
            "eval/latest/index.json",
        ],
        "entrypoints": {
            "cli_command": f"PYTHONPATH=src python3 -m {module_name} --help",
            "validation_command": f"PYTHONPATH=src python3 -m {module_name} validate-project-pack --project-root . --output json",
            "benchmark_command": f"PYTHONPATH=src python3 -m {module_name} benchmark-smoke --project-root . --output json",
        },
        "directory_contract": _directory_contract(),
        "identity_source": "pack.json",
        "notes": [
            "Created through the PackFactory template creation workflow.",
            f"creation_id={creation_id}",
            f"project_goal={project_goal}",
            f"capability_family={capability_family}",
            "factory_autonomy_baseline=This source template inherits the PackFactory autonomy baseline from docs/specs/project-pack-factory/PROJECT-PACK-FACTORY-AUTONOMY-STATE-BRIEF.md and docs/specs/project-pack-factory/PROJECT-PACK-FACTORY-AUTONOMY-OPERATIONS-NOTE.md.",
            "factory_autonomy_tracking=Template-level autonomy notes are pointers to factory defaults; the factory root remains the canonical baseline for inherited memory, feedback, restart, branch-choice behavior, and remote-session compliance.",
            "template_lineage_memory=When present, template-family lessons live under .pack-state/template-lineage-memory/latest-memory.json and remain advisory template-level context rather than canonical factory truth.",
            "factory_startup_compliance=Inherited startup guidance requires PackFactory-local remote-session workflows and treats external runtime-evidence import as factory-only.",
        ],
    }
    if personality_template is not None:
        manifest["personality_template"] = personality_template
        manifest["notes"].extend(
            [
                f"personality_template_id={personality_template['template_id']}",
                f"personality_template_default_for_derivatives={str(personality_template['apply_to_derived_build_packs_by_default']).lower()}",
            ]
        )
    return manifest


def _lifecycle_state(
    *,
    template_pack_id: str,
    creation_id: str,
    created_at: str,
    requested_by: str,
    reason: str,
) -> dict[str, Any]:
    return {
        "schema_version": "pack-lifecycle/v2",
        "pack_id": template_pack_id,
        "pack_kind": "template_pack",
        "lifecycle_stage": "maintained",
        "state_reason": reason,
        "current_version": "0.1.0",
        "current_revision": creation_id,
        "promotion_target": "none",
        "updated_at": created_at,
        "updated_by": requested_by,
    }


def _readiness_state(
    *,
    template_pack_id: str,
    created_at: str,
    benchmark_id: str,
    benchmark_objective: str,
) -> dict[str, Any]:
    return {
        "schema_version": "pack-readiness/v2",
        "pack_id": template_pack_id,
        "pack_kind": "template_pack",
        "readiness_state": "ready_for_review",
        "ready_for_deployment": False,
        "last_evaluated_at": created_at,
        "blocking_issues": [
            "Template packs are source-only and are not deployable artifacts.",
            "Initial template benchmark baseline has not been recorded yet.",
        ],
        "recommended_next_actions": [
            "Validate the new template pack.",
            "Run the initial smoke benchmark to record the first baseline.",
            "Materialize a build pack when the template is ready for downstream testing.",
        ],
        "required_gates": [
            {
                "gate_id": "validate_project_pack",
                "mandatory": True,
                "status": "not_run",
                "summary": "Basic PackFactory structure and contract validation.",
                "last_run_at": None,
                "evidence_paths": [],
            },
            {
                "gate_id": _gate_id(benchmark_id),
                "mandatory": True,
                "status": "not_run",
                "summary": benchmark_objective,
                "last_run_at": None,
                "evidence_paths": [],
            },
        ],
    }


def _deployment_state(template_pack_id: str) -> dict[str, Any]:
    return {
        "schema_version": "pack-deployment/v2",
        "pack_id": template_pack_id,
        "pack_kind": "template_pack",
        "deployment_state": "not_deployed",
        "active_environment": "none",
        "active_release_id": None,
        "active_release_path": None,
        "deployment_pointer_path": None,
        "deployment_transaction_id": None,
        "projection_state": "not_required",
        "last_promoted_at": None,
        "last_rollback": None,
        "last_verified_at": None,
        "deployment_notes": [
            "Template packs are source-only and are not directly deployable.",
        ],
    }


def _retirement_state(template_pack_id: str) -> dict[str, Any]:
    return {
        "schema_version": "pack-retirement/v1",
        "pack_id": template_pack_id,
        "pack_kind": "template_pack",
        "retirement_state": "active",
        "retired_at": None,
        "retired_by": None,
        "retirement_reason": None,
        "superseded_by_pack_id": None,
        "retirement_report_path": None,
        "removed_deployment_pointer_paths": [],
        "retained_artifacts": {
            "eval_history": True,
            "release_artifacts": False,
            "lineage": False,
        },
        "operator_notes": [
            "Created through the PackFactory template creation workflow.",
        ],
    }


def _active_set(template_pack_id: str, benchmark_id: str, objective: str) -> dict[str, Any]:
    return {
        "schema_version": "pack-benchmark-active-set/v1",
        "pack_id": template_pack_id,
        "pack_kind": "template_pack",
        "default_benchmark_id": benchmark_id,
        "active_benchmarks": [
            {
                "benchmark_id": benchmark_id,
                "declaration_path": f"benchmarks/declarations/{benchmark_id}.json",
                "objective": objective,
                "required_for_readiness": True,
            }
        ],
    }


def _eval_latest(template_pack_id: str, benchmark_id: str) -> dict[str, Any]:
    return {
        "schema_version": "pack-eval-index/v1",
        "pack_id": template_pack_id,
        "pack_kind": "template_pack",
        "updated_at": isoformat_z(),
        "benchmark_results": [
            {
                "benchmark_id": benchmark_id,
                "status": "not_run",
                "latest_run_id": f"{template_pack_id}-bootstrap",
                "run_artifact_path": "eval/history/bootstrap/not-run.json",
                "summary_artifact_path": "eval/history/bootstrap/not-run.json",
            }
        ],
    }


def _benchmark_declaration(
    *,
    template_pack_id: str,
    benchmark_id: str,
    creation_id: str,
    description: str,
) -> dict[str, Any]:
    benchmark_task_id = f"task-{benchmark_id}"
    return {
        "schema_version": "benchmark-declaration/v1",
        "benchmark_task_id": benchmark_task_id,
        "benchmark_suite_id": "packfactory-template-creation-suite",
        "benchmark_revision": f"rev-{benchmark_id}",
        "benchmark_category": "workflow-smoke",
        "benchmark_size_class": "small",
        "complexity_profile": "single-package-low",
        "approval_profile": "approval_not_required",
        "intended_pack_family": "template-pack",
        "intended_languages": ["python"],
        "description": description,
        "target_project": {
            "target_project_id": template_pack_id,
            "target_locator": "repo-local",
            "default_relative_root": f"templates/{template_pack_id}",
        },
        "manifest_defaults": {
            "pack_family": "template-pack",
            "pack_version": "0.1.0",
            "orchestration_core_version": creation_id,
            "terminal_benchmark_classification": "completed_within_envelope",
        },
        "tags": [
            "factory-native",
            "template-pack",
            "small",
            "created",
        ],
        "owners": ["orchadmin"],
        "status": "active",
    }


def _personality_overlay_section(
    personality_template: dict[str, Any] | None,
    *,
    template_default: bool,
) -> str:
    if personality_template is None:
        return ""
    inherited_text = (
        "Derived build-packs inherit this overlay by default unless materialization explicitly clears it or selects another personality template."
        if template_default
        else "Derived build-packs do not inherit this overlay automatically; materialization must select it explicitly when the overlay should follow downstream."
    )
    lines = [
        "## Optional Personality Overlay",
        "",
        (
            "This template currently carries the optional personality overlay "
            f"`{personality_template['template_id']}` ({personality_template['display_name']})."
        ),
        personality_template["summary"],
        inherited_text,
        "Treat the overlay as briefing and recommendation-framing guidance only. It does not override canonical factory policy, lifecycle state, deployment truth, or pack-local control-plane files.",
    ]
    for line in personality_template.get("agent_context_lines", []):
        lines.append(f"- {line}")
    lines.append("")
    return "\n".join(lines)


def _manifest_personality_template(personality_template: dict[str, Any] | None) -> dict[str, Any] | None:
    if personality_template is None:
        return None
    return {
        "template_id": personality_template["template_id"],
        "display_name": personality_template["display_name"],
        "summary": personality_template["summary"],
        "selection_origin": personality_template["selection_origin"],
        "selection_reason": personality_template["selection_reason"],
        "catalog_path": personality_template["catalog_path"],
        "apply_to_derived_build_packs_by_default": personality_template[
            "apply_to_derived_build_packs_by_default"
        ],
    }


def _pack_agents(display_name: str, personality_template: dict[str, Any] | None = None) -> str:
    return f"""# {display_name}

This is a PackFactory-native template created through the template creation workflow.

## Bootstrap Order

1. `AGENTS.md`
2. `project-context.md`
3. `pack.json`
4. `status/lifecycle.json`
5. `status/readiness.json`
6. `status/retirement.json`
7. `status/deployment.json`
8. `benchmarks/active-set.json`
9. `eval/latest/index.json`

## Factory Autonomy Baseline

This template inherits the PackFactory autonomy baseline from the factory root.

Read these factory-level surfaces when the task concerns inherited agent
memory, feedback loops, autonomy rehearsal, stop-and-restart behavior, or
branch-choice policy:

1. `docs/specs/project-pack-factory/PROJECT-PACK-FACTORY-AUTONOMY-STATE-BRIEF.md`
2. `docs/specs/project-pack-factory/PROJECT-PACK-FACTORY-AUTONOMY-OPERATIONS-NOTE.md`
3. `docs/specs/project-pack-factory/PROJECT-PACK-FACTORY-AUTONOMY-PLANNING-LIST.md`
4. `.pack-state/agent-memory/latest-memory.json`

Treat the factory-level autonomy baseline as canonical for inherited default
behavior. Use this template only for template-specific source guidance and
runtime shape.

When `.pack-state/template-lineage-memory/latest-memory.json` exists, read it
after the factory-level baseline when you need a compact view of what this
template family has already taught the factory across derived build-packs.
Treat that template lineage memory as advisory template-family context, not as
canonical factory truth.

For remote Codex session management and external runtime-evidence handling,
follow the factory-root control plane rather than inventing template-local
remote workflows:

- use PackFactory-local remote-session, continuity, rehearsal, export, pull,
  and import workflows from the factory root when an official workflow exists
- do not improvise ad hoc `ssh` prompts, handcrafted remote-session runners,
  or raw stdout/stderr logging loops as substitutes for PackFactory evidence
- treat external runtime-evidence import as factory-only through
  `tools/import_external_runtime_evidence.py` or a higher-level PackFactory
  workflow that wraps that import

{_personality_overlay_section(
    personality_template,
    template_default=bool(
        personality_template and personality_template.get("apply_to_derived_build_packs_by_default") is True
    ),
)}

## Working Rules

- Treat this pack as an active source template.
- Use `validate-project-pack` before trusting local state.
- Use `benchmark-smoke` as the smallest bounded benchmark for this template.
- Keep this template easy for a fresh agent to inspect and adapt.
- Treat this template as source-only. It is not directly deployable.
"""


def _project_context(module_name: str, benchmark_id: str, project_goal: str) -> str:
    return f"""# Project Context

This template was created to support the following project goal:

- {project_goal}

## Priority

1. Keep the template valid for PackFactory traversal and later materialization.
2. Keep validation and benchmark commands small and deterministic.
3. Keep the pack easy for a fresh agent to inspect.

## Primary Runtime Surfaces

- `src/{module_name}/cli.py`
- `src/{module_name}/validate_project_pack.py`
- `src/{module_name}/benchmark_smoke.py`
- `benchmarks/active-set.json`
- `benchmarks/declarations/{benchmark_id}.json`
- `eval/latest/index.json`

## Local State

- local scratch state: `.pack-state/`
- optional template lineage memory: `.pack-state/template-lineage-memory/latest-memory.json`

## Factory-Level Inheritance Note

This template is a source template, not the canonical home of the autonomy
baseline.

For inherited PackFactory defaults around agent memory, feedback loops,
restart behavior, rehearsal evidence, and branch-choice policy, prefer the
factory-level state brief and operations note:

- `docs/specs/project-pack-factory/PROJECT-PACK-FACTORY-AUTONOMY-STATE-BRIEF.md`
- `docs/specs/project-pack-factory/PROJECT-PACK-FACTORY-AUTONOMY-OPERATIONS-NOTE.md`

When present, the template-local lineage memory at
`.pack-state/template-lineage-memory/latest-memory.json` is the shortest path
to template-family learning that has already been distilled from derived
build-packs.

That inherited baseline now also includes startup-compliance expectations for
remote Codex session management and runtime-evidence flow:

- prefer PackFactory-local remote-session workflows from the factory root
- do not treat ad hoc `ssh` prompts or raw stdout/stderr logs as canonical
  PackFactory evidence
- return to the factory root for external runtime-evidence import

## Optional Personality Overlay

When `pack.json.personality_template` exists, treat it as an optional overlay
for briefing tone, recommendation framing, and operator-facing collaboration.

That overlay should stay composable with the template itself:

- one source template can still feed multiple build-packs with different
  personality overlays
- the overlay should not replace the project goal, runtime surfaces, or
  control-plane files
- canonical lifecycle, readiness, deployment, and promotion state always win
  over personality guidance when they point in different directions
"""


def _pack_readme(display_name: str, template_pack_id: str, module_name: str) -> str:
    return f"""# {display_name}

PackFactory-native template pack `{template_pack_id}`.

## Commands

```bash
PYTHONPATH=src python3 -m {module_name} --help
PYTHONPATH=src python3 -m {module_name} validate-project-pack --project-root . --output json
PYTHONPATH=src python3 -m {module_name} benchmark-smoke --project-root . --output json
```
"""


def _contracts_readme() -> str:
    return """# Contracts

This template keeps pack-level contracts in machine-readable PackFactory state files.
Add project-specific contracts here only when the template needs them.
"""


def _docs_specs_readme() -> str:
    return """# Specs

Add template-specific technical notes or implementation specs here when the template grows beyond the starter scaffold.
"""


def _prompts_readme() -> str:
    return """# Prompts

Store template-local prompts or operator guidance here when the pack needs them.
"""


def _tests_readme() -> str:
    return """# Tests

Keep tests small, deterministic, and focused on the few behaviors that materially protect this template.
"""


def _gitignore() -> str:
    return """__pycache__/
*.pyc
.pytest_cache/
.ruff_cache/
.mypy_cache/
.venv/
*.egg-info/
"""


def _pyproject(template_pack_id: str, display_name: str, module_name: str) -> str:
    escaped_display = display_name.replace('"', '\\"')
    return f"""[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "{template_pack_id}"
version = "0.1.0"
description = "{escaped_display}"
readme = "README.md"
requires-python = ">=3.12"
dependencies = []

[project.scripts]
{template_pack_id} = "{module_name}.cli:main"

[tool.setuptools]
package-dir = {{"" = "src"}}

[tool.setuptools.packages.find]
where = ["src"]
include = ["{module_name}*"]
"""


def _init_py() -> str:
    return '__all__ = ["main"]\n'


def _main_py(module_name: str) -> str:
    return f"""from .cli import main


if __name__ == "__main__":
    raise SystemExit(main())
"""


def _cli_py(module_name: str) -> str:
    return f"""from __future__ import annotations

import argparse
import json
from pathlib import Path

from .benchmark_smoke import benchmark_smoke
from .validate_project_pack import validate_project_pack


def main() -> int:
    parser = argparse.ArgumentParser(prog="{module_name}")
    subparsers = parser.add_subparsers(dest="command")

    validate_parser = subparsers.add_parser("validate-project-pack")
    validate_parser.add_argument("--project-root", default=".")
    validate_parser.add_argument("--output", choices=("json",), default="json")

    benchmark_parser = subparsers.add_parser("benchmark-smoke")
    benchmark_parser.add_argument("--project-root", default=".")
    benchmark_parser.add_argument("--output", choices=("json",), default="json")

    args = parser.parse_args()
    if args.command == "validate-project-pack":
        result = validate_project_pack(Path(args.project_root).resolve())
        print(json.dumps(result, indent=2))
        return 0 if result["status"] == "pass" else 1

    if args.command == "benchmark-smoke":
        result = benchmark_smoke(Path(args.project_root).resolve())
        print(json.dumps(result, indent=2))
        return 0 if result["status"] == "pass" else 1

    parser.print_help()
    return 0
"""


def _validate_project_pack_py() -> str:
    return """from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def validate_project_pack(project_root: Path) -> dict[str, Any]:
    manifest_path = project_root / "pack.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    required_paths = ["AGENTS.md", "project-context.md", "pack.json"]
    required_paths.extend(manifest.get("post_bootstrap_read_order", []))

    directory_contract = manifest.get("directory_contract", {})
    if isinstance(directory_contract, dict):
        required_paths.extend(
            value
            for value in directory_contract.values()
            if isinstance(value, str)
        )

    missing = sorted(
        relative_path
        for relative_path in set(required_paths)
        if not (project_root / relative_path).exists()
    )
    status = "pass" if not missing else "fail"
    return {
        "status": status,
        "project_root": str(project_root),
        "pack_id": manifest.get("pack_id"),
        "pack_kind": manifest.get("pack_kind"),
        "checked_paths": sorted(set(required_paths)),
        "missing_paths": missing,
    }
"""


def _benchmark_smoke_py(benchmark_id: str) -> str:
    return f"""from __future__ import annotations

from pathlib import Path
from typing import Any


def benchmark_smoke(project_root: Path) -> dict[str, Any]:
    manifest_path = project_root / "pack.json"
    readiness_path = project_root / "status/readiness.json"
    benchmark_path = project_root / "benchmarks/active-set.json"

    missing = [
        str(path.relative_to(project_root))
        for path in (manifest_path, readiness_path, benchmark_path)
        if not path.exists()
    ]

    return {{
        "status": "pass" if not missing else "fail",
        "project_root": str(project_root),
        "benchmark_id": "{benchmark_id}",
        "checked_paths": [
            "pack.json",
            "status/readiness.json",
            "benchmarks/active-set.json",
        ],
        "missing_paths": missing,
    }}
"""


def _bootstrap_eval_placeholder(template_pack_id: str, benchmark_id: str) -> dict[str, Any]:
    return {
        "status": "not_run",
        "pack_id": template_pack_id,
        "benchmark_id": benchmark_id,
        "summary": "Bootstrap placeholder created by the template creation workflow.",
    }


def _ensure_new_template_id(factory_root: Path, template_pack_id: str) -> None:
    template_root = factory_root / "templates" / template_pack_id
    if template_root.exists():
        raise ValueError(f"template pack already exists: {template_pack_id}")
    registry = _load_object(factory_root / REGISTRY_TEMPLATE_PATH)
    entries = registry.get("entries", [])
    if not isinstance(entries, list):
        raise ValueError(f"{factory_root / REGISTRY_TEMPLATE_PATH}: entries must be an array")
    if any(isinstance(entry, dict) and entry.get("pack_id") == template_pack_id for entry in entries):
        raise ValueError(f"template pack already registered: {template_pack_id}")


def _resolve_template_personality_selection(
    factory_root: Path,
    planning: dict[str, Any],
) -> dict[str, Any] | None:
    selection = planning.get("personality_template_selection")
    if selection is None:
        return None
    if not isinstance(selection, dict):
        raise ValueError("personality_template_selection must be an object when present")

    template_id = selection.get("personality_template_id")
    if not isinstance(template_id, str) or not template_id.strip():
        raise ValueError("personality_template_selection.personality_template_id must be a non-empty string")
    selection_reason = selection.get("selection_reason")
    if not isinstance(selection_reason, str) or not selection_reason.strip():
        raise ValueError("personality_template_selection.selection_reason must be a non-empty string")
    apply_to_derived = selection.get("apply_to_derived_build_packs_by_default")
    if not isinstance(apply_to_derived, bool):
        raise ValueError(
            "personality_template_selection.apply_to_derived_build_packs_by_default must be a boolean"
        )

    catalog_entry = resolve_personality_template(factory_root, template_id.strip())
    return {
        "template_id": catalog_entry["template_id"],
        "display_name": catalog_entry["display_name"],
        "summary": catalog_entry["summary"],
        "selection_origin": "template_selected",
        "selection_reason": selection_reason.strip(),
        "catalog_path": PERSONALITY_TEMPLATE_CATALOG_PATH.as_posix(),
        "agent_context_lines": list(catalog_entry.get("agent_context_lines", [])),
        "project_context_lines": list(catalog_entry.get("project_context_lines", [])),
        "apply_to_derived_build_packs_by_default": apply_to_derived,
    }


def _validate_request_semantics(factory_root: Path, request: dict[str, Any]) -> dict[str, Any] | None:
    if request.get("runtime") != "python":
        raise ValueError("template creation currently supports runtime=python only")
    if request.get("scaffold_strategy") != "minimal_python_text_pack":
        raise ValueError("template creation currently supports scaffold_strategy=minimal_python_text_pack only")
    planning = request.get("planning_summary")
    if not isinstance(planning, dict):
        raise ValueError("planning_summary must be an object")
    if planning.get("reuse_active_template") is not False:
        raise ValueError("planning decision must justify create_new_template; reuse_active_template must be false")
    rationale = planning.get("new_template_rationale")
    if not isinstance(rationale, str) or not rationale.strip():
        raise ValueError("new_template_rationale is required when creating a new template")
    capability_family = planning.get("capability_family")
    if not isinstance(capability_family, str) or not capability_family.strip():
        raise ValueError("capability_family is required for template creation reusability planning")
    expected_variants = planning.get("expected_build_pack_variants")
    if not isinstance(expected_variants, list) or len(expected_variants) < 2:
        raise ValueError(
            "expected_build_pack_variants must describe at least two meaningful build-pack variants "
            "so the template stays a reusable capability pattern"
        )
    normalized_variants: list[str] = []
    for item in expected_variants:
        if not isinstance(item, str) or not item.strip():
            raise ValueError("expected_build_pack_variants must contain only non-empty strings")
        normalized_variants.append(item.strip())
    if len(set(normalized_variants)) < 2:
        raise ValueError("expected_build_pack_variants must contain at least two distinct variant descriptions")
    first_materialization_purpose = planning.get("first_materialization_purpose")
    if not isinstance(first_materialization_purpose, str) or not first_materialization_purpose.strip():
        raise ValueError("first_materialization_purpose is required so the first proving-ground build-pack is explicit")
    return _resolve_template_personality_selection(factory_root, planning)


def create_template_pack(factory_root: Path, request: dict[str, Any]) -> dict[str, Any]:
    resolved_personality_template = _validate_request_semantics(factory_root, request)

    preflight = validate_factory(factory_root)
    if not preflight["valid"]:
        raise ValueError("; ".join(preflight["errors"]) or "factory preflight validation failed")

    template_pack_id = str(request["template_pack_id"])
    display_name = str(request["display_name"])
    owning_team = str(request["owning_team"])
    requested_by = str(request["requested_by"])
    planning = dict(request["planning_summary"])
    project_goal = str(planning["project_goal"])
    capability_family = str(planning["capability_family"])
    benchmark_intent = str(planning["initial_benchmark_intent"])
    reason = str(planning["new_template_rationale"])

    _ensure_new_template_id(factory_root, template_pack_id)

    module_name = _module_name(template_pack_id)
    benchmark_id = f"{template_pack_id.replace('_', '-')}-smoke-small-001"

    now = read_now()
    created_at = isoformat_z(now)
    creation_id = f"create-template-{template_pack_id}-{timestamp_token(now)}"
    template_root = factory_root / "templates" / template_pack_id
    template_root.mkdir(parents=True, exist_ok=False)
    report_relative = Path("eval/history") / creation_id / "template-creation-report.json"
    report_full_path = template_root / report_relative
    registry_updated = False
    operation_log_updated = False

    try:
        pack_root_relative = f"templates/{template_pack_id}"

        _write_text(
            template_root / "AGENTS.md",
            _pack_agents(display_name, resolved_personality_template),
        )
        _write_text(
            template_root / "project-context.md",
            _project_context(module_name, benchmark_id, project_goal),
        )
        _write_text(template_root / "README.md", _pack_readme(display_name, template_pack_id, module_name))
        _write_text(template_root / "contracts/README.md", _contracts_readme())
        _write_text(template_root / "docs/specs/README.md", _docs_specs_readme())
        _write_text(template_root / "prompts/README.md", _prompts_readme())
        _write_text(template_root / "tests/README.md", _tests_readme())
        _write_text(template_root / ".gitignore", _gitignore())
        _write_text(template_root / "pyproject.toml", _pyproject(template_pack_id, display_name, module_name))
        _write_text(template_root / "src" / module_name / "__init__.py", _init_py())
        _write_text(template_root / "src" / module_name / "__main__.py", _main_py(module_name))
        _write_text(template_root / "src" / module_name / "cli.py", _cli_py(module_name))
        _write_text(
            template_root / "src" / module_name / "validate_project_pack.py",
            _validate_project_pack_py(),
        )
        _write_text(
            template_root / "src" / module_name / "benchmark_smoke.py",
            _benchmark_smoke_py(benchmark_id),
        )

        write_json(
            template_root / "pack.json",
            _pack_manifest(
                template_pack_id=template_pack_id,
                display_name=display_name,
                owning_team=owning_team,
                module_name=module_name,
                creation_id=creation_id,
                project_goal=project_goal,
                capability_family=capability_family,
                personality_template=_manifest_personality_template(resolved_personality_template),
            ),
        )
        write_json(
            template_root / "status/lifecycle.json",
            _lifecycle_state(
                template_pack_id=template_pack_id,
                creation_id=creation_id,
                created_at=created_at,
                requested_by=requested_by,
                reason=reason,
            ),
        )
        write_json(
            template_root / "status/readiness.json",
            _readiness_state(
                template_pack_id=template_pack_id,
                created_at=created_at,
                benchmark_id=benchmark_id,
                benchmark_objective=benchmark_intent,
            ),
        )
        write_json(template_root / "status/deployment.json", _deployment_state(template_pack_id))
        write_json(template_root / "status/retirement.json", _retirement_state(template_pack_id))
        write_json(template_root / "benchmarks/active-set.json", _active_set(template_pack_id, benchmark_id, benchmark_intent))
        write_json(template_root / "eval/latest/index.json", _eval_latest(template_pack_id, benchmark_id))
        write_json(
            template_root / "benchmarks/declarations" / f"{benchmark_id}.json",
            _benchmark_declaration(
                template_pack_id=template_pack_id,
                benchmark_id=benchmark_id,
                creation_id=creation_id,
                description=benchmark_intent,
            ),
        )
        write_json(
            template_root / "eval/history/bootstrap/not-run.json",
            _bootstrap_eval_placeholder(template_pack_id, benchmark_id),
        )
        _write_text(template_root / "dist/exports/.gitkeep", "")
        _write_text(template_root / ".pack-state/.gitkeep", "")

        registry_path = factory_root / REGISTRY_TEMPLATE_PATH
        registry = _load_object(registry_path)
        entries = registry.get("entries", [])
        if not isinstance(entries, list):
            raise ValueError(f"{registry_path}: entries must be an array")
        entries.append(
            {
                "active": True,
                "active_benchmark_ids": [benchmark_id],
                "latest_eval_index": f"{pack_root_relative}/eval/latest/index.json",
                "lifecycle_stage": "maintained",
                "notes": [
                    "Created through the PackFactory template creation workflow.",
                    f"creation_id={creation_id}",
                ],
                "pack_id": template_pack_id,
                "pack_kind": "template_pack",
                "pack_root": pack_root_relative,
                "ready_for_deployment": False,
                "retired_at": None,
                "retirement_file": "status/retirement.json",
                "retirement_state": "active",
            }
        )
        registry["updated_at"] = created_at
        write_json(registry_path, registry)
        registry_updated = True

        promotion_log_path = factory_root / PROMOTION_LOG_PATH
        promotion_log = _load_object(promotion_log_path)
        events = promotion_log.setdefault("events", [])
        if not isinstance(events, list):
            raise ValueError(f"{promotion_log_path}: events must be an array")
        events.append(
            {
                "event_type": "template_created",
                "creation_id": creation_id,
                "template_pack_id": template_pack_id,
                "template_creation_report_path": str(report_relative),
                "status": "completed",
            }
        )
        promotion_log["updated_at"] = created_at
        write_json(promotion_log_path, promotion_log)
        operation_log_updated = True

        report = {
            "schema_version": "template-creation-report/v1",
            "creation_id": creation_id,
            "status": "created",
            "template_pack_id": template_pack_id,
            "created_at": created_at,
            "created_by": requested_by,
            "planning_summary": planning,
            "scaffold_strategy": "minimal_python_text_pack",
            "artifact_paths": {
                "template_root": pack_root_relative,
                "pack_manifest": f"{pack_root_relative}/pack.json",
                "lifecycle_file": f"{pack_root_relative}/status/lifecycle.json",
                "readiness_file": f"{pack_root_relative}/status/readiness.json",
                "creation_report": f"{pack_root_relative}/{report_relative}",
            },
            "factory_mutations": {
                "registry_updated": registry_updated,
                "operation_log_updated": operation_log_updated,
                "post_write_factory_validation": "pass",
            },
            "next_recommended_actions": [
                "Inspect the new template pack.",
                "Run validate-project-pack inside the new template.",
                "Run the initial smoke benchmark when ready.",
                f"Materialize the first build-pack proving ground for `{planning['first_materialization_purpose']}`.",
            ],
        }
        manifest_personality_template = _manifest_personality_template(resolved_personality_template)
        if manifest_personality_template is not None:
            report["resolved_personality_template"] = manifest_personality_template
        write_json(report_full_path, report)
        report_errors = validate_json_document(
            report_full_path,
            schema_path(factory_root, "template-creation-report.schema.json"),
        )
        if report_errors:
            raise ValueError("; ".join(report_errors))

        validation_payload = validate_factory(factory_root)
        validation_status = "pass" if validation_payload["valid"] else "fail"
        report["factory_mutations"]["post_write_factory_validation"] = validation_status
        if validation_status != "pass":
            report["status"] = "failed"
            for event in reversed(events):
                if isinstance(event, dict) and event.get("creation_id") == creation_id:
                    event["status"] = "failed"
                    break
            write_json(promotion_log_path, promotion_log)
        write_json(report_full_path, report)
        if validation_status != "pass":
            message = "; ".join(validation_payload.get("errors", []))
            raise ValueError(message or "post-write factory validation failed")
    except Exception as exc:
        if operation_log_updated:
            try:
                promotion_log_path = factory_root / PROMOTION_LOG_PATH
                promotion_log = _load_object(promotion_log_path)
                events = promotion_log.get("events", [])
                if isinstance(events, list):
                    for event in reversed(events):
                        if isinstance(event, dict) and event.get("creation_id") == creation_id:
                            event["status"] = "failed"
                            break
                    write_json(promotion_log_path, promotion_log)
            except Exception:
                pass
        if report_full_path.exists():
            try:
                report = _load_object(report_full_path)
                report["status"] = "failed"
                factory_mutations = report.get("factory_mutations")
                if isinstance(factory_mutations, dict) and factory_mutations.get("post_write_factory_validation") == "pass":
                    factory_mutations["post_write_factory_validation"] = "fail"
                write_json(report_full_path, report)
            except Exception:
                pass
        write_json(
            template_root / ".pack-state/failed-operations" / f"{creation_id}.json",
            {
                "creation_id": creation_id,
                "created_at": created_at,
                "template_pack_id": template_pack_id,
                "status": "failed",
                "error": str(exc),
            },
        )
        raise

    return {
        "status": "created",
        "creation_id": creation_id,
        "template_pack_id": template_pack_id,
        "template_pack_root": str(template_root),
        "template_creation_report_path": str(report_full_path),
    }


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a new template pack from the minimal PackFactory scaffold.")
    parser.add_argument("--factory-root", required=True)
    parser.add_argument("--request-file", required=True)
    parser.add_argument("--output", choices=("json",), default="json")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        factory_root = resolve_factory_root(args.factory_root)
        request = _load_request(Path(args.request_file), factory_root)
        payload = create_template_pack(factory_root, request)
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0
    except Exception as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}, indent=2, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
