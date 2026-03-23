#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import textwrap
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from factory_ops import (
    PROMOTION_LOG_PATH,
    REGISTRY_BUILD_PATH,
    discover_pack,
    isoformat_z,
    load_json,
    read_now,
    relative_path,
    resolve_factory_root,
    schema_path,
    timestamp_token,
    validate_json_document,
    write_json,
)

PACK_DOCUMENT_SCHEMAS = {
    "pack.json": "pack.schema.json",
    "status/lifecycle.json": "lifecycle.schema.json",
    "status/readiness.json": "readiness.schema.json",
    "status/deployment.json": "deployment.schema.json",
    "status/retirement.json": "retirement.schema.json",
    "benchmarks/active-set.json": "benchmark-active-set.schema.json",
    "eval/latest/index.json": "eval-latest-index.schema.json",
}


COPY_ROOT_NAMES = (
    "AGENTS.md",
    "project-context.md",
    "docs",
    "prompts",
    "contracts",
    "src",
    "tests",
    "benchmarks",
    "pyproject.toml",
    "uv.lock",
    "README.md",
    "Makefile",
    ".gitignore",
)
SKIP_ROOT_NAMES = {
    ".pack-state",
    "status",
}
TRANSIENT_NAMES = {
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    ".venv",
}

PORTABLE_RUNTIME_ROOT = ".packfactory-runtime"
PORTABLE_RUNTIME_TOOLS_DIR = f"{PORTABLE_RUNTIME_ROOT}/tools"
PORTABLE_RUNTIME_SCHEMAS_DIR = f"{PORTABLE_RUNTIME_ROOT}/schemas"
PORTABLE_RUNTIME_HELPER_MANIFEST = f"{PORTABLE_RUNTIME_ROOT}/manifest.json"
PORTABLE_RUNTIME_HELPER_SET_VERSION = "portable-build-pack-autonomy-runtime-helpers/v1"
PORTABLE_RUNTIME_MATERIALIZER_VERSION = "materialize_build_pack.py/v1"
PORTABLE_RUNTIME_SCHEMA_FILENAMES = (
    "portable-runtime-helper-manifest.schema.json",
    "readiness.schema.json",
    "eval-latest-index.schema.json",
    "autonomy-loop-event.schema.json",
    "autonomy-run-summary.schema.json",
)
PORTABLE_RUNTIME_TOOL_FILENAMES = (
    "factory_ops.py",
    "run_build_pack_readiness_eval.py",
    "record_autonomy_run.py",
)


def _load_object(path: Path) -> dict[str, Any]:
    payload = load_json(path)
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: JSON document must contain an object")
    return payload


def _load_request(request_path: Path, factory_root: Path) -> dict[str, Any]:
    errors = validate_json_document(
        request_path,
        schema_path(factory_root, "materialization-request.schema.json"),
    )
    if errors:
        raise ValueError("; ".join(errors))
    return _load_object(request_path)


def _copy_ignore(_directory: str, names: list[str]) -> set[str]:
    ignored = {name for name in names if name in TRANSIENT_NAMES or name.endswith(".egg-info")}
    ignored.update({"eval"} if "eval" in names else set())
    ignored.update({"dist"} if "dist" in names else set())
    return ignored


def _validate_source_template(factory_root: Path, template_root: Path) -> None:
    errors: list[str] = []
    for relative_document, schema_name in PACK_DOCUMENT_SCHEMAS.items():
        document_path = template_root / relative_document
        if not document_path.exists():
            errors.append(f"missing required template document: {relative_document}")
            continue
        errors.extend(validate_json_document(document_path, schema_path(factory_root, schema_name)))
    if errors:
        raise ValueError("; ".join(errors))


def _gate_id(benchmark_id: str) -> str:
    return benchmark_id.replace("-", "_")


def _load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


def _project_context_summary(project_context_text: str, fallback: str) -> str:
    for line in project_context_text.splitlines():
        candidate = line.strip()
        if not candidate or candidate.startswith("#"):
            continue
        return candidate
    return fallback


def _objective_id(pack_id: str) -> str:
    return f"{pack_id}_objective"


def _extract_project_goal(template_manifest: dict[str, Any], project_context_text: str) -> str | None:
    notes = template_manifest.get("notes", [])
    if isinstance(notes, list):
        for note in notes:
            if isinstance(note, str) and note.startswith("project_goal="):
                goal = note.split("=", 1)[1].strip()
                if goal:
                    return goal

    lines = project_context_text.splitlines()
    for index, line in enumerate(lines):
        if "project goal" not in line.lower():
            continue
        for candidate_line in lines[index + 1 :]:
            candidate = candidate_line.strip()
            if candidate.startswith("- "):
                return candidate[2:].strip()
    return None


def _build_directory_contract(
    *,
    runtime_evidence_export_dir: str | None = None,
    portable_runtime_tools_dir: str | None = None,
    portable_runtime_schemas_dir: str | None = None,
    portable_runtime_helper_manifest: str | None = None,
) -> dict[str, Any]:
    contract = {
        "docs_dir": "docs",
        "prompts_dir": "prompts",
        "contracts_dir": "contracts",
        "project_objective_file": "contracts/project-objective.json",
        "source_dir": "src",
        "tests_dir": "tests",
        "tasks_dir": "tasks",
        "task_backlog_file": "tasks/active-backlog.json",
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
        "work_state_file": "status/work-state.json",
        "lineage_dir": "lineage",
        "lineage_file": "lineage/source-template.json",
        "dist_dir": "dist",
        "candidate_release_dir": "dist/candidates",
        "immutable_release_dir": "dist/releases",
        "template_export_dir": None,
        "local_state_dir": ".pack-state",
        "portable_runtime_tools_dir": portable_runtime_tools_dir,
        "portable_runtime_schemas_dir": portable_runtime_schemas_dir,
        "portable_runtime_helper_manifest": portable_runtime_helper_manifest,
    }
    if runtime_evidence_export_dir is not None:
        contract["runtime_evidence_export_dir"] = runtime_evidence_export_dir
    return contract


