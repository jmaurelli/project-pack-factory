from __future__ import annotations

import hashlib
import json
import shutil
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from factory_ops import load_json
from validate_factory import validate_factory


PORTABLE_PACK_ID = "release-evidence-summarizer-build-pack-v4"
TOOL_COMMANDS = {
    "run_build_pack_validation": "python3 .packfactory-runtime/tools/run_build_pack_readiness_eval.py --pack-root . --mode validation-only --invoked-by autonomous-loop",
    "run_inherited_benchmarks": "python3 .packfactory-runtime/tools/run_build_pack_readiness_eval.py --pack-root . --mode benchmark-only --invoked-by autonomous-loop",
}


def _copy_factory(tmp_path: Path) -> Path:
    destination = tmp_path / "factory"

    def _ignore(_dir: str, names: list[str]) -> set[str]:
        return {
            name
            for name in names
            if name in {".git", ".venv", "__pycache__", ".pytest_cache", ".ruff_cache", ".mypy_cache"}
            or name.endswith(".egg-info")
        }

    shutil.copytree(ROOT, destination, ignore=_ignore)
    return destination


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(f"{json.dumps(payload, indent=2, sort_keys=True)}\n", encoding="utf-8")


def _portable_helper_setup(pack_root: Path) -> None:
    runtime_root = pack_root / ".packfactory-runtime"
    tools_dir = runtime_root / "tools"
    schemas_dir = runtime_root / "schemas"
    tools_dir.mkdir(parents=True, exist_ok=True)
    schemas_dir.mkdir(parents=True, exist_ok=True)

    helper_files = {
        runtime_root / "tools/run_build_pack_readiness_eval.py": "#!/usr/bin/env python3\nprint('ready')\n",
        runtime_root / "tools/record_autonomy_run.py": "#!/usr/bin/env python3\nprint('record')\n",
        runtime_root / "tools/factory_ops.py": "def resolve(project_root):\n    return project_root\n",
        runtime_root / "schemas/portable-helper-output.schema.json": {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
            "additionalProperties": False,
            "required": ["status"],
            "properties": {
                "status": {
                    "const": "ok"
                }
            },
        },
    }
    for path, payload in helper_files.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(payload, str):
            path.write_text(payload, encoding="utf-8")
        else:
            _write_json(path, payload)

    helper_paths = [
        ".packfactory-runtime/tools/run_build_pack_readiness_eval.py",
        ".packfactory-runtime/tools/record_autonomy_run.py",
        ".packfactory-runtime/tools/factory_ops.py",
        ".packfactory-runtime/schemas/portable-helper-output.schema.json",
    ]
    manifest = {
        "schema_version": "portable-runtime-helper-manifest/v1",
        "portable_runtime_helper_set_version": "portable-helper-set/v1",
        "materialized_at": "2026-03-23T15:00:00Z",
        "materialized_by": "pytest",
        "materializer_version": "pytest-1",
        "tools": helper_paths[:3],
        "schemas": helper_paths[3:],
        "helper_entries": [
            {
                "relative_path": relative_path,
                "sha256": _sha256(pack_root / relative_path),
                "size_bytes": (pack_root / relative_path).stat().st_size,
            }
            for relative_path in helper_paths
        ],
        "seeded_by_materializer": True,
    }
    _write_json(runtime_root / "manifest.json", manifest)

    manifest_path = pack_root / "pack.json"
    pack_manifest = load_json(manifest_path)
    contract = pack_manifest["directory_contract"]
    contract["portable_runtime_tools_dir"] = ".packfactory-runtime/tools"
    contract["portable_runtime_schemas_dir"] = ".packfactory-runtime/schemas"
    contract["portable_runtime_helper_manifest"] = ".packfactory-runtime/manifest.json"
    _write_json(manifest_path, pack_manifest)

    backlog_path = pack_root / "tasks/active-backlog.json"
    backlog = load_json(backlog_path)
    for task in backlog["tasks"]:
        command = TOOL_COMMANDS.get(task["task_id"])
        if command is not None:
            task["validation_commands"] = [command]
    _write_json(backlog_path, backlog)


def _portable_factory(tmp_path: Path) -> Path:
    factory_root = _copy_factory(tmp_path)
    _portable_helper_setup(factory_root / f"build-packs/{PORTABLE_PACK_ID}")
    return factory_root


def test_validate_factory_accepts_portable_runtime_helpers_contract(tmp_path: Path) -> None:
    factory_root = _portable_factory(tmp_path)
    result = validate_factory(factory_root)

    assert result["valid"] is True
    assert result["error_count"] == 0


class PortableRuntimeHelperContractTests(unittest.TestCase):
    def test_validate_factory_rejects_portable_runtime_helpers_regressions(self) -> None:
        cases = [
            (
                lambda pack_root: (pack_root / ".packfactory-runtime/manifest.json").unlink(),
                "portable_runtime_helper_manifest",
            ),
            (
                lambda pack_root: shutil.rmtree(pack_root / ".packfactory-runtime/schemas"),
                "portable_runtime_schemas_dir",
            ),
            (
                lambda pack_root: (pack_root / ".packfactory-runtime/tools/record_autonomy_run.py").unlink(),
                "record_autonomy_run.py",
            ),
            (
                lambda pack_root: _write_json(
                    pack_root / "tasks/active-backlog.json",
                    {
                        **load_json(pack_root / "tasks/active-backlog.json"),
                        "tasks": [
                            {
                                **task,
                                "validation_commands": [
                                    "python3 ../../tools/run_build_pack_readiness_eval.py --pack-root . --mode validation-only --invoked-by autonomous-loop"
                                ]
                                if task["task_id"] == "run_build_pack_validation"
                                else task["validation_commands"],
                            }
                            for task in load_json(pack_root / "tasks/active-backlog.json")["tasks"]
                        ],
                    },
                ),
                "../../tools/",
            ),
        ]

        for mutator, expected_error in cases:
            with self.subTest(expected_error=expected_error):
                factory_root = _portable_factory(Path(self._testMethodName))
                pack_root = factory_root / f"build-packs/{PORTABLE_PACK_ID}"
                mutator(pack_root)

                result = validate_factory(factory_root)

                self.assertFalse(result["valid"])
                self.assertTrue(any(expected_error in error for error in result["errors"]))
