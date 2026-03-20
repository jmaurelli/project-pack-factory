from __future__ import annotations

import json
import sys
from pathlib import Path

from click.testing import CliRunner


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def _src() -> Path:
    return _root() / "src"


def test_build_run_manifest_returns_machine_readable_payload() -> None:
    sys.path.insert(0, str(_src()))
    from ai_native_package.run_manifest import build_run_manifest

    payload = build_run_manifest(
        run_id="run-001",
        task_name="demo-build",
        project_root="/srv/projects/demo-build",
        selected_profile="python-cli-click",
        command=["python3 -m demo_build --help", "python3 -m demo_build --help"],
        validation=["pytest -q", "make validate"],
        artifact=["/tmp/demo/build-plan.json"],
        note=["baseline run"],
        outcome_status="pass",
        outcome_summary="Initial benchmark run succeeded.",
        setup_time_seconds=12.5,
        execution_time_seconds=34.0,
        validation_time_seconds=5.25,
        clarification_count=1,
        validation_failures=0,
        files_created=8,
        files_changed=3,
    )

    assert payload["schema_version"] == "build-run-manifest/v1"
    assert payload["generated_at"].endswith("Z")
    assert payload["producer"] == "ai-native-codex-package-template"
    assert payload["commands"] == ["python3 -m demo_build --help"]
    assert payload["validations"] == ["pytest -q", "make validate"]
    assert payload["outcome"] == {"status": "pass", "summary": "Initial benchmark run succeeded."}


def test_write_run_manifest_persists_json(tmp_path: Path) -> None:
    sys.path.insert(0, str(_src()))
    from ai_native_package.run_manifest import build_run_manifest, write_run_manifest

    payload = build_run_manifest(
        run_id="run-002",
        task_name="demo-build",
        selected_profile="python-cli-click",
        outcome_status="pass",
    )
    output_path = tmp_path / "run-manifest.json"
    written = write_run_manifest(payload, output_path=output_path)

    assert Path(written).exists()
    written_payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert written_payload["run_id"] == "run-002"
    assert written_payload["generated_at"].endswith("Z")
    assert written_payload["producer"] == "ai-native-codex-package-template"


def test_cli_build_run_manifest_writes_default_path(tmp_path: Path) -> None:
    sys.path.insert(0, str(_src()))
    from ai_native_package.cli import build_app

    project_root = tmp_path / "demo-project"
    project_root.mkdir()
    runner = CliRunner()
    result = runner.invoke(
        build_app(),
        [
            "build-run-manifest",
            "--run-id",
            "run-003",
            "--task-name",
            "demo-build",
            "--selected-profile",
            "python-cli-click",
            "--project-root",
            str(project_root),
            "--command",
            "python3 -m demo_build --help",
            "--validation",
            "make validate",
            "--outcome-status",
            "pass",
            "--outcome-summary",
            "CLI run succeeded.",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["manifest_path"].endswith(".ai-native-codex-package-template/run-manifests/run-003.json")
    assert Path(payload["manifest_path"]).exists()