def _runtime_evidence_export_helper_source() -> str:
    return textwrap.dedent(
        """
        #!/usr/bin/env python3
        from __future__ import annotations

        import argparse
        import hashlib
        import json
        import shutil
        import sys
        from datetime import datetime, timezone
        from pathlib import Path
        from typing import Any


        ALLOWED_RUN_ROOT = Path(".pack-state") / "autonomy-runs"
        EXPORT_ROOT = Path("dist") / "exports" / "runtime-evidence"
        RUN_SUMMARY_NAME = "run-summary.json"
        LOOP_EVENTS_NAME = "loop-events.jsonl"
        SUPPLEMENTARY_MEMORY_ROOT = Path(".pack-state") / "agent-memory"


        def _load_json(path: Path) -> dict[str, Any]:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                raise ValueError(f"{path}: JSON document must contain an object")
            return payload


        def _dump_json(path: Path, payload: dict[str, Any]) -> None:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(f"{json.dumps(payload, indent=2, sort_keys=True)}\\n", encoding="utf-8")


        def _sha256(path: Path) -> str:
            digest = hashlib.sha256()
            with path.open("rb") as handle:
                for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                    digest.update(chunk)
            return digest.hexdigest()


        def _isoformat_z() -> str:
            return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


        def _resolve_under(base: Path, candidate: str | Path) -> Path:
            path = Path(candidate)
            if path.is_absolute():
                raise ValueError(f"{candidate}: absolute paths are not allowed")
            resolved = (base / path).resolve()
            try:
                resolved.relative_to(base.resolve())
            except ValueError as exc:
                raise ValueError(f"{candidate}: path escapes the allowed base root") from exc
            return resolved


        def _media_type(path: Path) -> str:
            suffix = path.suffix.lower()
            if suffix == ".json":
                return "application/json"
            if suffix == ".jsonl":
                return "application/jsonl"
            return "text/plain; charset=utf-8"


        def _select_run_files(pack_root: Path, run_id: str, include_logs: list[str]) -> tuple[Path, list[Path]]:
            run_root = (pack_root / ALLOWED_RUN_ROOT / run_id).resolve()
            if not run_root.exists():
                raise ValueError(f"{run_root}: run directory does not exist")
            try:
                run_root.relative_to((pack_root / ALLOWED_RUN_ROOT).resolve())
            except ValueError as exc:
                raise ValueError("run directory must stay inside .pack-state/autonomy-runs") from exc

            selected: list[Path] = []
            summary_path = run_root / RUN_SUMMARY_NAME
            if not summary_path.exists():
                raise ValueError(f"{summary_path}: selected run is missing run-summary.json")
            selected.append(summary_path)

            loop_events_path = run_root / LOOP_EVENTS_NAME
            if loop_events_path.exists():
                selected.append(loop_events_path)

            for include in include_logs:
                include_path = _resolve_under(run_root, include)
                if include_path.is_dir():
                    raise ValueError(f"{include}: directory copies are not allowed")
                if not include_path.exists():
                    raise ValueError(f"{include}: included log does not exist")
                selected.append(include_path)

            return run_root, selected


        def _validate_loop_events(path: Path, run_id: str) -> None:
            for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
                if not line.strip():
                    continue
                payload = json.loads(line)
                if not isinstance(payload, dict):
                    raise ValueError(f"{path}:{line_number}: loop event must be a JSON object")
                if payload.get("run_id") != run_id:
                    raise ValueError(f"{path}:{line_number}: loop event run_id does not match selected run")


        def _copy_selected_artifacts(
            *,
            pack_root: Path,
            bundle_root: Path,
            run_root: Path,
            selected_files: list[Path],
        ) -> list[dict[str, Any]]:
            manifest: list[dict[str, Any]] = []
            for source_path in sorted({path.resolve() for path in selected_files}):
                if SUPPLEMENTARY_MEMORY_ROOT in source_path.parents:
                    raise ValueError("runtime-memory artifacts are not exportable in v1")
                try:
                    source_path.relative_to(run_root)
                except ValueError as exc:
                    raise ValueError(f"{source_path}: v1 export allows only files under the selected run root") from exc

                relative_source = source_path.relative_to(pack_root).as_posix()
                relative_bundle = Path("artifacts") / Path(relative_source).relative_to(Path(".pack-state") / "autonomy-runs" / run_root.name)
                target_path = bundle_root / relative_bundle
                target_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source_path, target_path)
                manifest.append(
                    {
                        "bundle_path": relative_bundle.as_posix(),
                        "source_pack_path": relative_source,
                        "sha256": _sha256(target_path),
                        "media_type": _media_type(source_path),
                        "required": source_path.name == RUN_SUMMARY_NAME,
                    }
                )
            return manifest


        def main(argv: list[str] | None = None) -> int:
            parser = argparse.ArgumentParser(description="Export bounded runtime evidence from a build pack.")
            parser.add_argument("--pack-root", required=True)
            parser.add_argument("--run-id", required=True)
            parser.add_argument("--exported-by", required=True)
            parser.add_argument("--output-dir", default=str(EXPORT_ROOT))
            parser.add_argument("--output", choices=("json",), default="json")
            parser.add_argument("--include-log", action="append", default=[])
            args = parser.parse_args(argv)

            pack_root = Path(args.pack_root).expanduser().resolve()
            if not pack_root.is_absolute():
                raise ValueError("--pack-root must resolve to an absolute path")
            output_dir = Path(args.output_dir)
            if output_dir.is_absolute():
                raise ValueError("--output-dir must be a relative path")

            pack_manifest = _load_json(pack_root / "pack.json")
            if pack_manifest.get("pack_kind") != "build_pack":
                raise ValueError("runtime evidence export only supports build packs")

            run_root, selected_files = _select_run_files(pack_root, args.run_id, args.include_log)
            run_summary = _load_json(run_root / RUN_SUMMARY_NAME)
            if run_summary.get("pack_id") != pack_manifest.get("pack_id"):
                raise ValueError("selected run pack_id does not match pack.json")
            if run_summary.get("run_id") != args.run_id:
                raise ValueError("selected run_id does not match run-summary.json")

            export_id = f"external-runtime-evidence-{args.run_id}-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
            bundle_root = (pack_root / output_dir / export_id).resolve()
            try:
                bundle_root.relative_to(pack_root)
            except ValueError as exc:
                raise ValueError("--output-dir must stay under the pack root") from exc
            bundle_root.mkdir(parents=True, exist_ok=False)

            artifact_manifest = _copy_selected_artifacts(
                pack_root=pack_root,
                bundle_root=bundle_root,
                run_root=run_root,
                selected_files=selected_files,
            )
            loop_events_path = run_root / LOOP_EVENTS_NAME
            if loop_events_path.exists():
                _validate_loop_events(loop_events_path, args.run_id)
            final_snapshot = run_summary.get("final_snapshot", {})
            if not isinstance(final_snapshot, dict):
                final_snapshot = {}

            control_plane_mutations = {
                "readiness_updated": False,
                "work_state_updated": False,
                "eval_latest_updated": False,
                "deployment_updated": False,
                "registry_updated": False,
                "release_artifacts_updated": False,
            }
            bundle = {
                "schema_version": "external-runtime-evidence-bundle/v1",
                "export_id": export_id,
                "generated_at": _isoformat_z(),
                "pack_id": pack_manifest.get("pack_id"),
                "pack_kind": "build_pack",
                "run_id": args.run_id,
                "exported_by": args.exported_by,
                "bundle_root": str(bundle_root.relative_to(pack_root)),
                "source_runtime_roots": [str(run_root.relative_to(pack_root))],
                "authority_class": "supplementary_runtime_evidence",
                "control_plane_mutations": control_plane_mutations,
                "artifact_manifest": artifact_manifest,
                "summary": {
                    "stop_reason": run_summary.get("stop_reason"),
                    "started_at": run_summary.get("started_at"),
                    "ended_at": run_summary.get("ended_at"),
                    "resume_count": run_summary.get("resume_count"),
                    "escalation_count": run_summary.get("escalation_count"),
                    "task_completion_rate": run_summary.get("metrics", {}).get("task_completion_rate") if isinstance(run_summary.get("metrics"), dict) else None,
                    "readiness_state_in_selected_run": final_snapshot.get("readiness_state"),
                    "ready_for_deployment_in_selected_run": final_snapshot.get("ready_for_deployment"),
                },
            }
            _dump_json(bundle_root / "bundle.json", bundle)

            result = {
                "status": "completed",
                "generated_at": bundle["generated_at"],
                "export_id": export_id,
                "bundle_root": str(bundle_root.relative_to(pack_root)),
                "copied_artifact_paths": [entry["bundle_path"] for entry in artifact_manifest],
            }
            if args.output == "json":
                print(json.dumps(result, indent=2, sort_keys=True))
            return 0


        if __name__ == "__main__":
            raise SystemExit(main())
        """
    ).lstrip()


