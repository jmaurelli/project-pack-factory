#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, cast

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from factory_ops import (
    isoformat_z,
    load_json,
    relative_path,
    resolve_factory_root,
    schema_path,
    timestamp_token,
    validate_json_document,
    write_json,
)


RUNTIME_ROOT_RELATIVE = Path(".pack-state/browser-proof-runtime")
BROWSER_PROOFS_ROOT_RELATIVE = Path(".pack-state/browser-proofs")
ACTIVE_BROWSER_NAME = "chromium"
PLAYWRIGHT_BROWSERS_JSON = Path("node_modules/playwright-core/browsers.json")
EXECUTABLE_CANDIDATES = (
    ("chromium-headless-shell", Path("chrome-headless-shell-linux64/chrome-headless-shell")),
    ("chromium", Path("chrome-linux64/chrome")),
    ("chromium", Path("chrome-linux/chrome")),
    ("chromium", Path("chrome-win/chrome.exe")),
    ("chromium", Path("chrome-mac/Chromium.app/Contents/MacOS/Chromium")),
)
RUNTIME_BROWSER_PREFIXES = ("chromium_headless_shell", "chromium")
PROOF_REPORT_SCHEMA_NAME = "browser-proof-report.schema.json"
READINESS_REPORT_SCHEMA_NAME = "browser-proof-host-readiness-report.schema.json"
READINESS_REPORT_SCHEMA_VERSION = "browser-proof-host-readiness-report/v1"
PROOF_KIND_DEFAULT = "adf_field_manual_hash_target_opens"


def _load_object(path: Path) -> dict[str, Any]:
    payload = load_json(path)
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: expected a JSON object")
    return cast(dict[str, Any], payload)


