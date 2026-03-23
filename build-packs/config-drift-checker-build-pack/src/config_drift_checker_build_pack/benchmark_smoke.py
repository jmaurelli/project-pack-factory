from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

BENCHMARK_ID = "config-drift-checker-build-pack-smoke-small-001"


def _run_check_drift(
    *,
    baseline_path: Path,
    candidate_path: Path,
    rules_path: Path | None = None,
) -> tuple[int, dict[str, Any]]:
    command = [
        sys.executable,
        "-m",
        "config_drift_checker_build_pack",
        "check-drift",
        "--baseline",
        str(baseline_path),
        "--candidate",
        str(candidate_path),
        "--output",
        "json",
    ]
    if rules_path is not None:
        command.extend(["--rules", str(rules_path)])
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
        / "benchmarks/declarations/config-drift-checker-build-pack-smoke-small-001.json"
    )
    fixture_path = project_root / "tests/fixtures/no-drift-sample.json"

    missing = [
        str(path.relative_to(project_root))
        for path in (manifest_path, readiness_path, benchmark_path, fixture_path)
        if not path.exists()
    ]
    runtime_checks: dict[str, Any] = {}

    if not missing:
        fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            pass_baseline = tmpdir_path / "pass-baseline.json"
            pass_candidate = tmpdir_path / "pass-candidate.json"
            pass_baseline.write_text(
                json.dumps(fixture["baseline"], indent=2) + "\n",
                encoding="utf-8",
            )
            pass_candidate.write_text(
                json.dumps(fixture["candidate"], indent=2) + "\n",
                encoding="utf-8",
            )
            pass_returncode, pass_result = _run_check_drift(
                baseline_path=pass_baseline,
                candidate_path=pass_candidate,
            )

            review_baseline = tmpdir_path / "review-baseline.json"
            review_candidate = tmpdir_path / "review-candidate.yaml"
            review_baseline.write_text('{"service": {"timeout_seconds": 30}}\n', encoding="utf-8")
            review_candidate.write_text("service:\n  timeout_seconds: 45\n", encoding="utf-8")
            review_returncode, review_result = _run_check_drift(
                baseline_path=review_baseline,
                candidate_path=review_candidate,
            )

            fail_rules = tmpdir_path / "fail-rules.yaml"
            fail_rules.write_text(
                "severity_overrides:\n  service.timeout_seconds: blocking\n",
                encoding="utf-8",
            )
            fail_returncode, fail_result = _run_check_drift(
                baseline_path=review_baseline,
                candidate_path=review_candidate,
                rules_path=fail_rules,
            )

        runtime_checks = {
            "pass_case": {
                "returncode": pass_returncode,
                "status": pass_result.get("status"),
                "counts": pass_result.get("counts", {}),
            },
            "review_required_case": {
                "returncode": review_returncode,
                "status": review_result.get("status"),
                "counts": review_result.get("counts", {}),
            },
            "blocking_case": {
                "returncode": fail_returncode,
                "status": fail_result.get("status"),
                "counts": fail_result.get("counts", {}),
            },
        }

        if pass_returncode != 0 or pass_result.get("status") != "pass":
            missing.append("runtime:pass_case_failed")
        if review_returncode != 2 or review_result.get("status") != "review_required":
            missing.append("runtime:review_required_case_failed")
        if fail_returncode != 1 or fail_result.get("status") != "fail":
            missing.append("runtime:blocking_case_failed")

    return {
        "status": "pass" if not missing else "fail",
        "project_root": str(project_root),
        "benchmark_id": BENCHMARK_ID,
        "checked_paths": [
            "pack.json",
            "status/readiness.json",
            "benchmarks/declarations/config-drift-checker-build-pack-smoke-small-001.json",
            "tests/fixtures/no-drift-sample.json",
        ],
        "runtime_checks": runtime_checks,
        "missing_paths": missing,
    }
