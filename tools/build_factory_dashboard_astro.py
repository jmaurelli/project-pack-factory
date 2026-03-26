#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Mapping, cast

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from factory_ops import load_json, resolve_factory_root, schema_path, validate_json_document, write_json
from generate_factory_dashboard import REPORT_SCHEMA_NAME, SNAPSHOT_SCHEMA_NAME


def _run_command(
    command: list[str],
    *,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        command,
        cwd=str(cwd) if cwd is not None else None,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        stderr = completed.stderr.strip()
        stdout = completed.stdout.strip()
        detail = stderr or stdout or "command failed without output"
        raise RuntimeError(f"Command failed: {' '.join(command)}\n{detail}")
    return completed


def _validate_generator_report(factory_root: Path, report_path: Path) -> dict[str, Any]:
    errors = validate_json_document(report_path, schema_path(factory_root, REPORT_SCHEMA_NAME))
    if errors:
        raise ValueError("\n".join(errors))
    payload = load_json(report_path)
    if not isinstance(payload, dict):
        raise ValueError(f"{report_path}: report must contain an object")
    report = cast(dict[str, Any], payload)
    if report.get("publication_mode") != "history_only":
        raise ValueError(f"{report_path}: expected publication_mode=history_only")
    if report.get("latest_published") is not False:
        raise ValueError(f"{report_path}: expected latest_published=false")
    required_fields = (
        "dashboard_build_id",
        "history_build_root",
        "snapshot_path",
        "report_path",
        "renderer",
        "renderer_output_root",
    )
    for field in required_fields:
        if not report.get(field):
            raise ValueError(f"{report_path}: missing required generator handoff field `{field}`")
    return report


def _generate_history_only_build(factory_root: Path, output_dir: Path) -> dict[str, Any]:
    command = [
        sys.executable,
        str(SCRIPT_DIR / "generate_factory_dashboard.py"),
        "--factory-root",
        str(factory_root),
        "--output-dir",
        str(output_dir),
        "--skip-latest-publish",
        "--report-format",
        "json",
    ]
    completed = _run_command(command, env=os.environ.copy())
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:  # pragma: no cover - fail-closed subprocess guard
        raise ValueError(f"Generator did not return valid JSON: {exc}") from exc
    report_path = Path(cast(str, payload["report_path"])).resolve()
    return _validate_generator_report(factory_root, report_path)


def _load_existing_generator_report(factory_root: Path, report_path: Path) -> dict[str, Any]:
    resolved_report = report_path.expanduser().resolve()
    return _validate_generator_report(factory_root, resolved_report)


def _validate_snapshot(factory_root: Path, snapshot_path: Path) -> None:
    errors = validate_json_document(snapshot_path, schema_path(factory_root, SNAPSHOT_SCHEMA_NAME))
    if errors:
        raise ValueError("\n".join(errors))


def _ensure_app_dependencies_installed(app_dir: Path) -> None:
    if (app_dir / "node_modules").exists():
        return
    _run_command(["npm", "ci", "--no-fund", "--no-audit"], cwd=app_dir, env=os.environ.copy())


def _run_astro_build(app_dir: Path, snapshot_path: Path, build_id: str, output_dir: Path) -> None:
    env = os.environ.copy()
    env["PACK_FACTORY_DASHBOARD_SNAPSHOT_PATH"] = str(snapshot_path)
    env["PACK_FACTORY_DASHBOARD_BUILD_ID"] = build_id
    env["PACK_FACTORY_DASHBOARD_OUTPUT_DIR"] = str(output_dir)
    _run_command(["npm", "run", "build"], cwd=app_dir, env=env)


def _validate_staged_astro_output(staged_root: Path) -> list[str]:
    required = [
      staged_root / "index.html",
      staged_root / "assets" / "dashboard.css",
      staged_root / "assets" / "dashboard.js",
    ]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise ValueError("Astro build is missing required artifacts:\n" + "\n".join(missing))
    return [str(path) for path in required]


def _finalize_history_build(
    factory_root: Path,
    *,
    generator_report: Mapping[str, Any],
    staged_root: Path,
    renderer_artifact_paths: list[str],
) -> dict[str, Any]:
    build_root = Path(cast(str, generator_report["history_build_root"]))
    report_path = build_root / "dashboard-report.json"
    final_index = build_root / "index.html"
    final_assets = build_root / "assets"
    final_assets.mkdir(parents=True, exist_ok=True)
    shutil.copy2(staged_root / "index.html", final_index)
    shutil.copy2(staged_root / "assets" / "dashboard.css", final_assets / "dashboard.css")
    shutil.copy2(staged_root / "assets" / "dashboard.js", final_assets / "dashboard.js")

    report = dict(generator_report)
    report["latest_published"] = True
    report["publication_mode"] = "published_latest"
    report["renderer"] = "astro"
    report["renderer_output_root"] = str(staged_root)
    report["renderer_artifact_paths"] = renderer_artifact_paths
    report["index_path"] = str(final_index)
    report["asset_paths"] = [
        str(final_assets / "dashboard.css"),
        str(final_assets / "dashboard.js"),
    ]
    report["report_path"] = str(report_path)
    write_json(report_path, report)
    errors = validate_json_document(report_path, schema_path(factory_root, REPORT_SCHEMA_NAME))
    if errors:
        raise ValueError("\n".join(errors))
    return report


def _publish_latest(history_build_root: Path, latest_root: Path) -> None:
    latest_tmp = latest_root.with_name(f"{latest_root.name}-tmp-{history_build_root.name}")
    if latest_tmp.exists():
        shutil.rmtree(latest_tmp)
    shutil.copytree(history_build_root, latest_tmp)
    if latest_root.exists():
        shutil.rmtree(latest_root)
    latest_tmp.rename(latest_root)


def build_factory_dashboard_astro(
    *,
    factory_root: Path,
    output_dir: Path,
    app_dir: Path,
    staging_root: Path,
    generator_report_path: Path | None = None,
) -> dict[str, Any]:
    if generator_report_path is None:
        generator_report = _generate_history_only_build(factory_root, output_dir)
    else:
        generator_report = _load_existing_generator_report(factory_root, generator_report_path)

    snapshot_path = Path(cast(str, generator_report["snapshot_path"])).resolve()
    build_id = cast(str, generator_report["dashboard_build_id"])
    history_build_root = Path(cast(str, generator_report["history_build_root"])).resolve()
    _validate_snapshot(factory_root, snapshot_path)

    staged_root = staging_root.expanduser().resolve() / build_id
    if staged_root.exists():
        shutil.rmtree(staged_root)
    staged_root.mkdir(parents=True, exist_ok=True)

    _ensure_app_dependencies_installed(app_dir)
    _run_astro_build(app_dir, snapshot_path, build_id, staged_root)
    renderer_artifact_paths = _validate_staged_astro_output(staged_root)
    final_report = _finalize_history_build(
        factory_root,
        generator_report=generator_report,
        staged_root=staged_root,
        renderer_artifact_paths=renderer_artifact_paths,
    )
    _publish_latest(history_build_root, output_dir)
    return final_report


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the Astro PackFactory dashboard from an immutable history-only snapshot.")
    parser.add_argument("--factory-root", required=True, help="Absolute path to the PackFactory root.")
    parser.add_argument(
        "--output-dir",
        default="/home/orchadmin/project-pack-factory/.pack-state/factory-dashboard/latest",
        help="Absolute path to the canonical latest dashboard output directory.",
    )
    parser.add_argument(
        "--app-dir",
        default="/home/orchadmin/project-pack-factory/apps/factory-dashboard",
        help="Absolute path to the Astro dashboard app root.",
    )
    parser.add_argument(
        "--staging-root",
        default="/home/orchadmin/project-pack-factory/.pack-state/factory-dashboard/astro-staging",
        help="Absolute path to the wrapper-owned Astro staging root.",
    )
    parser.add_argument(
        "--generator-report-path",
        help="Optional absolute path to an existing history-only generator report for replay/debug use.",
    )
    parser.add_argument("--report-format", choices=("json", "text"), default="text")
    args = parser.parse_args()

    try:
        result = build_factory_dashboard_astro(
            factory_root=resolve_factory_root(args.factory_root),
            output_dir=Path(args.output_dir).expanduser().resolve(),
            app_dir=Path(args.app_dir).expanduser().resolve(),
            staging_root=Path(args.staging_root).expanduser().resolve(),
            generator_report_path=Path(args.generator_report_path).expanduser().resolve()
            if args.generator_report_path
            else None,
        )
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if args.report_format == "json":
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"Built dashboard {result['dashboard_build_id']}")
        print(f"- latest output: {result['latest_output_root']}")
        print(f"- renderer: {result['renderer']}")
        print(f"- snapshot: {result['snapshot_path']}")
        print(f"- report: {result['report_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
