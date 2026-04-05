from __future__ import annotations

import contextlib
import functools
import json
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from .starlight_site import DEFAULT_REVIEW_SHELL_ARTIFACT_ROOT


def resolve_serving_root(
    *,
    project_root: Path,
    artifact_root: str | Path | None = None,
    site_root: str | Path | None = None,
) -> dict[str, Any]:
    if site_root is not None:
        candidate_root = (project_root / Path(site_root)).resolve()
        mode = "explicit_site_root"
    else:
        artifact_root_path = Path(artifact_root) if artifact_root is not None else DEFAULT_REVIEW_SHELL_ARTIFACT_ROOT
        candidate_root = (project_root / artifact_root_path / "starlight-site").resolve()
        mode = "default_starlight_site"

    built_dist = candidate_root / "dist"
    if built_dist.is_dir():
        serving_root = built_dist
        mode = "built_starlight_dist"
    else:
        serving_root = candidate_root

    if not serving_root.exists() or not serving_root.is_dir():
        raise FileNotFoundError(f"serving root does not exist: {serving_root}")

    index_path = serving_root / "index.html"
    default_entry = "/" if index_path.exists() else None
    return {
        "serving_root": serving_root,
        "mode": mode,
        "default_entry": default_entry,
    }


def describe_generated_content_server(
    *,
    project_root: Path,
    artifact_root: str | Path | None = None,
    site_root: str | Path | None = None,
    host: str = "127.0.0.1",
    port: int = 18083,
) -> dict[str, Any]:
    resolved = resolve_serving_root(
        project_root=project_root,
        artifact_root=artifact_root,
        site_root=site_root,
    )
    serving_root = resolved["serving_root"]
    preview_url = f"http://{host}:{port}{resolved['default_entry'] or '/'}"
    return {
        "status": "pass",
        "host": host,
        "port": port,
        "serving_root": str(serving_root.relative_to(project_root)),
        "serving_mode": resolved["mode"],
        "default_entry": resolved["default_entry"],
        "preview_url": preview_url,
    }


def serve_generated_content(
    *,
    project_root: Path,
    artifact_root: str | Path | None = None,
    site_root: str | Path | None = None,
    host: str = "127.0.0.1",
    port: int = 18083,
    dry_run: bool = False,
) -> dict[str, Any]:
    description = describe_generated_content_server(
        project_root=project_root,
        artifact_root=artifact_root,
        site_root=site_root,
        host=host,
        port=port,
    )
    if dry_run:
        return description

    resolved = resolve_serving_root(
        project_root=project_root,
        artifact_root=artifact_root,
        site_root=site_root,
    )
    serving_root = resolved["serving_root"]

    class GeneratedContentHandler(SimpleHTTPRequestHandler):
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__(*args, directory=str(serving_root), **kwargs)

        def end_headers(self) -> None:
            self.send_header("Cache-Control", "no-store, no-cache, max-age=0, must-revalidate")
            self.send_header("Pragma", "no-cache")
            self.send_header("Expires", "0")
            super().end_headers()

        def do_GET(self) -> None:
            request_path = urlsplit(self.path).path
            if request_path == "/" and not (serving_root / "index.html").exists():
                self.send_error(404, "generated site root exists but has not been built yet")
                return
            super().do_GET()

        def log_message(self, format: str, *args: Any) -> None:
            return

    handler = functools.partial(GeneratedContentHandler)
    with ThreadingHTTPServer((host, port), handler) as httpd:
        print(json.dumps(description, indent=2))
        with contextlib.suppress(KeyboardInterrupt):
            httpd.serve_forever()
    return description