def _load_browsers_payload(browsers_json_path: Path) -> dict[str, Any]:
    if not browsers_json_path.exists():
        raise FileNotFoundError(f"Playwright browsers.json is missing: {browsers_json_path}")
    payload = json.loads(browsers_json_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{browsers_json_path}: expected a JSON object")
    return payload


def _resolve_chromium_entry(browsers_payload: dict[str, Any]) -> dict[str, Any]:
    entries = browsers_payload.get("browsers", [])
    if not isinstance(entries, list):
        raise ValueError("Playwright browsers payload is missing the browsers list")
    for entry in entries:
        if isinstance(entry, dict) and entry.get("name") == ACTIVE_BROWSER_NAME:
            return entry
    raise ValueError("Playwright browsers payload does not define an active chromium entry")


def _browser_install_roots(browser_root: Path, browser_revision: str) -> list[Path]:
    return [(browser_root / f"{prefix}-{browser_revision}").resolve() for prefix in RUNTIME_BROWSER_PREFIXES]


def _resolve_executable_path(browser_install_root: Path) -> tuple[Path | None, str]:
    for executable_kind, candidate_relative in EXECUTABLE_CANDIDATES:
        candidate_path = browser_install_root / candidate_relative
        if candidate_path.exists():
            return candidate_path.resolve(), executable_kind
    for candidate_path in browser_install_root.rglob("chrome-headless-shell"):
        if candidate_path.is_file():
            return candidate_path.resolve(), "chromium-headless-shell"
    for candidate_path in browser_install_root.rglob("chrome"):
        if candidate_path.is_file():
            return candidate_path.resolve(), "chromium"
    return None, "unknown"


def _run_ldd(executable_path: Path) -> tuple[bool, int | None, list[str], list[str]]:
    ldd_binary = shutil.which("ldd")
    if not ldd_binary:
        return False, None, [], ["ldd is unavailable on this host."]

    completed = subprocess.run(
        [ldd_binary, str(executable_path)],
        capture_output=True,
        check=False,
        text=True,
    )
    combined_output = "\n".join(
        text for text in (completed.stdout.strip(), completed.stderr.strip()) if text
    )
    output_lines = [line.rstrip() for line in combined_output.splitlines() if line.strip()]
    missing_libraries = []
    for line in output_lines:
        if "=> not found" in line:
            missing_libraries.append(line.split("=>", 1)[0].strip())
    return True, completed.returncode, missing_libraries, output_lines


def _inspect_exact_browser_binary(
    factory_root: Path,
    executable_path: Path | None,
    *,
    browser_revision: str,
    browser_version: str,
    browser_executable_source: str,
    runtime_root: Path | None = None,
    node_root: Path | None = None,
    browser_root: Path | None = None,
) -> dict[str, Any]:
    runtime_root_text = str(runtime_root.resolve()) if runtime_root is not None else ""
    node_root_text = str(node_root.resolve()) if node_root is not None else ""
    browser_root_text = str(browser_root.resolve()) if browser_root is not None else ""
    resolved_path = executable_path.resolve() if executable_path is not None else None
    browser_install_root = (
        resolved_path.parent.parent.resolve()
        if resolved_path is not None and len(resolved_path.parents) >= 2
        else None
    )
    executable_exists = bool(resolved_path and resolved_path.exists())
    ldd_available, ldd_exit_code, missing_libraries, ldd_output_lines = (
        _run_ldd(resolved_path) if executable_exists and resolved_path is not None else (False, None, [], [])
    )

    if not executable_exists:
        status = "missing_browser_executable"
        summary = "Active Playwright Chromium executable could not be resolved from PackFactory evidence."
    elif not ldd_available:
        status = "ldd_unavailable"
        summary = "Chromium executable resolved, but host readiness could not run because ldd is unavailable."
    elif missing_libraries:
        status = "missing_host_dependencies"
        summary = "Chromium executable resolved, but host shared-library dependencies are still missing."
    else:
        status = "ready"
        summary = "Chromium executable resolved and ldd reported no missing shared-library dependencies."

    return {
        "checked_at": isoformat_z(),
        "status": status,
        "runtime_root": runtime_root_text,
        "runtime_root_relative_path": relative_path(factory_root, Path(runtime_root_text)) if runtime_root_text else "",
        "node_root": node_root_text,
        "node_root_relative_path": relative_path(factory_root, Path(node_root_text)) if node_root_text else "",
        "browser_root": browser_root_text,
        "browser_root_relative_path": relative_path(factory_root, Path(browser_root_text)) if browser_root_text else "",
        "browser_name": ACTIVE_BROWSER_NAME,
        "browser_revision": browser_revision,
        "browser_version": browser_version,
        "browser_install_root": str(browser_install_root) if browser_install_root is not None else "",
        "browser_install_root_relative_path": (
            relative_path(factory_root, browser_install_root) if browser_install_root is not None else ""
        ),
        "browser_executable_kind": (
            "chromium-headless-shell"
            if resolved_path is not None and "chrome-headless-shell" in resolved_path.name
            else "chromium"
            if resolved_path is not None and resolved_path.name == "chrome"
            else "unknown"
        ),
        "browser_executable_path": str(resolved_path) if resolved_path is not None else None,
        "browser_executable_relative_path": (
            relative_path(factory_root, resolved_path) if resolved_path is not None else None
        ),
        "browser_executable_exists": executable_exists,
        "browser_executable_source": browser_executable_source,
        "ldd_available": ldd_available,
        "ldd_exit_code": ldd_exit_code,
        "missing_libraries": missing_libraries,
        "missing_library_count": len(missing_libraries),
        "ldd_output_lines": (
            ldd_output_lines
            if ldd_output_lines
            else ["No ldd output captured."]
            if executable_exists
            else ["Browser executable is unresolved; ldd was not run."]
        ),
        "summary": summary,
    }


def inspect_browser_proof_host_readiness(factory_root: Path, *, runtime_root: Path | None = None) -> dict[str, Any]:
    resolved_runtime_root = (runtime_root or (factory_root / RUNTIME_ROOT_RELATIVE)).resolve()
    node_root = resolved_runtime_root / "node-runtime"
    browser_root = resolved_runtime_root / "playwright-browsers"
    browsers_json_path = node_root / PLAYWRIGHT_BROWSERS_JSON

    browsers_payload = _load_browsers_payload(browsers_json_path)
    chromium_entry = _resolve_chromium_entry(browsers_payload)
    browser_revision = str(chromium_entry.get("revision", "")).strip()
    if not browser_revision:
        raise ValueError("Playwright chromium entry is missing a revision")
    browser_version = str(chromium_entry.get("browserVersion", "unknown")).strip() or "unknown"

    executable_path: Path | None = None
    for install_root in _browser_install_roots(browser_root, browser_revision):
        executable_path, _ = _resolve_executable_path(install_root)
        if executable_path is not None:
            break

    return _inspect_exact_browser_binary(
        factory_root,
        executable_path,
        browser_revision=browser_revision,
        browser_version=browser_version,
        browser_executable_source="active_runtime",
        runtime_root=resolved_runtime_root,
        node_root=node_root,
        browser_root=browser_root,
    )


def _iter_proof_reports(factory_root: Path, proof_kind: str) -> list[Path]:
    root = factory_root / BROWSER_PROOFS_ROOT_RELATIVE
    if not root.exists():
        return []
    return sorted(root.glob(f"browser-proof-{proof_kind}-*/proof-report.json"))


def _select_latest_valid_report(factory_root: Path, proof_kind: str) -> tuple[Path, dict[str, Any]]:
    candidates: list[tuple[str, Path, dict[str, Any]]] = []
    for report_path in _iter_proof_reports(factory_root, proof_kind):
        errors = validate_json_document(report_path, schema_path(factory_root, PROOF_REPORT_SCHEMA_NAME))
        if errors:
            continue
        payload = _load_object(report_path)
        if payload.get("proof_kind") != proof_kind:
            continue
        recorded_at = str(payload.get("recorded_at", "")).strip()
        if not recorded_at:
            continue
        candidates.append((recorded_at, report_path, payload))
    if not candidates:
        raise FileNotFoundError(f"no schema-valid browser-proof report found for proof kind `{proof_kind}`")
    candidates.sort(key=lambda item: item[0], reverse=True)
    _, report_path, payload = candidates[0]
    return report_path, payload


def _resolve_browser_from_report_or_runtime(
    factory_root: Path,
    proof_report: dict[str, Any],
) -> tuple[dict[str, Any], str]:
    runtime = proof_report.get("runtime")
    if not isinstance(runtime, dict):
        raise ValueError("proof report runtime section is missing or invalid")

    runtime_root = Path(str(runtime.get("runtime_root", "")).strip()).expanduser().resolve() if str(runtime.get("runtime_root", "")).strip() else None
    node_root = Path(str(runtime.get("node_root", "")).strip()).expanduser().resolve() if str(runtime.get("node_root", "")).strip() else None
    browser_root = Path(str(runtime.get("browser_root", "")).strip()).expanduser().resolve() if str(runtime.get("browser_root", "")).strip() else None

    explicit_path = str(runtime.get("browser_executable_path", "")).strip()
    if explicit_path:
        browser_path = Path(explicit_path).expanduser().resolve()
        if browser_path.exists():
            readiness = _inspect_exact_browser_binary(
                factory_root,
                browser_path,
                browser_revision=str(runtime.get("browser_revision", "unknown")).strip() or "unknown",
                browser_version=str(runtime.get("browser_version", "unknown")).strip() or "unknown",
                browser_executable_source="proof_report_reference",
                runtime_root=runtime_root,
                node_root=node_root,
                browser_root=browser_root,
            )
            return readiness, "proof_report_runtime_field"

    if runtime_root is not None:
        readiness = inspect_browser_proof_host_readiness(factory_root, runtime_root=runtime_root)
        return readiness, "active_runtime"

    raise ValueError(
        "active Chromium binary is unresolved: the latest schema-valid proof report does not record an exact executable path and no runtime root is available for fail-closed inspection"
    )


def _build_report_root(factory_root: Path, proof_kind: str) -> Path:
    return (
        factory_root
        / BROWSER_PROOFS_ROOT_RELATIVE
        / f"browser-proof-host-readiness-{proof_kind}-{timestamp_token()}"
    )


def _write_validated_report(factory_root: Path, path: Path, payload: dict[str, Any]) -> None:
    write_json(path, payload)
    errors = validate_json_document(path, schema_path(factory_root, READINESS_REPORT_SCHEMA_NAME))
    if errors:
        raise ValueError("; ".join(errors))


def _build_host_readiness_report(
    factory_root: Path,
    *,
    proof_kind: str,
    proof_report_path: Path,
    proof_report: dict[str, Any],
    readiness: dict[str, Any],
    selection_source: str,
    report_root: Path,
) -> dict[str, Any]:
    report_path = report_root / "host-readiness-report.json"
    artifacts = proof_report.get("artifacts")
    preferred_request_path: str | None = None
    preferred_request_relative_path: str | None = None
    rerun_request_strategy = "regenerate_equivalent_request"
    if isinstance(artifacts, dict):
        candidate = str(artifacts.get("validated_request_path", "")).strip()
        if candidate:
            preferred = Path(candidate).expanduser().resolve()
            if preferred.exists():
                preferred_request_path = str(preferred)
                preferred_request_relative_path = relative_path(factory_root, preferred)
                rerun_request_strategy = "reuse_preserved_validated_request"

    overall_status = "pass" if readiness.get("status") == "ready" else "fail"
    next_step_summary = (
        "Host shared-library check is clean. Rerun the browser proof to confirm behavior beyond browser launch."
        if overall_status == "pass"
        else "Host shared-library blocker remains or the active Chromium binary is not yet provable. Provision the missing libraries or regenerate an equivalent request, then rerun the browser proof."
    )

    return {
        "schema_version": READINESS_REPORT_SCHEMA_VERSION,
        "proof_kind": proof_kind,
        "status": overall_status,
        "readiness_status": readiness.get("status", "inspection_error"),
        "recorded_at": isoformat_z(),
        "proof_report_path": str(proof_report_path),
        "proof_report_relative_path": relative_path(factory_root, proof_report_path),
        "proof_report_recorded_at": str(proof_report.get("recorded_at", "")).strip(),
        "browser_binary_selection_source": selection_source,
        "browser_binary_kind": readiness.get("browser_executable_kind", "unknown"),
        "browser_revision": str(readiness.get("browser_revision", "unknown")).strip() or "unknown",
        "browser_version": str(readiness.get("browser_version", "unknown")).strip() or "unknown",
        "browser_binary_path": readiness.get("browser_executable_path"),
        "browser_binary_relative_path": readiness.get("browser_executable_relative_path"),
        "ldd_command": (
            f"ldd {readiness.get('browser_executable_path')}" if readiness.get("browser_executable_path") else ""
        ),
        "missing_shared_libraries": readiness.get("missing_libraries", []),
        "ldd_output_lines": readiness.get("ldd_output_lines", ["No ldd output captured."]),
        "preferred_rerun_request_path": preferred_request_path,
        "preferred_rerun_request_relative_path": preferred_request_relative_path,
        "rerun_request_strategy": rerun_request_strategy,
        "next_step_summary": next_step_summary,
        "artifacts": {
            "report_path": str(report_path),
            "report_relative_path": relative_path(factory_root, report_path),
        },
        "failure_summary": None if overall_status == "pass" else str(readiness.get("summary", "")).strip() or None,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate a bounded host-readiness report for the active PackFactory browser-proof Chromium runtime."
    )
    parser.add_argument("--factory-root", required=True, help="Absolute path to the PackFactory root.")
    parser.add_argument(
        "--proof-kind",
        default=PROOF_KIND_DEFAULT,
        help="Browser proof kind to inspect. Defaults to the ADF field-manual proving-ground recipe.",
    )
    parser.add_argument("--output", choices=("json",), default="json", help="Response format.")
    args = parser.parse_args()

    try:
        factory_root = resolve_factory_root(args.factory_root)
        proof_report_path, proof_report = _select_latest_valid_report(factory_root, args.proof_kind)
        readiness, selection_source = _resolve_browser_from_report_or_runtime(factory_root, proof_report)
        report_root = _build_report_root(factory_root, args.proof_kind)
        report_root.mkdir(parents=True, exist_ok=True)
        report = _build_host_readiness_report(
            factory_root,
            proof_kind=args.proof_kind,
            proof_report_path=proof_report_path,
            proof_report=proof_report,
            readiness=readiness,
            selection_source=selection_source,
            report_root=report_root,
        )
        report_path = report_root / "host-readiness-report.json"
        _write_validated_report(factory_root, report_path, report)
        json.dump(report, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
        return 0 if report["status"] == "pass" else 1
    except Exception as exc:
        payload = {
            "schema_version": READINESS_REPORT_SCHEMA_VERSION,
            "proof_kind": args.proof_kind,
            "status": "fail",
            "failure_summary": str(exc),
        }
        json.dump(payload, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
