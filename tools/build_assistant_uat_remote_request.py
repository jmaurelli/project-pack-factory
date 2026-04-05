#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
import textwrap
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from factory_ops import (
    discover_pack,
    load_json,
    read_now,
    resolve_factory_root,
    schema_path,
    validate_json_document,
    write_json,
)
from remote_autonomy_roundtrip_common import canonical_local_bundle_staging_dir
from remote_autonomy_staging_common import (
    canonical_remote_export_dir,
    canonical_remote_pack_dir,
    canonical_remote_parent_dir,
    canonical_remote_run_dir,
    resolve_local_scratch_root,
)


RUN_REQUEST_SCHEMA_NAME = "remote-autonomy-run-request.schema.json"
TEST_REQUEST_SCHEMA_NAME = "remote-autonomy-test-request.schema.json"
RUN_REQUEST_SCHEMA_VERSION = "remote-autonomy-run-request/v1"
TEST_REQUEST_SCHEMA_VERSION = "remote-autonomy-test-request/v1"
SCENARIO_SCHEMA_NAME = "assistant-uat-scenario.schema.json"
SCENARIO_SCHEMA_VERSION = "assistant-uat-scenario/v1"
SCENARIO_ROOT = Path("docs/specs/project-pack-factory/assistant-uat-scenarios")
SLUG_PATTERN = re.compile(r"^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$")
RUN_ID_SUFFIX_PATTERN = re.compile(r"^(.+)-uat-autonomous-run-v(\d+)$")


def _load_object(path: Path) -> dict[str, Any]:
    payload = load_json(path)
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: JSON document must contain an object")
    return payload


def _write_validated(factory_root: Path, path: Path, payload: dict[str, Any], schema_name: str) -> None:
    write_json(path, payload)
    errors = validate_json_document(path, schema_path(factory_root, schema_name))
    if errors:
        raise ValueError("; ".join(errors))


def _next_run_id(factory_root: Path, remote_target_label: str, pack_id: str) -> str:
    request_root = factory_root / ".pack-state" / "remote-autonomy-requests" / remote_target_label / pack_id
    max_version = 0
    if request_root.exists():
        for child in request_root.iterdir():
            if not child.is_dir():
                continue
            match = RUN_ID_SUFFIX_PATTERN.fullmatch(child.name)
            if match and match.group(1) == pack_id:
                max_version = max(max_version, int(match.group(2)))
    return f"{pack_id}-uat-autonomous-run-v{max_version + 1}"


def _request_root(factory_root: Path, remote_target_label: str, pack_id: str, run_id: str) -> Path:
    return factory_root / ".pack-state" / "remote-autonomy-requests" / remote_target_label / pack_id / run_id


def _resolve_scenario_path(factory_root: Path, scenario_id: str, prompt_bundle_path: str | None) -> Path:
    if prompt_bundle_path and prompt_bundle_path.strip():
        candidate = Path(prompt_bundle_path).expanduser()
        if not candidate.is_absolute():
            candidate = (factory_root / candidate).resolve()
        else:
            candidate = candidate.resolve()
        return candidate
    return (factory_root / SCENARIO_ROOT / f"{scenario_id}.json").resolve()


def _load_scenario(factory_root: Path, scenario_id: str, prompt_bundle_path: str | None) -> tuple[Path, dict[str, Any]]:
    scenario_path = _resolve_scenario_path(factory_root, scenario_id, prompt_bundle_path)
    if not scenario_path.exists():
        raise FileNotFoundError(f"assistant-UAT scenario bundle is missing: {scenario_path}")
    errors = validate_json_document(scenario_path, schema_path(factory_root, SCENARIO_SCHEMA_NAME))
    if errors:
        raise ValueError("; ".join(errors))
    scenario = _load_object(scenario_path)
    if scenario.get("schema_version") != SCENARIO_SCHEMA_VERSION:
        raise ValueError(f"{scenario_path}: schema_version must be {SCENARIO_SCHEMA_VERSION}")
    if scenario.get("scenario_id") != scenario_id:
        raise ValueError(
            f"{scenario_path}: scenario_id `{scenario.get('scenario_id')}` does not match requested `{scenario_id}`"
        )
    prompts = scenario.get("prompts")
    if not isinstance(prompts, list):
        raise ValueError(f"{scenario_path}: prompts must be an array")
    prompt_names: list[str] = []
    for item in prompts:
        if not isinstance(item, dict):
            raise ValueError(f"{scenario_path}: prompts entries must be JSON objects")
        name = item.get("name")
        if not isinstance(name, str) or not name:
            raise ValueError(f"{scenario_path}: prompts entries must declare a non-empty name")
        prompt_names.append(name)
    duplicate_names = sorted({name for name in prompt_names if prompt_names.count(name) > 1})
    if duplicate_names:
        raise ValueError(
            f"{scenario_path}: prompt names must be unique because artifact filenames are derived from them: {', '.join(duplicate_names)}"
        )
    return scenario_path, scenario


