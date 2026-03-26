from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = ROOT / "tools"
sys.path.insert(0, str(TOOLS_DIR))

from factory_ops import load_json
from test_generate_factory_dashboard import _build_minimal_factory

import build_factory_dashboard_astro as astro_builder


def test_validate_generator_report_rejects_non_history_only(tmp_path: Path) -> None:
    factory_root = _build_minimal_factory(tmp_path)
    report_path = tmp_path / "dashboard-report.json"
    report_path.write_text(
        """
{
  "schema_version": "factory-dashboard-report/v1",
  "dashboard_build_id": "factory-dashboard-build-20260326t183000z",
  "generated_at": "2026-03-26T18:30:00Z",
  "output_root": "/tmp/out",
  "latest_output_root": "/tmp/out",
  "latest_published": true,
  "publication_mode": "published_latest",
  "renderer": "python",
  "renderer_output_root": "/tmp/history",
  "history_build_root": "/tmp/history",
  "snapshot_path": "/tmp/history/dashboard-snapshot.json",
  "index_path": "/tmp/history/index.html",
  "report_path": "/tmp/history/dashboard-report.json",
  "asset_paths": [
    "/tmp/history/assets/dashboard.css",
    "/tmp/history/assets/dashboard.js"
  ],
  "renderer_artifact_paths": [
    "/tmp/history/index.html"
  ],
  "source_trace": [],
  "source_count": 0,
  "mismatch_warning_count": 0,
  "mismatch_warnings": [],
  "freshness_thresholds": {
    "fresh_hours": 24,
    "stale_hours": 72,
    "recent_motion_hours": 96
  },
  "ranking_rules": [],
  "startup_benchmark_comparison": null,
  "validations": {
    "snapshot_schema": "pass",
    "report_schema": "pass",
    "errors": []
  },
  "summary_counts": {
    "high_priority": 1,
    "medium_priority": 0,
    "worth_watching": 0,
    "historical_baseline": 0,
    "ideas_lab": 0
  }
}
""".strip(),
        encoding="utf-8",
    )

    try:
        astro_builder._validate_generator_report(factory_root, report_path)
    except ValueError as exc:
        assert "publication_mode=history_only" in str(exc)
    else:  # pragma: no cover - fail-closed expectation
        raise AssertionError("expected history-only validation failure")


def test_build_factory_dashboard_astro_finalizes_and_publishes(tmp_path: Path, monkeypatch) -> None:
    factory_root = _build_minimal_factory(tmp_path)
    latest_root = factory_root / ".pack-state/factory-dashboard/latest"
    app_dir = tmp_path / "app"
    app_dir.mkdir()
    staging_root = tmp_path / "astro-staging"

    def fake_install(app_root: Path) -> None:
        assert app_root == app_dir

    def fake_build(app_root: Path, snapshot_path: Path, build_id: str, output_dir: Path) -> None:
        assert app_root == app_dir
        assert snapshot_path.exists()
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "assets").mkdir(parents=True, exist_ok=True)
        (output_dir / "index.html").write_text(
            f"<html><body><h1>Astro {build_id}</h1></body></html>",
            encoding="utf-8",
        )
        (output_dir / "assets" / "dashboard.css").write_text("body { color: #123; }\n", encoding="utf-8")
        (output_dir / "assets" / "dashboard.js").write_text("console.log('astro');\n", encoding="utf-8")

    monkeypatch.setattr(astro_builder, "_ensure_app_dependencies_installed", fake_install)
    monkeypatch.setattr(astro_builder, "_run_astro_build", fake_build)

    report = astro_builder.build_factory_dashboard_astro(
        factory_root=factory_root,
        output_dir=latest_root,
        app_dir=app_dir,
        staging_root=staging_root,
    )

    assert report["renderer"] == "astro"
    assert report["latest_published"] is True
    assert report["publication_mode"] == "published_latest"
    assert Path(report["index_path"]).read_text(encoding="utf-8").startswith("<html><body><h1>Astro")
    assert latest_root.exists()
    latest_report = load_json(latest_root / "dashboard-report.json")
    assert latest_report["renderer"] == "astro"
    assert (latest_root / "assets/dashboard.css").exists()
    assert (latest_root / "assets/dashboard.js").exists()