def _runtime_evidence_export_command() -> str:
    return (
        "python3 src/pack_export_runtime_evidence.py "
        "--pack-root . "
        "--run-id <run-id> "
        "--exported-by <actor> "
        "--output-dir dist/exports/runtime-evidence "
        "--output json"
    )


def _build_pack_agents_text(
    *,
    pack_id: str,
    display_name: str,
    source_template_id: str,
    runtime_is_python: bool,
) -> str:
    lines = [
        f"# {display_name} Build Pack Agent Context",
        "",
        "This directory is a PackFactory build pack, not a source template.",
        "",
        "Read `status/lifecycle.json`, `status/readiness.json`, and `status/deployment.json` first.",
        "Then read `pack.json` and use `pack.json.post_bootstrap_read_order` as the canonical post-bootstrap traversal contract.",
        "When `pack.json.directory_contract` declares `contracts/project-objective.json`, `tasks/active-backlog.json`, or `status/work-state.json`, read those files as canonical pack-local control-plane handoff files.",
        "Treat `project-context.md` as inherited background context unless the manifest and status files say otherwise.",
    ]
    if runtime_is_python:
        lines.extend(
            [
                "",
                "This build pack can export bounded runtime evidence when running externally.",
                "Use `pack.json.entrypoints.export_runtime_evidence_command` when that capability is present.",
                "Export bundles remain supplementary runtime evidence only.",
            ]
        )
    lines.extend(
        [
            "",
            f"Derived from template `{source_template_id}`.",
            f"Pack id: `{pack_id}`.",
        ]
    )
    return "\n".join(lines) + "\n"