def _build_remote_runner(*, run_id: str, scenario: dict[str, Any]) -> str:
    prompts = scenario["prompts"]
    session_preamble = str(scenario["session_preamble"]).strip()
    scenario_id = str(scenario["scenario_id"])
    scenario_summary = str(scenario["summary"]).strip()
    allow_preview_bundle = bool(scenario.get("allow_preview_bundle", False))
    allow_contract_profile_refinement = bool(scenario.get("allow_contract_profile_refinement", False))
    model_reasoning_effort = str(scenario.get("model_reasoning_effort", "medium")).strip() or "medium"
    model_reasoning_effort_config = json.dumps(f'model_reasoning_effort="{model_reasoning_effort}"')
    expected_sidecars = [str(item) for item in scenario.get("expected_sidecar_artifacts", [])]
    preview_policy = (
        "Preview artifacts may also be written under dist/candidates/uat-preview."
        if allow_preview_bundle
        else "Do not create preview artifacts unless the existing local assistant commands already require them."
    )
    profile_refinement_policy = (
        "Contract-profile refinement is allowed for this scenario when the prompt explicitly requires it."
        if allow_contract_profile_refinement
        else "Do not pass refine_profile_json and do not modify contracts/operator-profile.json during this run."
    )
    writable_surface_policy = (
        "Keep artifacts inside .pack-state/autonomy-runs/<run-id>/assistant-uat. "
        f"{preview_policy} "
        "You may update existing assistant state through sanctioned local assistant commands such as "
        f"record-operator-intake or record-business-review, but do not write new arbitrary roots. {profile_refinement_policy} "
        "Do not modify registry, deployments, promotion state, or unrelated files."
    )
    return textwrap.dedent(
        f"""
        python3 -B - <<'PY'
        from __future__ import annotations

        import json
        import os
        import signal
        import shutil
        import subprocess
        import time
        from datetime import datetime, timezone
        from pathlib import Path

        RUN_ID = {run_id!r}
        SCENARIO_ID = {scenario_id!r}
        SCENARIO_SUMMARY = {scenario_summary!r}
        SESSION_PREAMBLE = {session_preamble!r}
        WRITABLE_SURFACE_POLICY = {writable_surface_policy!r}
        ALLOW_PREVIEW_BUNDLE = {allow_preview_bundle!r}
        EXPECTED_SIDECAR_ARTIFACTS = {expected_sidecars!r}
        PROMPTS = {prompts!r}
        PACK_ROOT = Path('.').resolve()
        UAT_ROOT = PACK_ROOT / '.pack-state' / 'autonomy-runs' / RUN_ID / 'assistant-uat'
        UAT_ROOT.mkdir(parents=True, exist_ok=True)
        STALE_ASSISTANT_UAT_ETIMES_SECONDS = 900
        os.environ['PYTHONDONTWRITEBYTECODE'] = '1'


        def now() -> str:
            return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


        def cleanup_incidental_writes() -> None:
            removable_dir_names = {{'__pycache__', '.pytest_cache', '.ruff_cache', '.mypy_cache'}}
            for path in sorted(PACK_ROOT.rglob('*'), reverse=True):
                if path.is_dir() and path.name in removable_dir_names:
                    shutil.rmtree(path, ignore_errors=True)
                elif path.is_file() and path.suffix == '.pyc':
                    path.unlink(missing_ok=True)
            run_root = PACK_ROOT / '.pack-state' / 'autonomy-runs'
            if run_root.exists():
                for run_dir in sorted(run_root.iterdir(), reverse=True):
                    if not run_dir.is_dir() or run_dir.name == RUN_ID:
                        continue
                    assistant_dir = run_dir / 'assistant-uat'
                    try:
                        if assistant_dir.exists() and assistant_dir.is_dir() and not any(assistant_dir.iterdir()):
                            assistant_dir.rmdir()
                    except OSError:
                        pass
                    try:
                        if not any(run_dir.iterdir()):
                            run_dir.rmdir()
                    except OSError:
                        pass


        def _process_exists(pid: int) -> bool:
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                return False
            except PermissionError:
                return True
            return True


        def cleanup_stale_assistant_uat_codex_processes() -> dict[str, object]:
            command = ['ps', '-eo', 'pid=,pgid=,etimes=,args=']
            completed = subprocess.run(
                command,
                text=True,
                capture_output=True,
                check=False,
            )
            result: dict[str, object] = {{
                'status': 'pass' if completed.returncode == 0 else 'ps_failed',
                'scan_command': ' '.join(command),
                'cleanup_boundary': {{
                    'scope': 'pack-scoped-assistant-uat-only',
                    'pack_root': str(PACK_ROOT),
                    'assistant_uat_root': str((PACK_ROOT / '.pack-state' / 'autonomy-runs').resolve()),
                    'current_run_id': RUN_ID,
                    'aged_threshold_seconds': STALE_ASSISTANT_UAT_ETIMES_SECONDS,
                    'pgid_aware': True,
                }},
                'killed_processes': [],
                'killed_process_groups': [],
                'skipped_processes': [],
            }}
            if completed.returncode != 0:
                result['error'] = completed.stderr.strip() or completed.stdout.strip() or 'ps failed'
                return result
            assistant_uat_root = str((PACK_ROOT / '.pack-state' / 'autonomy-runs').resolve())
            all_process_records: list[dict[str, object]] = []
            for raw_line in completed.stdout.splitlines():
                line = raw_line.strip()
                if not line:
                    continue
                parts = line.split(None, 3)
                if len(parts) != 4:
                    continue
                pid_text, pgid_text, etimes_text, args = parts
                try:
                    pid = int(pid_text)
                    pgid = int(pgid_text)
                    etimes = int(etimes_text)
                except ValueError:
                    continue
                record = {{
                    'pid': pid,
                    'pgid': pgid,
                    'elapsed_seconds': etimes,
                    'args': args,
                    'assistant_uat_candidate': (
                        'codex exec' in args
                        and assistant_uat_root in args
                        and '/assistant-uat/' in args
                        and RUN_ID not in args
                        and etimes >= STALE_ASSISTANT_UAT_ETIMES_SECONDS
                    ),
                }}
                all_process_records.append(record)

            process_records = [
                record for record in all_process_records if bool(record.get('assistant_uat_candidate'))
            ]
            skipped_processes = [
                {{
                    'pid': int(record['pid']),
                    'pgid': int(record['pgid']),
                    'elapsed_seconds': int(record['elapsed_seconds']),
                    'args': record['args'],
                }}
                for record in all_process_records
                if not bool(record.get('assistant_uat_candidate')) and (
                    'codex exec' in str(record.get('args', ''))
                    and assistant_uat_root in str(record.get('args', ''))
                    and '/assistant-uat/' in str(record.get('args', ''))
                )
            ]
            processes_by_pgid: dict[int, list[dict[str, object]]] = {{}}
            for record in all_process_records:
                processes_by_pgid.setdefault(int(record['pgid']), []).append(record)

            safe_group_pids: set[int] = set()
            for pgid, records in processes_by_pgid.items():
                candidate_records = [
                    record
                    for record in records
                    if bool(record.get('assistant_uat_candidate'))
                ]
                if len(candidate_records) < 2:
                    continue
                if len(candidate_records) == len(records):
                    safe_group_pids.add(pgid)

            killed_process_groups: list[dict[str, object]] = []
            for pgid in sorted(safe_group_pids):
                signal_used = 'sigterm'
                try:
                    os.killpg(pgid, signal.SIGTERM)
                except ProcessLookupError:
                    signal_used = 'already_exited'
                else:
                    time.sleep(1)
                    try:
                        os.killpg(pgid, 0)
                    except ProcessLookupError:
                        pass
                    else:
                        os.killpg(pgid, signal.SIGKILL)
                        signal_used = 'sigkill'
                group_records = [
                    record
                    for record in processes_by_pgid.get(pgid, [])
                    if bool(record.get('assistant_uat_candidate'))
                ]
                killed_process_groups.append(
                    {{
                        'pgid': pgid,
                        'signal_used': signal_used,
                        'pid_count': len(group_records),
                        'pids': [int(record['pid']) for record in group_records],
                        'elapsed_seconds': max(
                            int(record.get('elapsed_seconds', 0) or 0) for record in group_records
                        )
                        if group_records
                        else 0,
                    }}
                )

            safe_group_member_pids = {{
                int(record['pid'])
                for pgid in safe_group_pids
                for record in processes_by_pgid.get(pgid, [])
            }}
            killed_processes: list[dict[str, object]] = []
            for record in process_records:
                if int(record['pid']) in safe_group_member_pids:
                    continue
                signal_used = 'sigterm'
                try:
                    os.kill(int(record['pid']), signal.SIGTERM)
                except ProcessLookupError:
                    signal_used = 'already_exited'
                else:
                    time.sleep(1)
                    if _process_exists(int(record['pid'])):
                        os.kill(int(record['pid']), signal.SIGKILL)
                        signal_used = 'sigkill'
                killed_processes.append(
                    {{
                        'pid': int(record['pid']),
                        'pgid': int(record['pgid']),
                        'elapsed_seconds': int(record['elapsed_seconds']),
                        'signal_used': signal_used,
                        'args': record['args'],
                    }}
                )
            result['killed_processes'] = killed_processes
            result['killed_process_groups'] = killed_process_groups
            result['killed_process_count'] = len(killed_processes)
            result['killed_process_group_count'] = len(killed_process_groups)
            result['matched_process_count'] = len(process_records)
            result['safe_process_group_count'] = len(safe_group_pids)
            result['skipped_processes'] = skipped_processes
            return result


        def run_codex(name: str, task_prompt: str) -> dict[str, object]:
            prompt = '\\n\\n'.join(
                [
                    'You are running inside a staged Project Pack Factory build-pack.',
                    'Work only inside this pack root. Read AGENTS.md, project-context.md, and pack.json first, then the assistant/operator/partnership contracts needed for the task.',
                    WRITABLE_SURFACE_POLICY,
                    'Assistant UAT scenario:',
                    SESSION_PREAMBLE,
                    'Assistant UAT task:',
                    task_prompt,
                    'Do the needed local work. End with a concise plain-language answer.',
                ]
            )
            output_path = UAT_ROOT / f'{{name}}-last-message.txt'
            stdout_path = UAT_ROOT / f'{{name}}-stdout.txt'
            stderr_path = UAT_ROOT / f'{{name}}-stderr.txt'
            env = dict(os.environ)
            env['PYTHONDONTWRITEBYTECODE'] = '1'
            cleanup_incidental_writes()
            with stdout_path.open('w', encoding='utf-8') as stdout_handle, stderr_path.open('w', encoding='utf-8') as stderr_handle:
                completed = subprocess.run(
                    [
                        'codex', 'exec', '--skip-git-repo-check', '--dangerously-bypass-approvals-and-sandbox',
                        '--color', 'never', '-c', {model_reasoning_effort_config},
                        '-C', '.', '-o', str(output_path), '-'
                    ],
                    input=prompt,
                    text=True,
                    cwd=PACK_ROOT,
                    env=env,
                    stdout=stdout_handle,
                    stderr=stderr_handle,
                    check=False,
                )
            cleanup_incidental_writes()
            return {{
                'name': name,
                'returncode': completed.returncode,
                'output_path': output_path.relative_to(PACK_ROOT).as_posix(),
                'stdout_path': stdout_path.relative_to(PACK_ROOT).as_posix(),
                'stderr_path': stderr_path.relative_to(PACK_ROOT).as_posix(),
            }}


        stale_process_cleanup = cleanup_stale_assistant_uat_codex_processes()
        results = [run_codex(item['name'], item['prompt']) for item in PROMPTS]
        standard_artifact_names = {{'uat-report.json'}}
        for item in PROMPTS:
            standard_artifact_names.add(f"{{item['name']}}-last-message.txt")
            standard_artifact_names.add(f"{{item['name']}}-stdout.txt")
            standard_artifact_names.add(f"{{item['name']}}-stderr.txt")
        extra_artifacts = sorted(
            path.relative_to(UAT_ROOT).as_posix()
            for path in UAT_ROOT.rglob('*')
            if path.is_file() and path.relative_to(UAT_ROOT).as_posix() not in standard_artifact_names
        )
        assistant_memory_root = PACK_ROOT / '.pack-state' / 'assistant-memory'
        latest_memory_pointer_path = PACK_ROOT / '.pack-state' / 'agent-memory' / 'latest-memory.json'
        preview_root = PACK_ROOT / 'dist' / 'candidates' / 'uat-preview'
        report = {{
            'schema_version': 'codex-personal-assistant-uat-report/v1',
            'generated_at': now(),
            'run_id': RUN_ID,
            'scenario_id': SCENARIO_ID,
            'scenario_summary': SCENARIO_SUMMARY,
            'allow_preview_bundle': ALLOW_PREVIEW_BUNDLE,
            'expected_sidecar_artifacts': EXPECTED_SIDECAR_ARTIFACTS,
            'present_expected_sidecar_artifacts': [
                name for name in EXPECTED_SIDECAR_ARTIFACTS if (UAT_ROOT / name).exists()
            ],
            'stale_process_cleanup': stale_process_cleanup,
            'stale_process_cleanup_boundary': stale_process_cleanup.get('cleanup_boundary'),
            'extra_artifacts': extra_artifacts,
            'prompt_results': results,
            'assistant_memory_files': (
                sorted(path.name for path in assistant_memory_root.glob('*.json'))
                if assistant_memory_root.exists()
                else []
            ),
            'latest_memory_pointer_present': latest_memory_pointer_path.exists(),
            'preview_exists': preview_root.exists(),
            'preview_paths': (
                sorted(path.relative_to(preview_root).as_posix() for path in preview_root.rglob('*') if path.is_file())
                if preview_root.exists()
                else []
            ),
        }}
        report_path = UAT_ROOT / 'uat-report.json'
        report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + '\\n', encoding='utf-8')
        cleanup_incidental_writes()
        print(json.dumps({{
            'status': 'completed' if all(item['returncode'] == 0 for item in results) else 'failed',
            'report_path': report_path.relative_to(PACK_ROOT).as_posix(),
            'scenario_id': SCENARIO_ID,
            'prompt_count': len(results),
            'failed_prompts': [item['name'] for item in results if item['returncode'] != 0],
            'present_expected_sidecar_artifacts': [
                name for name in EXPECTED_SIDECAR_ARTIFACTS if (UAT_ROOT / name).exists()
            ],
        }}, sort_keys=True))
        PY
        """
    ).strip()


