from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


def _run_check_json(input_path: Path) -> tuple[int, dict[str, Any]]:
    command = [
        sys.executable,
        "-m",
        "json_health_checker_template_pack",
        "check-json",
        "--input",
        str(input_path),
        "--require",
        "id",
        "--require",
        "status",
        "--output",
        "json",
    ]
    completed = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
    )
    try:
        result = json.loads(completed.stdout)
    except json.JSONDecodeError:
        result = {
            "status": "fail",
            "error": "invalid_cli_json_output",
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        }
    return completed.returncode, result


def benchmark_smoke(project_root: Path) -> dict[str, Any]:
    manifest_path = project_root / "pack.json"
    readiness_path = project_root / "status/readiness.json"
    benchmark_path = (
        project_root
        / "benchmarks/declarations/json-health-checker-build-pack-smoke-small-001.json"
    )

    missing = [
        str(path.relative_to(project_root))
        for path in (manifest_path, readiness_path, benchmark_path)
        if not path.exists()
    ]
    pass_case: dict[str, Any] | None = None
    fail_case: dict[str, Any] | None = None

    if not missing:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            pass_input = tmpdir_path / "pass.json"
            pass_input.write_text('{"id": 1, "status": "ok"}\n', encoding="utf-8")
            pass_returncode, pass_result = _run_check_json(pass_input)

            fail_input = tmpdir_path / "fail.json"
            fail_input.write_text('{"id": 1}\n', encoding="utf-8")
            fail_returncode, fail_result = _run_check_json(fail_input)

        pass_case = {
            "returncode": pass_returncode,
            "status": pass_result.get("status"),
            "missing_fields": pass_result.get("missing_fields", []),
        }
        fail_case = {
            "returncode": fail_returncode,
            "status": fail_result.get("status"),
            "missing_fields": fail_result.get("missing_fields", []),
        }

        if pass_returncode != 0 or pass_result.get("status") != "pass":
            missing.append("runtime:pass_case_failed")
        if (
            fail_returncode == 0
            or fail_result.get("status") != "fail"
            or fail_result.get("missing_fields") != ["status"]
        ):
            missing.append("runtime:fail_closed_case_failed")

    return {
        "status": "pass" if not missing else "fail",
        "project_root": str(project_root),
        "benchmark_id": "json-health-checker-build-pack-smoke-small-001",
        "checked_paths": [
            "pack.json",
            "status/readiness.json",
            "benchmarks/declarations/json-health-checker-build-pack-smoke-small-001.json",
        ],
        "runtime_checks": {
            "pass_case": pass_case,
            "fail_closed_case": fail_case,
        },
        "missing_paths": missing,
    }