def _copy_template_content(template_root: Path, target_root: Path) -> tuple[list[str], list[str]]:
    copied_paths: list[str] = []
    skipped_paths: list[str] = sorted(SKIP_ROOT_NAMES | {"eval", "dist"})
    for name in COPY_ROOT_NAMES:
        source = template_root / name
        if not source.exists():
            continue
        target = target_root / name
        if source.is_dir():
            shutil.copytree(source, target, ignore=_copy_ignore)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
        copied_paths.append(name)
    return copied_paths, skipped_paths


def _synthesize_build_pack(
    *,
    factory_root: Path,
    template_root: Path,
    target_root: Path,
    request: dict[str, Any],
    materialization_id: str,
    generated_at: str,
) -> dict[str, Any]:
    template_manifest = _load_object(template_root / "pack.json")
    template_lifecycle = _load_object(template_root / "status/lifecycle.json")
    template_readiness = _load_object(template_root / "status/readiness.json")
    template_active_set = _load_object(template_root / "benchmarks/active-set.json")
    project_context_text = _load_text(template_root / "project-context.md")
    runtime = str(template_manifest["runtime"])
    template_entrypoints = dict(template_manifest["entrypoints"])
    runtime_evidence_export_dir = None
    portability_enabled = runtime == "python"
    if portability_enabled:
        template_entrypoints["export_runtime_evidence_command"] = _runtime_evidence_export_command()
        runtime_evidence_export_dir = "dist/exports/runtime-evidence"

    pack_id = str(request["target_build_pack_id"])
    display_name = str(request["target_display_name"])
    target_version = str(request["target_version"])
    target_revision = str(request["target_revision"])
    materialized_by = str(request["materialized_by"])
    reason = str(request["materialization_reason"])
    source_template_id = str(request["source_template_id"])
    project_goal = _extract_project_goal(template_manifest, project_context_text)

    pack_manifest = {
        "schema_version": "pack-manifest/v2",
        "pack_id": pack_id,
        "pack_kind": "build_pack",
        "display_name": display_name,
        "owning_team": template_manifest["owning_team"],
        "runtime": template_manifest["runtime"],
        "bootstrap_read_order": template_manifest["bootstrap_read_order"],
        "post_bootstrap_read_order": [
            "status/lifecycle.json",
            "status/readiness.json",
            "status/retirement.json",
            "status/deployment.json",
            "lineage/source-template.json",
            "contracts/project-objective.json",
            "tasks/active-backlog.json",
            "status/work-state.json",
            "benchmarks/active-set.json",
            "eval/latest/index.json",
        ],
        "entrypoints": template_entrypoints,
        "directory_contract": _build_directory_contract(
            runtime_evidence_export_dir=runtime_evidence_export_dir,
            portable_runtime_tools_dir=PORTABLE_RUNTIME_TOOLS_DIR if portability_enabled else None,
            portable_runtime_schemas_dir=PORTABLE_RUNTIME_SCHEMAS_DIR if portability_enabled else None,
            portable_runtime_helper_manifest=PORTABLE_RUNTIME_HELPER_MANIFEST if portability_enabled else None,
        ),
        "identity_source": "pack.json",
        "notes": [
            f"Materialized from template `{source_template_id}`.",
            f"materialization_id={materialization_id}",
        ],
    }

    objective_id = _objective_id(pack_id)
    objective_summary = _project_context_summary(
        project_goal or project_context_text,
        f"Advance `{pack_id}` from materialized build-pack state to validated, benchmarked, deployment-ready state.",
    )

    benchmarks = template_active_set.get("active_benchmarks", [])
    if not isinstance(benchmarks, list):
        raise ValueError("benchmarks/active-set.json active_benchmarks must be an array")

    required_gates: list[dict[str, Any]] = [
        {
            "gate_id": "validate_build_pack_contract",
            "mandatory": True,
            "status": "not_run",
            "summary": "Build-pack contract validation has not been executed yet.",
            "last_run_at": None,
            "evidence_paths": [],
        }
    ]
    benchmark_results: list[dict[str, Any]] = []
    report_relative = f"eval/history/{materialization_id}/materialization-report.json"
    for benchmark in benchmarks:
        if not isinstance(benchmark, dict):
            continue
        benchmark_id = str(benchmark["benchmark_id"])
        objective = str(benchmark.get("objective", "Inherited benchmark has not been executed yet."))
        required_gates.append(
            {
                "gate_id": _gate_id(benchmark_id),
                "mandatory": bool(benchmark.get("required_for_readiness", True)),
                "status": "not_run",
                "summary": objective,
                "last_run_at": None,
                "evidence_paths": [],
            }
        )
        benchmark_results.append(
            {
                "benchmark_id": benchmark_id,
                "status": "not_run",
                "latest_run_id": materialization_id,
                "run_artifact_path": report_relative,
                "summary_artifact_path": report_relative,
            }
        )

    lifecycle = {
        "schema_version": "pack-lifecycle/v2",
        "pack_id": pack_id,
        "pack_kind": "build_pack",
        "lifecycle_stage": "testing",
        "state_reason": reason,
        "current_version": target_version,
        "current_revision": target_revision,
        "promotion_target": "testing",
        "updated_at": generated_at,
        "updated_by": materialized_by,
    }
    readiness = {
        "schema_version": "pack-readiness/v2",
        "pack_id": pack_id,
        "pack_kind": "build_pack",
        "readiness_state": "in_progress",
        "ready_for_deployment": False,
        "last_evaluated_at": generated_at,
        "blocking_issues": [
            "This build pack has been materialized but has not been evaluated yet."
        ],
        "recommended_next_actions": [
            "Start with the canonical validation task in tasks/active-backlog.json.",
            "Run the inherited benchmark task after validation passes.",
        ],
        "required_gates": required_gates,
    }
    retirement = {
        "schema_version": "pack-retirement/v1",
        "pack_id": pack_id,
        "pack_kind": "build_pack",
        "retirement_state": "active",
        "retired_at": None,
        "retired_by": None,
        "retirement_reason": None,
        "superseded_by_pack_id": None,
        "retirement_report_path": None,
        "removed_deployment_pointer_paths": [],
        "retained_artifacts": {
            "eval_history": True,
            "release_artifacts": True,
            "lineage": True,
        },
        "operator_notes": [],
    }
    deployment = {
        "schema_version": "pack-deployment/v2",
        "pack_id": pack_id,
        "pack_kind": "build_pack",
        "deployment_state": "not_deployed",
        "active_environment": "none",
        "active_release_id": None,
        "active_release_path": None,
        "deployment_pointer_path": None,
        "deployment_transaction_id": None,
        "projection_state": "not_required",
        "last_promoted_at": None,
        "last_verified_at": None,
        "last_rollback": None,
        "deployment_notes": [
            "Newly materialized build pack; no active deployment candidate."
        ],
    }
    template_version = str(template_lifecycle["current_version"])
    template_revision = str(template_lifecycle["current_revision"])
    lineage = {
        "schema_version": "pack-lineage/v2",
        "build_pack_id": pack_id,
        "source_template_id": source_template_id,
        "source_template_version": template_version,
        "source_template_revision": template_revision,
        "derivation_mode": "copied",
        "sync_state": "current",
        "last_sync_at": generated_at,
        "last_sync_summary": f"materialization_id={materialization_id}",
        "inherited_entrypoints": sorted(template_manifest["entrypoints"].keys()),
        "inherited_contracts": sorted(
            path.stem.replace(".schema", "")
            for path in (target_root / "contracts").glob("*")
            if path.is_file()
        ),
    }
    eval_latest = {
        "schema_version": "pack-eval-index/v1",
        "pack_id": pack_id,
        "pack_kind": "build_pack",
        "updated_at": generated_at,
        "benchmark_results": benchmark_results or [
            {
                "benchmark_id": "validate_build_pack_contract",
                "status": "not_run",
                "latest_run_id": materialization_id,
                "run_artifact_path": report_relative,
                "summary_artifact_path": report_relative,
            }
        ],
    }
    project_objective = {
        "schema_version": "project-objective/v1",
        "pack_id": pack_id,
        "source_template_id": source_template_id,
        "materialization_id": materialization_id,
        "generated_at": generated_at,
        "objective_id": objective_id,
        "objective_summary": objective_summary,
        "problem_statement": project_context_text,
        "intended_inputs": [
            "Pack-local source code and configuration under the materialized build-pack.",
            "Validation and benchmark commands declared in pack.json entrypoints.",
            "Current readiness, eval, and benchmark state for this build-pack.",
        ],
        "intended_outputs": [
            "A schema-valid build-pack with current validation and benchmark evidence.",
            "Updated readiness and eval state that supports promotion decisions.",
        ],
        "success_criteria": [
            "The build-pack validation command completes successfully and records passing evidence.",
            "The inherited benchmark command completes successfully and updates readiness evidence.",
        ],
        "metrics": [
            {
                "metric_id": "validation_gate_status",
                "summary": "Validation gate reaches a passing state.",
                "target": "validate_build_pack_contract=pass",
                "evidence_hint": "status/readiness.json and eval/latest/index.json",
            },
            {
                "metric_id": "benchmark_completion",
                "summary": "All inherited readiness benchmarks complete successfully.",
                "target": "required inherited benchmark gates=pass or waived",
                "evidence_hint": "benchmarks/active-set.json and eval/latest/index.json",
            },
        ],
        "non_goals": [
            "Changing deployment state outside the existing PackFactory workflows.",
            "Creating new tests or benchmarks without explicit operator approval.",
        ],
        "completion_definition": [
            "All starter tasks in tasks/active-backlog.json are completed or explicitly resolved through existing workflows.",
            "The build-pack is ready for review, ready for deploy, or awaiting the next PackFactory workflow step.",
        ],
        "promotion_readiness_requirements": [
            "Build-pack validation must pass with recorded evidence.",
            "Inherited required benchmark gates must pass or be waived.",
            "Readiness state must be updated through existing bounded validation and benchmark surfaces.",
        ],
    }
    validation_task_id = "run_build_pack_validation"
    benchmark_task_id = "run_inherited_benchmarks"
    task_backlog = {
        "schema_version": "task-backlog/v1",
        "pack_id": pack_id,
        "objective_id": objective_id,
        "generated_at": generated_at,
        "tasks": [
            {
                "task_id": validation_task_id,
                "summary": "Run the validation readiness-evaluation workflow and capture canonical validation evidence.",
                "status": "in_progress",
                "objective_link": objective_id,
                "acceptance_criteria": [
                    "The validation readiness-evaluation workflow exits successfully.",
                    "The validation gate records passing evidence in status/readiness.json.",
                ],
                "validation_commands": [
                    _portable_runtime_command("validation-only")
                    if portability_enabled
                    else "python3 ../../tools/run_build_pack_readiness_eval.py --pack-root . --mode validation-only --invoked-by autonomous-loop"
                ],
                "files_in_scope": [
                    "pack.json",
                    "status/readiness.json",
                    "eval/latest/index.json",
                ],
                "dependencies": [],
                "blocked_by": [],
                "escalation_conditions": [
                    "Validation reports schema or contract failures that the current task scope cannot resolve safely.",
                ],
                "completion_signals": [
                    "validate_build_pack_contract reaches pass state.",
                    "Validation evaluation evidence is recorded under eval/history and linked from status/readiness.json.",
                ],
            },
            {
                "task_id": benchmark_task_id,
                "summary": "Run the benchmark readiness-evaluation workflow after validation passes.",
                "status": "pending",
                "objective_link": objective_id,
                "acceptance_criteria": [
                    "The benchmark readiness-evaluation workflow exits successfully.",
                    "Inherited benchmark gates update from not_run to pass or waived.",
                ],
                "validation_commands": [
                    _portable_runtime_command("benchmark-only")
                    if portability_enabled
                    else "python3 ../../tools/run_build_pack_readiness_eval.py --pack-root . --mode benchmark-only --invoked-by autonomous-loop"
                ],
                "files_in_scope": [
                    "benchmarks/active-set.json",
                    "status/readiness.json",
                    "eval/latest/index.json",
                ],
                "dependencies": [validation_task_id],
                "blocked_by": [],
                "escalation_conditions": [
                    "Benchmark output fails to update readiness or eval state through the existing bounded surfaces.",
                ],
                "completion_signals": [
                    "Benchmark evaluation evidence records results in eval/latest/index.json.",
                    "Required benchmark gates advance to pass or waived in status/readiness.json.",
                ],
            },
        ],
    }
    work_state = {
        "schema_version": "work-state/v1",
        "pack_id": pack_id,
        "objective_id": objective_id,
        "autonomy_state": "actively_building",
        "active_task_id": validation_task_id,
        "next_recommended_task_id": validation_task_id,
        "pending_task_ids": [benchmark_task_id],
        "blocked_task_ids": [],
        "completed_task_ids": [],
        "last_outcome": "stopped",
        "last_outcome_at": generated_at,
        "last_validation_results": [],
        "last_agent_action": "Materialized the build-pack and seeded objective, backlog, and work-state files.",
        "resume_instructions": [
            "Read the objective, backlog, and work-state files before editing code.",
            "Run the validation task before attempting benchmark execution or deployment workflows.",
        ],
        "stop_conditions": [
            "Stop when deployment or promotion becomes the next valid action under existing PackFactory workflows.",
            "Stop and escalate if the next action would require changing registry, deployment pointer, or promotion state directly.",
        ],
        "escalation_state": "none",
    }
    return {
        "pack_manifest": pack_manifest,
        "lifecycle": lifecycle,
        "readiness": readiness,
        "retirement": retirement,
        "deployment": deployment,
        "lineage": lineage,
        "eval_latest": eval_latest,
        "project_objective": project_objective,
        "task_backlog": task_backlog,
        "work_state": work_state,
    }


