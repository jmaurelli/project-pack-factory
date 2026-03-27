from __future__ import annotations

import contextlib
import functools
import json
import re
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from .runtime_baseline import DEFAULT_ARTIFACT_ROOT

STRAY_LITERAL_DIV_BLOCK = re.compile(
    r'\s*<div class="expressive-code"><figure class="frame not-content"><figcaption class="header"></figcaption>'
    r'<pre data-language="plaintext"><code><div class="ec-line"><div class="code"><span[^>]*>&#x3C;/div></span>'
    r'</div></div></code></pre><div class="copy"><div aria-live="polite"></div>'
    r'<button title="Copy to clipboard" data-copied="Copied!" data-code="</div>"><div></div></button>'
    r'</div></figure></div>',
    re.DOTALL,
)

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
  --ec-brdRad: 0.8rem !important;
  width: min(100%, 88ch) !important;
  max-width: 88ch !important;
  margin-left: 0 !important;
  margin-right: auto !important;
}
.adf-check .expressive-code .frame,
.adf-system-checkpoint .expressive-code .frame {
  border-radius: calc(var(--ec-brdRad) + var(--ec-brdWd)) !important;
  overflow: hidden !important;
}
:root[data-theme='light'] .adf-check .expressive-code,
:root[data-theme='light'] .adf-system-checkpoint .expressive-code {
  --ec-brdCol: color-mix(in srgb, var(--sl-color-gray-5), transparent 25%) !important;
  --ec-codeBg: #23262f !important;
  --ec-codeFg: #d6deeb !important;
  --ec-codeSelBg: #1d3b53 !important;
  --ec-gtrFg: #63798b !important;
  --ec-gtrBrdCol: #63798b33 !important;
  --ec-gtrHlFg: #c5e4fd97 !important;
  --ec-uiSelBg: #234d708c !important;
  --ec-uiSelFg: #ffffff !important;
  --ec-focusBrd: #122d42 !important;
  --ec-sbThumbCol: #ffffff17 !important;
  --ec-sbThumbHoverCol: #ffffff47 !important;
  --ec-tm-markBg: #ffffff17 !important;
  --ec-tm-markBrdCol: #ffffff40 !important;
  --ec-tm-insBg: #1e571599 !important;
  --ec-tm-insBrdCol: #487f3bd0 !important;
  --ec-tm-insDiffIndCol: #79b169d0 !important;
  --ec-tm-delBg: #862d2799 !important;
  --ec-tm-delBrdCol: #d1584d !important;
  --ec-tm-delDiffIndCol: #e26b5d !important;
  --ec-frm-shdCol: #00000070 !important;
  --ec-frm-edBg: #23262f !important;
  --ec-frm-trmTtbBg: #1b1e26 !important;
  --ec-frm-trmBg: #23262f !important;
}
:root[data-theme='light'] .adf-check .expressive-code .ec-line :where(span[style^='--']:not([class])),
:root[data-theme='light'] .adf-system-checkpoint .expressive-code .ec-line :where(span[style^='--']:not([class])) {
  color: var(--0, inherit) !important;
  background-color: var(--0bg, transparent) !important;
  font-style: var(--0fs, inherit) !important;
  font-weight: var(--0fw, inherit) !important;
  text-decoration: var(--0td, inherit) !important;
}
.adf-check .expressive-code .frame .header,
.adf-system-checkpoint .expressive-code .frame .header {
  display: none !important;
}
.adf-check .expressive-code .frame.has-title pre,
.adf-check .expressive-code .frame.has-title code,
.adf-check .expressive-code .frame.is-terminal pre,
.adf-check .expressive-code .frame.is-terminal code,
.adf-system-checkpoint .expressive-code .frame.has-title pre,
.adf-system-checkpoint .expressive-code .frame.has-title code,
.adf-system-checkpoint .expressive-code .frame.is-terminal pre,
.adf-system-checkpoint .expressive-code .frame.is-terminal code {
  border-top: var(--ec-brdWd) solid var(--ec-brdCol) !important;
  border-top-left-radius: calc(var(--ec-brdRad) + var(--ec-brdWd)) !important;
  border-top-right-radius: calc(var(--ec-brdRad) + var(--ec-brdWd)) !important;
}
.adf-check .expressive-code .frame.is-terminal pre,
.adf-system-checkpoint .expressive-code .frame.is-terminal pre {
  overflow-x: hidden !important;
}
.adf-check .expressive-code .frame.is-terminal .ec-line .code,
.adf-system-checkpoint .expressive-code .frame.is-terminal .ec-line .code {
  white-space: pre-wrap !important;
  overflow-wrap: anywhere !important;
  min-width: 0 !important;
  padding-inline-end: calc(var(--ec-codePadInl) + 2.8rem) !important;
}
.adf-check .expressive-code .frame.is-terminal .copy,
.adf-system-checkpoint .expressive-code .frame.is-terminal .copy {
  inset-block-start: 0.9rem !important;
  inset-inline-end: 1.6rem !important;
  z-index: 3 !important;
}
.adf-check .expressive-code .frame:not(.is-terminal) .copy,
.adf-system-checkpoint .expressive-code .frame:not(.is-terminal) .copy {
  display: none !important;
}
.adf-check .expressive-code .copy button,
.adf-system-checkpoint .expressive-code .copy button {
  background: rgba(27, 30, 38, 0.96) !important;
  color: #d6deeb !important;
  border-color: rgba(99, 121, 139, 0.35) !important;
  border-radius: 0.75rem !important;
  width: 2rem !important;
  height: 2rem !important;
  opacity: 0 !important;
  pointer-events: none !important;
  transition: opacity 160ms ease !important;
}
.adf-check .expressive-code .frame.is-terminal:hover .copy button,
.adf-check .expressive-code .frame.is-terminal:focus-within .copy button,
.adf-system-checkpoint .expressive-code .frame.is-terminal:hover .copy button,
.adf-system-checkpoint .expressive-code .frame.is-terminal:focus-within .copy button {
  opacity: 0.96 !important;
  pointer-events: auto !important;
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
            html = STRAY_LITERAL_DIV_BLOCK.sub("", html)
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
