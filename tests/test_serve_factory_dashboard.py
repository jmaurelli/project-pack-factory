from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = ROOT / "tools"
sys.path.insert(0, str(TOOLS_DIR))

import serve_factory_dashboard as serve_tool


def test_dashboard_url_uses_localhost_for_wildcard_host() -> None:
    assert serve_tool._dashboard_url(host="0.0.0.0", port=8000) == "http://127.0.0.1:8000/"


def test_prepare_dashboard_output_uses_astro_wrapper(monkeypatch, tmp_path: Path) -> None:
    captured: list[list[str]] = []

    def fake_run_command(command: list[str], *, env: dict[str, str] | None = None):
        captured.append(command)
        class Result:
            stdout = json.dumps(
                {
                    "renderer": "astro",
                    "dashboard_build_id": "factory-dashboard-build-20260326t180000z",
                }
            )
        return Result()

    monkeypatch.setattr(serve_tool, "_run_command", fake_run_command)
    report = serve_tool._prepare_dashboard_output(
        factory_root=tmp_path,
        renderer="astro",
        output_dir=tmp_path / "latest",
    )

    assert report["renderer"] == "astro"
    assert "build_factory_dashboard_astro.py" in " ".join(captured[0])


def test_prepare_dashboard_output_uses_python_generator(monkeypatch, tmp_path: Path) -> None:
    captured: list[list[str]] = []

    def fake_run_command(command: list[str], *, env: dict[str, str] | None = None):
        captured.append(command)
        class Result:
            stdout = json.dumps(
                {
                    "renderer": "python",
                    "dashboard_build_id": "factory-dashboard-build-20260326t180100z",
                }
            )
        return Result()

    monkeypatch.setattr(serve_tool, "_run_command", fake_run_command)
    report = serve_tool._prepare_dashboard_output(
        factory_root=tmp_path,
        renderer="python",
        output_dir=tmp_path / "latest",
    )

    assert report["renderer"] == "python"
    assert "generate_factory_dashboard.py" in " ".join(captured[0])