def _write_runtime_evidence_export_helper(target_root: Path) -> None:
    helper_path = target_root / "src/pack_export_runtime_evidence.py"
    helper_path.parent.mkdir(parents=True, exist_ok=True)
    helper_path.write_text(_runtime_evidence_export_helper_source(), encoding="utf-8")


def _portable_runtime_helper_source_root() -> Path:
    return SCRIPT_DIR / "portable_runtime_helpers"


def _portable_runtime_schema_source_root(factory_root: Path) -> Path:
    return factory_root / "docs/specs/project-pack-factory/schemas"


def _portable_runtime_command(mode: str) -> str:
    return (
        "python3 .packfactory-runtime/tools/run_build_pack_readiness_eval.py "
        f"--pack-root . --mode {mode} --invoked-by autonomous-loop"
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _seed_portable_runtime_helpers(
    *,
    factory_root: Path,
    target_root: Path,
    generated_at: str,
    materialized_by: str,
) -> dict[str, Any]:
    helper_source_root = _portable_runtime_helper_source_root()
    schema_source_root = _portable_runtime_schema_source_root(factory_root)
    runtime_root = target_root / PORTABLE_RUNTIME_ROOT
    tools_root = runtime_root / "tools"
    schemas_root = runtime_root / "schemas"
    tools_root.mkdir(parents=True, exist_ok=True)
    schemas_root.mkdir(parents=True, exist_ok=True)

    tool_paths: list[str] = []
    schema_paths: list[str] = []
    helper_entries: list[dict[str, Any]] = []

    for filename in PORTABLE_RUNTIME_TOOL_FILENAMES:
        source_path = helper_source_root / filename
        target_path = tools_root / filename
        shutil.copy2(source_path, target_path)
        relative = relative_path(target_root, target_path)
        tool_paths.append(relative)
        helper_entries.append(
            {
                "relative_path": relative,
                "sha256": _sha256(target_path),
                "size_bytes": target_path.stat().st_size,
            }
        )

    for filename in PORTABLE_RUNTIME_SCHEMA_FILENAMES:
        source_path = schema_source_root / filename
        target_path = schemas_root / filename
        shutil.copy2(source_path, target_path)
        relative = relative_path(target_root, target_path)
        schema_paths.append(relative)
        helper_entries.append(
            {
                "relative_path": relative,
                "sha256": _sha256(target_path),
                "size_bytes": target_path.stat().st_size,
            }
        )

    manifest = {
        "schema_version": "portable-runtime-helper-manifest/v1",
        "portable_runtime_helper_set_version": PORTABLE_RUNTIME_HELPER_SET_VERSION,
        "materialized_at": generated_at,
        "materialized_by": materialized_by,
        "materializer_version": PORTABLE_RUNTIME_MATERIALIZER_VERSION,
        "tools": tool_paths,
        "schemas": schema_paths,
        "helper_entries": helper_entries,
        "seeded_by_materializer": True,
    }
    write_json(runtime_root / "manifest.json", manifest)
    return manifest


def materialize_build_pack(factory_root: Path, request: dict[str, Any]) -> dict[str, Any]:
    source_template_id = str(request["source_template_id"])
    target_build_pack_id = str(request["target_build_pack_id"])
    display_name = str(request["target_display_name"])
    materialized_by = str(request["materialized_by"])
    target_version = str(request["target_version"])
    target_revision = str(request["target_revision"])

    source = discover_pack(factory_root, source_template_id)
    if source.pack_kind != "template_pack":
        raise ValueError(f"{source_template_id} is not a template_pack")
    source_retirement = _load_object(source.pack_root / "status/retirement.json")
    source_lifecycle = _load_object(source.pack_root / "status/lifecycle.json")
    if source_retirement.get("retirement_state") != "active":
        raise ValueError("source template is not active")
    if source_lifecycle.get("lifecycle_stage") == "retired":
        raise ValueError("source template is retired")
    _validate_source_template(factory_root, source.pack_root)

    target_root = factory_root / "build-packs" / target_build_pack_id
    if target_root.exists():
        raise ValueError(f"target build pack already exists: {target_build_pack_id}")
    build_registry_path = factory_root / REGISTRY_BUILD_PATH
    build_registry = _load_object(build_registry_path)
    entries = build_registry.get("entries", [])
    if not isinstance(entries, list):
        raise ValueError(f"{build_registry_path}: entries must be an array")
    if any(isinstance(entry, dict) and entry.get("pack_id") == target_build_pack_id for entry in entries):
        raise ValueError(f"target build pack already registered: {target_build_pack_id}")

    now = read_now()
    generated_at = isoformat_z(now)
    materialization_id = f"materialize-{target_build_pack_id}-{timestamp_token(now)}"
    target_root.mkdir(parents=True, exist_ok=False)
    try:
        copied_paths, skipped_paths = _copy_template_content(source.pack_root, target_root)
        for relative_dir in (
            "status",
            "tasks",
            "lineage",
            "eval/latest",
            "eval/history",
            "dist/candidates",
            "dist/releases",
            "dist/exports",
            ".pack-state",
        ):
            (target_root / relative_dir).mkdir(parents=True, exist_ok=True)
        state = _synthesize_build_pack(
            factory_root=factory_root,
            template_root=source.pack_root,
            target_root=target_root,
            request=request,
            materialization_id=materialization_id,
            generated_at=generated_at,
        )

        pack_root_relative = f"build-packs/{target_build_pack_id}"
        write_json(target_root / "pack.json", state["pack_manifest"])
        write_json(target_root / "status/lifecycle.json", state["lifecycle"])
        write_json(target_root / "status/readiness.json", state["readiness"])
        write_json(target_root / "status/retirement.json", state["retirement"])
        write_json(target_root / "status/deployment.json", state["deployment"])
        write_json(target_root / "status/work-state.json", state["work_state"])
        write_json(target_root / "contracts/project-objective.json", state["project_objective"])
        write_json(target_root / "tasks/active-backlog.json", state["task_backlog"])
        write_json(target_root / "lineage/source-template.json", state["lineage"])
        write_json(target_root / "eval/latest/index.json", state["eval_latest"])
        runtime_is_python = state["pack_manifest"]["runtime"] == "python"
        write_text_path = target_root / "AGENTS.md"
        write_text_path.write_text(
            _build_pack_agents_text(
                pack_id=target_build_pack_id,
                display_name=display_name,
                source_template_id=source_template_id,
                runtime_is_python=runtime_is_python,
            ),
            encoding="utf-8",
        )
        if runtime_is_python:
            (target_root / "dist/exports/runtime-evidence").mkdir(parents=True, exist_ok=True)
            _write_runtime_evidence_export_helper(target_root)
            _seed_portable_runtime_helpers(
                factory_root=factory_root,
                target_root=target_root,
                generated_at=generated_at,
                materialized_by=materialized_by,
            )

        registry_entry = {
            "active": True,
            "active_release_id": None,
            "deployment_pointer": None,
            "deployment_state": "not_deployed",
            "latest_eval_index": f"{pack_root_relative}/eval/latest/index.json",
            "lifecycle_stage": "testing",
            "notes": [
                f"Derived from template `{source_template_id}` via PackFactory materialization.",
                f"materialization_id={materialization_id}",
            ],
            "pack_id": target_build_pack_id,
            "pack_kind": "build_pack",
            "pack_root": pack_root_relative,
            "ready_for_deployment": False,
            "retirement_file": "status/retirement.json",
            "retirement_state": "active",
            "retired_at": None,
        }
        entries.append(registry_entry)
        build_registry["updated_at"] = generated_at
        write_json(build_registry_path, build_registry)

        promotion_log_path = factory_root / PROMOTION_LOG_PATH
        promotion_log = _load_object(promotion_log_path)
        events = promotion_log.setdefault("events", [])
        if not isinstance(events, list):
            raise ValueError(f"{promotion_log_path}: events must be an array")

        report_relative = Path("eval/history") / materialization_id / "materialization-report.json"
        report = {
            "schema_version": "build-pack-materialization-report/v1",
            "materialization_id": materialization_id,
            "generated_at": generated_at,
            "source_template_id": source_template_id,
            "target_build_pack_id": target_build_pack_id,
            "source_template_root": f"templates/{source_template_id}",
            "target_build_pack_root": pack_root_relative,
            "materialized_by": materialized_by,
            "target_version": target_version,
            "target_revision": target_revision,
            "copy_summary": {
                "copied_paths": copied_paths,
                "skipped_paths": skipped_paths,
            },
            "lineage_path": f"{pack_root_relative}/lineage/source-template.json",
            "registry_update": {
                "registry_path": "registry/build-packs.json",
                "pack_id": target_build_pack_id,
                "lifecycle_stage": "testing",
                "retirement_state": "active",
                "deployment_state": "not_deployed",
            },
            "operation_log_update": {
                "promotion_log_path": "registry/promotion-log.json",
                "event_type": "materialized",
                "materialization_id": materialization_id,
                "target_build_pack_id": target_build_pack_id,
                "materialization_report_path": str(report_relative),
            },
            "actions": [
                {
                    "action_id": "copy_template_content",
                    "status": "completed",
                    "target_path": pack_root_relative,
                    "summary": "Copied bounded template content into the new build pack.",
                },
                {
                    "action_id": "write_build_pack_manifest",
                    "status": "completed",
                    "target_path": f"{pack_root_relative}/pack.json",
                    "summary": "Wrote the schema-valid build-pack manifest.",
                },
                {
                    "action_id": "write_lineage",
                    "status": "completed",
                    "target_path": f"{pack_root_relative}/lineage/source-template.json",
                    "summary": "Recorded template lineage and inherited contract metadata.",
                },
                {
                    "action_id": "write_status_files",
                    "status": "completed",
                    "target_path": f"{pack_root_relative}/status",
                    "summary": "Wrote initial lifecycle, readiness, retirement, deployment, and work-state files.",
                },
                {
                    "action_id": "rewrite_build_pack_agents",
                    "status": "completed",
                    "target_path": f"{pack_root_relative}/AGENTS.md",
                    "summary": "Rewrote the build-pack AGENTS file to match the derived build-pack runtime model.",
                },
                *(
                    [
                        {
                            "action_id": "seed_runtime_evidence_export_helper",
                            "status": "completed",
                            "target_path": f"{pack_root_relative}/src/pack_export_runtime_evidence.py",
                            "summary": "Seeded the standalone runtime evidence export helper for Python build packs.",
                        },
                        {
                            "action_id": "seed_portable_runtime_helpers",
                            "status": "completed",
                            "target_path": f"{pack_root_relative}/{PORTABLE_RUNTIME_HELPER_MANIFEST}",
                            "summary": "Seeded the bounded portable runtime helper bundle for autonomy-capable Python build packs.",
                        }
                    ]
                    if runtime_is_python
                    else []
                ),
                {
                    "action_id": "update_registry_entry",
                    "status": "completed",
                    "target_path": "registry/build-packs.json",
                    "summary": "Registered the materialized build pack as active and not deployed.",
                },
                {
                    "action_id": "append_operation_log",
                    "status": "completed",
                    "target_path": "registry/promotion-log.json",
                    "summary": "Appended a materialized event for later agents.",
                },
                {
                    "action_id": "write_materialization_report",
                    "status": "completed",
                    "target_path": f"{pack_root_relative}/{report_relative}",
                    "summary": "Wrote the terminal materialization evidence report.",
                },
            ],
            "evidence_paths": [
                f"{pack_root_relative}/{report_relative}",
                f"{pack_root_relative}/eval/latest/index.json",
                f"{pack_root_relative}/lineage/source-template.json",
                f"{pack_root_relative}/AGENTS.md",
                *(
                    [
                        f"{pack_root_relative}/src/pack_export_runtime_evidence.py",
                        f"{pack_root_relative}/{PORTABLE_RUNTIME_HELPER_MANIFEST}",
                    ]
                    if runtime_is_python
                    else []
                ),
            ],
        }

        events.append(
            {
                "event_type": "materialized",
                "materialization_id": materialization_id,
                "source_template_id": source_template_id,
                "target_build_pack_id": target_build_pack_id,
                "materialization_report_path": str(report_relative),
                "status": "completed",
            }
        )
        promotion_log["updated_at"] = generated_at
        write_json(promotion_log_path, promotion_log)
        write_json(target_root / report_relative, report)
    except Exception as exc:
        failure_summary = {
            "materialization_id": materialization_id,
            "generated_at": generated_at,
            "source_template_id": source_template_id,
            "target_build_pack_id": target_build_pack_id,
            "status": "failed",
            "error": str(exc),
        }
        write_json(
            target_root / ".pack-state/failed-operations" / f"{materialization_id}.json",
            failure_summary,
        )
        raise

    return {
        "status": "completed",
        "materialization_id": materialization_id,
        "source_template_id": source_template_id,
        "target_build_pack_id": target_build_pack_id,
        "target_build_pack_root": str(target_root),
        "materialization_report_path": str(target_root / report_relative),
    }


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Materialize a build pack from a template pack.")
    parser.add_argument("--factory-root", required=True)
    parser.add_argument("--request-file", required=True)
    parser.add_argument("--output", choices=("json",), default="json")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        factory_root = resolve_factory_root(args.factory_root)
        request = _load_request(Path(args.request_file), factory_root)
        payload = materialize_build_pack(factory_root, request)
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0
    except Exception as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}, indent=2, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
