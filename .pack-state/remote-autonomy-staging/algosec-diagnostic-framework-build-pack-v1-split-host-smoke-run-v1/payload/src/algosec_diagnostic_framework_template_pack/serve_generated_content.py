from __future__ import annotations

import contextlib
import functools
import json
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from .runtime_baseline import DEFAULT_ARTIFACT_ROOT

LAYOUT_HOTFIX_STYLE = """
<style id="adf-layout-hotfix">
html:not([data-has-sidebar]) { --sl-content-width: 124rem; }
.main-pane { width: 100% !important; }
.content-panel > .sl-container {
  width: min(100%, 124rem) !important;
  max-width: none !important;
  margin-left: 0 !important;
  margin-right: auto !important;
}
.adf-cockpit-grid,
.adf-system-grid {
  grid-template-columns: 22rem minmax(0, 1fr) !important;
  align-items: start !important;
}
.adf-check pre,
.adf-check .expressive-code,
.adf-check .frame,
.adf-system-checkpoint pre,
.adf-system-checkpoint .expressive-code,
.adf-system-checkpoint .frame {
  width: min(100%, 88ch) !important;
  max-width: 88ch !important;
  margin-left: 0 !important;
  margin-right: auto !important;
}
</style>
""".strip()


def resolve_serving_root(
    *,
    project_root: Path,
    artifact_root: str | Path | None = None,
    site_root: str | Path | None = None,
) -> dict[str, Any]:
    baseline_root = project_root / (Path(artifact_root) if artifact_root else DEFAULT_ARTIFACT_ROOT)
    if site_root is not None:
        serving_root = project_root / Path(site_root)
        mode = "explicit_site_root"
    else:
        built_starlight_dist = baseline_root / "starlight-site" / "dist"
        if built_starlight_dist.is_dir():
            serving_root = built_starlight_dist
            mode = "built_starlight_dist"
        else:
            serving_root = baseline_root
            mode = "artifact_root"

    serving_root = serving_root.resolve()
    try:
        serving_root.relative_to(project_root)
    except ValueError as exc:
        raise ValueError("serving root must stay under the selected project root") from exc
    if not serving_root.exists() or not serving_root.is_dir():
        raise FileNotFoundError(f"serving root does not exist: {serving_root}")

    index_path = serving_root / "index.html"
    support_baseline_path = serving_root / "support-baseline.html"
    if index_path.exists():
        default_entry = "/"
    elif support_baseline_path.exists():
        default_entry = "/support-baseline.html"
    else:
        default_entry = None

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
    host: str = "0.0.0.0",
    port: int = 18082,
) -> dict[str, Any]:
    resolved = resolve_serving_root(
        project_root=project_root,
        artifact_root=artifact_root,
        site_root=site_root,
    )
    serving_root = resolved["serving_root"]
    default_entry = resolved["default_entry"]
    preview_url = f"http://{host}:{port}{default_entry or '/'}"
    return {
        "status": "pass",
        "host": host,
        "port": port,
        "serving_root": str(serving_root.relative_to(project_root)),
        "serving_mode": resolved["mode"],
        "default_entry": default_entry,
        "preview_url": preview_url,
    }


def serve_generated_content(
    *,
    project_root: Path,
    artifact_root: str | Path | None = None,
    site_root: str | Path | None = None,
    host: str = "0.0.0.0",
    port: int = 18082,
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
    default_entry = resolved["default_entry"]
    index_exists = (serving_root / "index.html").exists()

    class GeneratedContentHandler(SimpleHTTPRequestHandler):
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__(*args, directory=str(serving_root), **kwargs)

        def _resolved_request_path(self) -> Path:
            request_path = urlsplit(self.path).path
            translated = Path(self.translate_path(request_path))
            if translated.is_dir():
                translated = translated / "index.html"
            return translated

        def _serve_hotfixed_html(self, target_path: Path) -> bool:
            if not target_path.is_file() or target_path.suffix.lower() != ".html":
                return False
            html = target_path.read_text(encoding="utf-8")
            if 'id="adf-layout-hotfix"' not in html:
                if "</head>" in html:
                    html = html.replace("</head>", f"{LAYOUT_HOTFIX_STYLE}</head>", 1)
                else:
                    html = f"{LAYOUT_HOTFIX_STYLE}{html}"
            body = html.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return True

        def end_headers(self) -> None:
            # Keep the preview server fail-closed for layout and content edits so
            # operator navigation does not silently fall back to stale browser cache.
            self.send_header("Cache-Control", "no-store, no-cache, max-age=0, must-revalidate")
            self.send_header("Pragma", "no-cache")
            self.send_header("Expires", "0")
            super().end_headers()

        def do_GET(self) -> None:
            if (
                self.path in {"/", "/index.html"}
                and not index_exists
                and default_entry == "/support-baseline.html"
            ):
                self.send_response(302)
                self.send_header("Location", default_entry)
                self.end_headers()
                return
            if self._serve_hotfixed_html(self._resolved_request_path()):
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