def _build_run_request(
    *,
    factory_root: Path,
    pack_root: Path,
    pack_id: str,
    run_id: str,
    remote_target_label: str,
    remote_host: str,
    remote_user: str,
    staged_by: str,
    reason: str,
    local_scratch_root: Path,
    scenario: dict[str, Any],
) -> dict[str, Any]:
    remote_parent_dir = canonical_remote_parent_dir(remote_target_label)
    remote_pack_dir = canonical_remote_pack_dir(remote_parent_dir, pack_id)
    return {
        "schema_version": RUN_REQUEST_SCHEMA_VERSION,
        "source_factory_root": str(factory_root),
        "source_build_pack_id": pack_id,
        "source_build_pack_root": str(pack_root),
        "local_scratch_root": str(local_scratch_root),
        "run_id": run_id,
        "remote_host": remote_host,
        "remote_user": remote_user,
        "remote_target_label": remote_target_label,
        "remote_parent_dir": remote_parent_dir,
        "remote_pack_dir": remote_pack_dir,
        "remote_run_dir": canonical_remote_run_dir(remote_pack_dir, run_id),
        "remote_export_dir": canonical_remote_export_dir(remote_pack_dir),
        "remote_reason": f"Autonomous Codex-driven assistant UAT of {reason}.",
        "staged_by": staged_by,
        "remote_runner": _build_remote_runner(run_id=run_id, scenario=scenario),
    }


