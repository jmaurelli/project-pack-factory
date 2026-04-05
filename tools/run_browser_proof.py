#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ipaddress
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from factory_ops import (
    isoformat_z,
    relative_path,
    resolve_factory_root,
    schema_path,
    timestamp_token,
    validate_json_document,
    write_json,
)
from browser_proof_host_readiness import inspect_browser_proof_host_readiness


REQUEST_SCHEMA_NAME = "browser-proof-request.schema.json"
REPORT_SCHEMA_NAME = "browser-proof-report.schema.json"
REQUEST_SCHEMA_VERSION = "browser-proof-request/v1"
REPORT_SCHEMA_VERSION = "browser-proof-report/v1"
PROOF_KIND = "adf_field_manual_hash_target_opens"
TARGET_KIND = "packfactory_local_preview"
PAGE_PATH = "/playbooks/asms-ui-is-down/"
TARGET_ID_PREFIX = "manual-ui-and-proxy-step-"
PLAYWRIGHT_VERSION = "1.58.2"
RUNTIME_ROOT_RELATIVE = Path(".pack-state/browser-proof-runtime")
OUTPUT_ROOT_RELATIVE = Path(".pack-state/browser-proofs")
HELPER_SCRIPT_NAME = "browser_proof_runner.cjs"


def _load_request(factory_root: Path, request_path: Path) -> dict[str, Any]:
    errors = validate_json_document(request_path, schema_path(factory_root, REQUEST_SCHEMA_NAME))
    if errors:
        raise ValueError("; ".join(errors))
    payload = json.loads(request_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{request_path}: request file must contain a JSON object")
    if payload.get("schema_version") != REQUEST_SCHEMA_VERSION:
        raise ValueError(f"{request_path}: schema_version must be {REQUEST_SCHEMA_VERSION}")
    return payload


def _resolve_user_path(factory_root: Path, raw_path: str) -> Path:
    candidate = Path(raw_path).expanduser()
    if not candidate.is_absolute():
        candidate = (factory_root / candidate).resolve()
    else:
        candidate = candidate.resolve()
    return candidate


def _ensure_within_factory(factory_root: Path, path: Path, *, label: str) -> None:
    try:
        path.relative_to(factory_root)
    except ValueError as exc:
        raise ValueError(f"{label} must stay under the factory root: {path}") from exc


def _validate_local_preview_host(hostname: str | None) -> None:
    if hostname is None:
        raise ValueError("target_url must include a host")
    if hostname in {"localhost", "127.0.0.1", "::1"}:
        return
    try:
        address = ipaddress.ip_address(hostname)
    except ValueError as exc:
        raise ValueError(
            "target_url host must be localhost, loopback, or a literal private IP for V1"
        ) from exc
    if not (address.is_private or address.is_loopback):
        raise ValueError("target_url host must be private or loopback for V1")


def _normalize_request(factory_root: Path, payload: dict[str, Any]) -> dict[str, Any]:
    if payload.get("proof_kind") != PROOF_KIND:
        raise ValueError(f"proof_kind must be {PROOF_KIND}")
    if payload.get("target_kind") != TARGET_KIND:
        raise ValueError(f"target_kind must be {TARGET_KIND}")

    target_url = str(payload["target_url"]).strip()
    parsed = urlparse(target_url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("target_url must use http or https")
    if parsed.path != PAGE_PATH:
        raise ValueError(f"target_url path must be {PAGE_PATH}")
    _validate_local_preview_host(parsed.hostname)

    preview_root = _resolve_user_path(factory_root, str(payload["preview_root"]))
    _ensure_within_factory(factory_root, preview_root, label="preview_root")
    if not preview_root.exists():
        raise FileNotFoundError(f"preview_root is missing: {preview_root}")
    if not preview_root.is_dir():
        raise ValueError(f"preview_root must be a directory: {preview_root}")

    expected_preview_markers = [
        preview_root / "src/content/docs/playbooks/asms-ui-is-down.md",
        preview_root / "public/adf-field-manual.js",
    ]
    missing_markers = [marker for marker in expected_preview_markers if not marker.exists()]
    if missing_markers:
        missing_text = ", ".join(str(path) for path in missing_markers)
        raise FileNotFoundError(
            "preview_root does not look like the PackFactory-managed ADF Starlight preview root: "
            f"{missing_text}"
        )

    page_path = str(payload["page_path"]).strip()
    if page_path != PAGE_PATH:
        raise ValueError(f"page_path must be {PAGE_PATH}")

    step_number = int(payload["step_number"])
    if step_number < 1:
        raise ValueError("step_number must be >= 1")

    timeout_ms = int(payload.get("timeout_ms", 20000))
    if timeout_ms < 1_000 or timeout_ms > 120_000:
        raise ValueError("timeout_ms must be between 1000 and 120000")

    return {
        "schema_version": REQUEST_SCHEMA_VERSION,
        "proof_kind": PROOF_KIND,
        "target_kind": TARGET_KIND,
        "target_url": target_url,
        "page_path": PAGE_PATH,
        "preview_root": str(preview_root),
        "preview_root_relative_path": relative_path(factory_root, preview_root),
        "step_number": step_number,
        "target_id": f"{TARGET_ID_PREFIX}{step_number}",
        "capture_console": bool(payload.get("capture_console", True)),
        "capture_screenshot": bool(payload.get("capture_screenshot", False)),
        "timeout_ms": timeout_ms,
    }


def _run_command(command: list[str], *, cwd: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip() or "command failed without output"
        raise RuntimeError(f"Command failed: {' '.join(command)}\n{detail}")
    return completed


def _runtime_env(runtime_root: Path, browser_root: Path) -> dict[str, str]:
    env = os.environ.copy()
    env["HOME"] = str(runtime_root / "home")
    env["PLAYWRIGHT_BROWSERS_PATH"] = str(browser_root)
    env["PLAYWRIGHT_SKIP_BROWSER_GC"] = "1"
    env["PLAYWRIGHT_DOWNLOAD_CONNECTION_TIMEOUT"] = "120000"
    env["npm_config_cache"] = str(runtime_root / "npm-cache")
    return env


def _ensure_playwright_runtime(factory_root: Path) -> dict[str, str]:
    runtime_root = (factory_root / RUNTIME_ROOT_RELATIVE).resolve()
    node_root = runtime_root / "node-runtime"
    browser_root = runtime_root / "playwright-browsers"
    install_state_root = runtime_root / "install-state"
    node_root.mkdir(parents=True, exist_ok=True)
    browser_root.mkdir(parents=True, exist_ok=True)
    install_state_root.mkdir(parents=True, exist_ok=True)
    (runtime_root / "home").mkdir(parents=True, exist_ok=True)

    package_json_path = node_root / "package.json"
    package_payload = {
        "name": "packfactory-browser-proof-runtime",
        "private": True,
        "version": "0.0.0",
        "description": "Factory-managed runtime for PackFactory browser proof tooling.",
        "dependencies": {
            "playwright": PLAYWRIGHT_VERSION,
        },
    }
    if not package_json_path.exists():
        write_json(package_json_path, package_payload)
    else:
        current_payload = json.loads(package_json_path.read_text(encoding="utf-8"))
        if current_payload != package_payload:
            write_json(package_json_path, package_payload)

    env = _runtime_env(runtime_root, browser_root)
    node_modules_playwright = node_root / "node_modules" / "playwright" / "package.json"
    if not node_modules_playwright.exists():
        _run_command(["npm", "install", "--no-audit", "--no-fund"], cwd=node_root, env=env)
    else:
        installed_payload = json.loads(node_modules_playwright.read_text(encoding="utf-8"))
        installed_version = str(installed_payload.get("version", "")).strip()
        if installed_version != PLAYWRIGHT_VERSION:
            _run_command(["npm", "install", "--no-audit", "--no-fund"], cwd=node_root, env=env)

    browser_marker = install_state_root / f"playwright-{PLAYWRIGHT_VERSION}-chromium.ok"
    if not browser_marker.exists():
        _run_command(
            [str(node_root / "node_modules" / ".bin" / "playwright"), "install", "chromium"],
            cwd=node_root,
            env=env,
        )
        browser_marker.write_text(f"{PLAYWRIGHT_VERSION}\n", encoding="utf-8")

    return {
        "runtime_root": str(runtime_root),
        "runtime_root_relative_path": relative_path(factory_root, runtime_root),
        "node_root": str(node_root),
        "node_root_relative_path": relative_path(factory_root, node_root),
        "browser_root": str(browser_root),
        "browser_root_relative_path": relative_path(factory_root, browser_root),
        "node_modules_root": str(node_root / "node_modules"),
        "npm_package_version": PLAYWRIGHT_VERSION,
    }


def _validated_request_payload(normalized_request: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": normalized_request["schema_version"],
        "proof_kind": normalized_request["proof_kind"],
        "target_kind": normalized_request["target_kind"],
        "target_url": normalized_request["target_url"],
        "preview_root": normalized_request["preview_root"],
        "page_path": normalized_request["page_path"],
        "step_number": normalized_request["step_number"],
        "capture_console": normalized_request["capture_console"],
        "capture_screenshot": normalized_request["capture_screenshot"],
        "timeout_ms": normalized_request["timeout_ms"],
    }


def _write_validated_request(
    *,
    factory_root: Path,
    proof_root: Path,
    validated_request: dict[str, Any],
) -> Path:
    proof_root.mkdir(parents=True, exist_ok=True)
    validated_request_path = proof_root / "validated-request.json"
    write_json(validated_request_path, validated_request)
    errors = validate_json_document(
        validated_request_path,
        schema_path(factory_root, REQUEST_SCHEMA_NAME),
    )
    if errors:
        raise ValueError("; ".join(errors))
    return validated_request_path


def _fallback_host_readiness(runtime_info: dict[str, str], *, failure_summary: str) -> dict[str, Any]:
    summary = failure_summary.strip() or "Host readiness inspection failed before the browser proof ran."
    return {
        "checked_at": isoformat_z(),
        "status": "inspection_error",
        "browser_name": "chromium",
        "browser_executable_kind": "unknown",
        "browser_revision": "unknown",
        "browser_version": "unknown",
        "browser_executable_path": None,
        "browser_executable_relative_path": None,
        "browser_executable_exists": False,
        "browser_executable_source": "unknown",
        "ldd_available": False,
        "ldd_exit_code": None,
        "missing_libraries": [],
        "missing_library_count": 0,
        "summary": summary,
        "runtime_root": runtime_info["runtime_root"],
        "runtime_root_relative_path": runtime_info["runtime_root_relative_path"],
        "node_root": runtime_info["node_root"],
        "node_root_relative_path": runtime_info["node_root_relative_path"],
        "browser_root": runtime_info["browser_root"],
        "browser_root_relative_path": runtime_info["browser_root_relative_path"],
    }


def _build_output_root(factory_root: Path, proof_kind: str) -> Path:
    run_id = f"browser-proof-{proof_kind}-{timestamp_token()}"
    return factory_root / OUTPUT_ROOT_RELATIVE / run_id


def _run_browser_helper(
    *,
    factory_root: Path,
    normalized_request: dict[str, Any],
    runtime_info: dict[str, str],
    proof_root: Path,
) -> dict[str, Any]:
    proof_root.mkdir(parents=True, exist_ok=True)
    normalized_request_path = proof_root / "normalized-request.json"
    write_json(normalized_request_path, normalized_request)
    screenshot_path = proof_root / "debug-screenshot.png"
    helper_request = dict(normalized_request)
    helper_request["capture_screenshot_path"] = (
        str(screenshot_path) if normalized_request["capture_screenshot"] else None
    )
    helper_request_path = proof_root / "helper-request.json"
    write_json(helper_request_path, helper_request)

    env = _runtime_env(Path(runtime_info["runtime_root"]), Path(runtime_info["browser_root"]))
    env["NODE_PATH"] = runtime_info["node_modules_root"]

    completed = subprocess.run(
        ["node", str(SCRIPT_DIR / HELPER_SCRIPT_NAME), "--request-file", str(helper_request_path)],
        cwd=factory_root,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    stdout = completed.stdout.strip()
    if not stdout:
        detail = completed.stderr.strip() or "browser helper returned no stdout"
        raise RuntimeError(detail)
    helper_payload = json.loads(stdout)
    if not isinstance(helper_payload, dict):
        raise ValueError("browser helper did not return a JSON object")
    return helper_payload


def _build_report(
    *,
    factory_root: Path,
    normalized_request: dict[str, Any],
    runtime_info: dict[str, str],
    helper_result: dict[str, Any],
    host_readiness: dict[str, Any],
    proof_root: Path,
    validated_request_path: Path,
) -> dict[str, Any]:
    screenshot_path = proof_root / "debug-screenshot.png"
    report_path = proof_root / "proof-report.json"
    assertions = helper_result.get("assertions", [])
    if not isinstance(assertions, list):
        raise ValueError("browser helper returned invalid assertions")
    if not assertions:
        assertions = [
            {
                "name": "browser_helper_completed",
                "status": "fail",
                "summary": str(helper_result.get("failure_summary", "Browser helper returned no assertions.")),
            }
        ]

    status = str(helper_result.get("status", "fail"))
    report = {
        "schema_version": REPORT_SCHEMA_VERSION,
        "proof_run_id": proof_root.name,
        "proof_kind": PROOF_KIND,
        "target_kind": TARGET_KIND,
        "status": status,
        "recorded_at": isoformat_z(),
        "target_url": normalized_request["target_url"],
        "page_path": normalized_request["page_path"],
        "step_number": normalized_request["step_number"],
        "target_id": normalized_request["target_id"],
        "packfactory_provenance": {
            "preview_root": normalized_request["preview_root"],
            "preview_root_relative_path": normalized_request["preview_root_relative_path"],
            "preview_markers": [
                "src/content/docs/playbooks/asms-ui-is-down.md",
                "public/adf-field-manual.js",
            ],
        },
        "runtime": {
            "runtime_root": runtime_info["runtime_root"],
            "runtime_root_relative_path": runtime_info["runtime_root_relative_path"],
            "node_root": runtime_info["node_root"],
            "node_root_relative_path": runtime_info["node_root_relative_path"],
            "browser_root": runtime_info["browser_root"],
            "browser_root_relative_path": runtime_info["browser_root_relative_path"],
            "browser_name": "chromium",
            "browser_executable_kind": host_readiness.get("browser_executable_kind", "unknown"),
            "browser_revision": str(host_readiness.get("browser_revision", "unknown")) or "unknown",
            "browser_version": str(
                helper_result.get("browser_version", host_readiness.get("browser_version", "unknown"))
            )
            or "unknown",
            "browser_executable_path": host_readiness.get("browser_executable_path"),
            "browser_executable_relative_path": host_readiness.get("browser_executable_relative_path"),
            "browser_executable_source": host_readiness.get("browser_executable_source", "active_runtime"),
            "npm_package_version": runtime_info["npm_package_version"],
        },
        "host_readiness": {
            "checked_at": host_readiness.get("checked_at", isoformat_z()),
            "status": host_readiness.get("status", "missing_browser_executable"),
            "browser_name": host_readiness.get("browser_name", "chromium"),
            "browser_executable_kind": host_readiness.get("browser_executable_kind", "unknown"),
            "browser_revision": str(host_readiness.get("browser_revision", "unknown")) or "unknown",
            "browser_version": str(host_readiness.get("browser_version", "unknown")) or "unknown",
            "browser_executable_path": host_readiness.get("browser_executable_path"),
            "browser_executable_relative_path": host_readiness.get("browser_executable_relative_path"),
            "browser_executable_exists": bool(host_readiness.get("browser_executable_exists", False)),
            "browser_executable_source": host_readiness.get("browser_executable_source", "active_runtime"),
            "ldd_available": bool(host_readiness.get("ldd_available", False)),
            "ldd_exit_code": host_readiness.get("ldd_exit_code"),
            "missing_libraries": host_readiness.get("missing_libraries", []),
            "missing_library_count": int(host_readiness.get("missing_library_count", 0)),
            "summary": str(host_readiness.get("summary", "Host readiness was not recorded.")).strip()
            or "Host readiness was not recorded.",
        },
        "target_state": {
            "overview_label": helper_result.get("overview_label", ""),
            "summary_command_count_text": helper_result.get("summary_command_count_text", ""),
            "detected_run_block_count": helper_result.get("detected_run_block_count", 0),
            "initially_collapsed": helper_result.get("initially_collapsed", False),
            "details_open_after_navigation": helper_result.get("details_open_after_navigation", False),
            "final_url": helper_result.get("final_url", ""),
            "final_hash": helper_result.get("final_hash", ""),
        },
        "assertions": assertions,
        "console": {
            "enabled": bool(normalized_request["capture_console"]),
            "message_count": helper_result.get("console_message_count", 0),
            "messages": helper_result.get("console_messages", []),
            "page_errors": helper_result.get("page_errors", []),
        },
        "artifacts": {
            "report_path": str(report_path),
            "report_relative_path": relative_path(factory_root, report_path),
            "validated_request_path": str(validated_request_path),
            "validated_request_relative_path": relative_path(factory_root, validated_request_path),
            "screenshot_path": str(screenshot_path) if screenshot_path.exists() else None,
            "screenshot_relative_path": (
                relative_path(factory_root, screenshot_path) if screenshot_path.exists() else None
            ),
        },
        "failure_summary": str(helper_result.get("failure_summary", "")).strip() or None,
    }
    return report


def _write_validated_report(factory_root: Path, report_path: Path, payload: dict[str, Any]) -> None:
    write_json(report_path, payload)
    errors = validate_json_document(report_path, schema_path(factory_root, REPORT_SCHEMA_NAME))
    if errors:
        raise ValueError("; ".join(errors))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run one bounded PackFactory browser proof against a PackFactory-managed local preview surface."
    )
    parser.add_argument("--factory-root", required=True, help="Absolute path to the PackFactory root.")
    parser.add_argument("--request-file", required=True, help="Path to a browser-proof request JSON file.")
    parser.add_argument("--output", choices=("json",), default="json", help="Response format.")
    args = parser.parse_args()

    try:
        factory_root = resolve_factory_root(args.factory_root)
        request_path = _resolve_user_path(factory_root, args.request_file)
        request_payload = _load_request(factory_root, request_path)
        normalized_request = _normalize_request(factory_root, request_payload)
        runtime_info = _ensure_playwright_runtime(factory_root)
        proof_root = _build_output_root(factory_root, PROOF_KIND)
        validated_request_path = _write_validated_request(
            factory_root=factory_root,
            proof_root=proof_root,
            validated_request=_validated_request_payload(normalized_request),
        )
        try:
            host_readiness = inspect_browser_proof_host_readiness(
                factory_root,
                runtime_root=Path(runtime_info["runtime_root"]),
            )
        except Exception as exc:
            host_readiness = _fallback_host_readiness(runtime_info, failure_summary=str(exc))
        try:
            helper_result = _run_browser_helper(
                factory_root=factory_root,
                normalized_request=normalized_request,
                runtime_info=runtime_info,
                proof_root=proof_root,
            )
        except Exception as exc:
            helper_result = {
                "status": "fail",
                "failure_summary": str(exc),
                "assertions": [
                    {
                        "name": "browser_helper_completed",
                        "status": "fail",
                        "summary": str(exc),
                    }
                ],
                "console_message_count": 0,
                "console_messages": [],
                "page_errors": [],
            }
        report = _build_report(
            factory_root=factory_root,
            normalized_request=normalized_request,
            runtime_info=runtime_info,
            helper_result=helper_result,
            host_readiness=host_readiness,
            proof_root=proof_root,
            validated_request_path=validated_request_path,
        )
        report_path = proof_root / "proof-report.json"
        _write_validated_report(factory_root, report_path, report)
        json.dump(report, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
        return 0 if report["status"] == "pass" else 1
    except Exception as exc:
        error_payload = {
            "schema_version": REPORT_SCHEMA_VERSION,
            "proof_kind": PROOF_KIND,
            "status": "fail",
            "failure_summary": str(exc),
        }
        json.dump(error_payload, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
