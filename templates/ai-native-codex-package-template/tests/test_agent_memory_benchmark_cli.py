from __future__ import annotations

import json
import sys
from pathlib import Path

from click.testing import CliRunner


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def _src() -> Path:
    return _root() / "src"


def _build_app():
    sys.path.insert(0, str(_src()))
    from ai_native_package.cli import build_app

    return build_app()


def test_benchmark_agent_memory_cli_writes_outputs(tmp_path: Path) -> None:
    runner = CliRunner()
    fixture_root = tmp_path / "fixture"
    scorecard_path = tmp_path / "agent-memory-scorecard.json"
    snapshot_path = tmp_path / "agent-memory-snapshot.json"

    result = runner.invoke(
        _build_app(),
        [
            "benchmark-agent-memory",
            "--fixture-root",
            str(fixture_root),
            "--output-path",
            str(scorecard_path),
            "--snapshot-output-path",
            str(snapshot_path),
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["all_checks_passed"] is True
    assert payload["output_paths"]["scorecard_path"] == str(scorecard_path.resolve())
    assert payload["output_paths"]["snapshot_path"] == str(snapshot_path.resolve())
    assert json.loads(snapshot_path.read_text(encoding="utf-8"))["reader"] == "agent-memory-reader"