def _build_test_request(
    *,
    factory_root: Path,
    remote_target_label: str,
    pack_id: str,
    run_id: str,
    remote_run_request_path: Path,
    imported_by: str,
    reason: str,
    local_scratch_root: Path,
) -> dict[str, Any]:
    return {
        "schema_version": TEST_REQUEST_SCHEMA_VERSION,
        "remote_run_request_path": str(remote_run_request_path),
        "local_bundle_staging_dir": str(
            canonical_local_bundle_staging_dir(
                factory_root=factory_root,
                remote_target_label=remote_target_label,
                build_pack_id=pack_id,
                run_id=run_id,
                local_scratch_root=local_scratch_root,
            )
        ),
        "local_scratch_root": str(local_scratch_root),
        "pull_bundle": True,
        "import_bundle": True,
        "imported_by": imported_by,
        "import_reason": f"Import supplementary runtime evidence from autonomous remote assistant UAT of {reason}.",
        "test_reason": f"Run a bounded remote Codex acceptance pass for {reason}, then preserve the resulting runtime evidence for review.",
    }


def build_assistant_uat_remote_request(
    *,
    factory_root: Path,
    build_pack_id: str,
    remote_target_label: str,
    remote_host: str,
    remote_user: str,
    scenario_id: str,
    reason: str,
    prompt_bundle_path: str | None,
    run_id: str | None,
    staged_by: str,
    imported_by: str,
) -> dict[str, Any]:
    location = discover_pack(factory_root, build_pack_id)
    if location.pack_kind != "build_pack":
        raise ValueError(f"{build_pack_id} is not a build_pack")
    local_scratch_root = resolve_local_scratch_root(factory_root)
    scenario_path, scenario = _load_scenario(factory_root, scenario_id, prompt_bundle_path)
    resolved_run_id = run_id.strip() if run_id and run_id.strip() else _next_run_id(factory_root, remote_target_label, build_pack_id)
    if not SLUG_PATTERN.fullmatch(resolved_run_id):
        raise ValueError(
            "run_id must be a lowercase PackFactory slug matching "
            "`^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$`"
        )
    request_root = _request_root(factory_root, remote_target_label, build_pack_id, resolved_run_id)

    run_request_path = request_root / "remote-run-request.json"
    test_request_path = request_root / "remote-test-request.json"
    scenario_manifest_path = request_root / "assistant-uat-scenario-manifest.json"

    run_request = _build_run_request(
        factory_root=factory_root,
        pack_root=location.pack_root,
        pack_id=build_pack_id,
        run_id=resolved_run_id,
        remote_target_label=remote_target_label,
        remote_host=remote_host,
        remote_user=remote_user,
        staged_by=staged_by,
        reason=reason,
        local_scratch_root=local_scratch_root,
        scenario=scenario,
    )
    test_request = _build_test_request(
        factory_root=factory_root,
        remote_target_label=remote_target_label,
        pack_id=build_pack_id,
        run_id=resolved_run_id,
        remote_run_request_path=run_request_path,
        imported_by=imported_by,
        reason=reason,
        local_scratch_root=local_scratch_root,
    )
    scenario_manifest = {
        "schema_version": "assistant-uat-request-scenario-manifest/v1",
        "generated_at": read_now().isoformat().replace("+00:00", "Z"),
        "run_id": resolved_run_id,
        "build_pack_id": build_pack_id,
        "remote_target_label": remote_target_label,
        "reason": reason,
        "scenario_source_path": str(scenario_path),
        "scenario": scenario,
    }

    request_root.mkdir(parents=True, exist_ok=True)
    _write_validated(factory_root, run_request_path, run_request, RUN_REQUEST_SCHEMA_NAME)
    _write_validated(factory_root, test_request_path, test_request, TEST_REQUEST_SCHEMA_NAME)
    write_json(scenario_manifest_path, scenario_manifest)

    return {
        "schema_version": "assistant-uat-remote-request-build-result/v1",
        "status": "completed",
        "generated_at": read_now().isoformat().replace("+00:00", "Z"),
        "build_pack_id": build_pack_id,
        "run_id": resolved_run_id,
        "remote_target_label": remote_target_label,
        "remote_host": remote_host,
        "remote_user": remote_user,
        "scenario_id": scenario_id,
        "scenario_source_path": str(scenario_path),
        "request_root": str(request_root),
        "remote_run_request_path": str(run_request_path),
        "remote_test_request_path": str(test_request_path),
        "scenario_manifest_path": str(scenario_manifest_path),
    }


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a bounded assistant-UAT remote request pair for the existing PackFactory roundtrip control plane."
    )
    parser.add_argument("--factory-root", required=True)
    parser.add_argument("--build-pack-id", required=True)
    parser.add_argument("--remote-target-label", required=True)
    parser.add_argument("--remote-host", required=True)
    parser.add_argument("--remote-user", required=True)
    parser.add_argument("--scenario-id", required=True)
    parser.add_argument("--reason", required=True)
    parser.add_argument("--prompt-bundle-path")
    parser.add_argument("--run-id")
    parser.add_argument("--staged-by", default="codex")
    parser.add_argument("--imported-by", default="codex")
    parser.add_argument("--output", default="json", choices=("json",))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    factory_root = resolve_factory_root(args.factory_root)
    result = build_assistant_uat_remote_request(
        factory_root=factory_root,
        build_pack_id=args.build_pack_id,
        remote_target_label=args.remote_target_label,
        remote_host=args.remote_host,
        remote_user=args.remote_user,
        scenario_id=args.scenario_id,
        reason=args.reason,
        prompt_bundle_path=args.prompt_bundle_path,
        run_id=args.run_id,
        staged_by=args.staged_by,
        imported_by=args.imported_by,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
