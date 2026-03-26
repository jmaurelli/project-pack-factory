#!/usr/bin/env python3
from __future__ import annotations

import argparse
import functools
import http.server
import json
import os
import socketserver
import subprocess
import sys
from pathlib import Path
from typing import Any, cast

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from factory_ops import resolve_factory_root


def _run_command(command: list[str], *, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
    if completed.returncode != 0:
        stderr = completed.stderr.strip()
        stdout = completed.stdout.strip()
        detail = stderr or stdout or "command failed without output"
        raise RuntimeError(f"Command failed: {' '.join(command)}\n{detail}")
    return completed


def _prepare_dashboard_output(
    *,
    factory_root: Path,
    renderer: str,
    output_dir: Path,
) -> dict[str, Any]:
    env = os.environ.copy()
    if renderer == "astro":
        command = [
            sys.executable,
            str(SCRIPT_DIR / "build_factory_dashboard_astro.py"),
            "--factory-root",
            str(factory_root),
            "--output-dir",
            str(output_dir),
            "--app-dir",
            str(factory_root / "apps/factory-dashboard"),
            "--staging-root",
            str(factory_root / ".pack-state/factory-dashboard/astro-staging"),
            "--report-format",
            "json",
        ]
    elif renderer == "python":
        command = [
            sys.executable,
            str(SCRIPT_DIR / "generate_factory_dashboard.py"),
            "--factory-root",
            str(factory_root),
            "--output-dir",
            str(output_dir),
            "--report-format",
            "json",
        ]
    else:  # pragma: no cover - argparse constrains this
        raise ValueError(f"unsupported renderer: {renderer}")
    completed = _run_command(command, env=env)
    payload = json.loads(completed.stdout)
    if not isinstance(payload, dict):
        raise ValueError("dashboard build command did not return a JSON object")
    return cast(dict[str, Any], payload)


def _dashboard_url(*, host: str, port: int) -> str:
    if host == "0.0.0.0":
        host = "127.0.0.1"
    return f"http://{host}:{port}/"


def serve_dashboard(
    *,
    directory: Path,
    host: str,
    port: int,
) -> None:
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(directory))
    class ThreadingTCPServer(socketserver.ThreadingTCPServer):
        allow_reuse_address = True
    with ThreadingTCPServer((host, port), handler) as httpd:
        httpd.serve_forever()


def main() -> int:
    parser = argparse.ArgumentParser(description="Build and serve the PackFactory dashboard at a local HTTP URL.")
    parser.add_argument("--factory-root", required=True, help="Absolute path to the PackFactory root.")
    parser.add_argument(
        "--renderer",
        choices=("astro", "python"),
        default="astro",
        help="Renderer to publish before serving. Astro is the default operator-facing path.",
    )
    parser.add_argument(
        "--output-dir",
        default="/home/orchadmin/project-pack-factory/.pack-state/factory-dashboard/latest",
        help="Absolute path to the published dashboard output directory to serve.",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Host interface to bind.")
    parser.add_argument("--port", type=int, default=8000, help="HTTP port to bind.")
    parser.add_argument(
        "--skip-build",
        action="store_true",
        help="Serve the current published dashboard without rebuilding it first.",
    )
    args = parser.parse_args()

    factory_root = resolve_factory_root(args.factory_root)
    output_dir = Path(args.output_dir).expanduser().resolve()
    build_report: dict[str, Any] | None = None

    try:
        if not args.skip_build:
            build_report = _prepare_dashboard_output(
                factory_root=factory_root,
                renderer=args.renderer,
                output_dir=output_dir,
            )
        if not (output_dir / "index.html").exists():
            raise FileNotFoundError(f"dashboard index is missing: {output_dir / 'index.html'}")
        print(f"Serving PackFactory dashboard at {_dashboard_url(host=args.host, port=args.port)}")
        print(f"- directory: {output_dir}")
        if build_report is not None:
            print(f"- renderer: {build_report.get('renderer', args.renderer)}")
            print(f"- build: {build_report.get('dashboard_build_id', 'unknown')}")
        serve_dashboard(directory=output_dir, host=args.host, port=args.port)
    except KeyboardInterrupt:
        return 0
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
