from __future__ import annotations

import json
import shutil
import venv
from pathlib import Path
from typing import Final

_TEMPLATE_DISTRIBUTION_NAME: Final[str] = "ai-native-codex-package-template"
_TEMPLATE_MODULE_NAME: Final[str] = "ai_native_package"
_TEMPLATE_SCRIPT_NAME: Final[str] = "ai-native-package"
_TEMPLATE_PACKAGE_PATH: Final[str] = "/ai-workflow/packages/ai-native-codex-package-template"
_BOOTSTRAP_MANIFEST_RELATIVE_PATH: Final[str] = ".ai-native-codex-package-template/bootstrap-manifest.json"
_IGNORE_NAMES: Final[tuple[str, ...]] = (
    ".git",
    ".venv",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "__pycache__",
)
_TEXT_SUFFIXES: Final[tuple[str, ...]] = (
    ".json",
    ".lock",
    ".md",
    ".py",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
)
_TEMPLATE_SCAFFOLD_TEST_FILENAME: Final[str] = "test_ai_native_package_scaffold.py"
_VENV_DIRNAME: Final[str] = ".venv"


def _package_root() -> Path:
    return Path(__file__).resolve().parents[2]


def derive_module_name(package_name: str) -> str:
    normalized = package_name.strip()
    if not normalized:
        raise ValueError("package_name must not be empty")
    return normalized.replace("-", "_")


def _ignore_copy(path: str, names: list[str]) -> set[str]:
    ignored = set(_IGNORE_NAMES).intersection(names)
    ignored.update(name for name in names if name.endswith(".egg-info"))
    return ignored


def _rename_module_directory(project_root: Path, module_name: str) -> None:
    source = project_root / "src" / _TEMPLATE_MODULE_NAME
    target = project_root / "src" / module_name
    if module_name == _TEMPLATE_MODULE_NAME:
        return
    if not source.exists():
        raise FileNotFoundError(f"Template module path missing: {source}")
    source.rename(target)


def _rename_scaffold_test_file(project_root: Path, module_name: str) -> None:
    source = project_root / "tests" / _TEMPLATE_SCAFFOLD_TEST_FILENAME
    target = project_root / "tests" / f"test_{module_name}_scaffold.py"
    if not source.exists():
        raise FileNotFoundError(f"Template scaffold test missing: {source}")
    if source == target:
        return
    source.rename(target)


def _replace_in_text_files(project_root: Path, replacements: list[tuple[str, str]]) -> int:
    changed_files = 0
    for path in sorted(project_root.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix not in _TEXT_SUFFIXES and path.name not in {"Makefile", ".gitignore"}:
            continue
        text = path.read_text(encoding="utf-8")
        updated = text
        for old, new in replacements:
            updated = updated.replace(old, new)
        if updated != text:
            path.write_text(updated, encoding="utf-8")
            changed_files += 1
    return changed_files


def _bootstrap_virtualenv(project_root: Path) -> str:
    target = project_root / _VENV_DIRNAME
    if not target.exists():
        builder = venv.EnvBuilder(with_pip=False)
        builder.create(target)
    return str(target)


def _bootstrap_manifest_payload(
    *,
    project_root: Path,
    package_name: str,
    module_name: str,
    script_name: str,
    domain_summary: str | None,
    copied_from: str,
    replaced_file_count: int,
    virtualenv_path: str,
) -> dict[str, object]:
    return {
        "schema_version": "benchmark-bootstrap-manifest/v1",
        "copied_from": copied_from,
        "project_root": str(project_root),
        "package_name": package_name,
        "module_name": module_name,
        "script_name": script_name,
        "domain_summary": domain_summary,
        "virtualenv_path": virtualenv_path,
        "ignored_copy_patterns": list(_IGNORE_NAMES) + ["*.egg-info"],
        "replaced_file_count": replaced_file_count,
        "environment_commands": [
            f"cd {project_root}",
            "make setup-env",
        ],
        "validation_commands": [
            f"cd {project_root}",
            f".venv/bin/python -m {module_name} --help",
            "make validate",
        ],
    }


def write_bootstrap_manifest(project_root: str | Path, payload: dict[str, object]) -> str:
    root = Path(project_root)
    target = root / _BOOTSTRAP_MANIFEST_RELATIVE_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return str(target)


def create_project_from_template(
    *,
    package_name: str,
    destination_root: str | Path,
    module_name: str | None = None,
    script_name: str | None = None,
    domain_summary: str | None = None,
    template_root: str | Path | None = None,
) -> dict[str, object]:
    resolved_package_name = package_name.strip()
    if not resolved_package_name:
        raise ValueError("package_name must not be empty")
    resolved_module_name = derive_module_name(module_name or resolved_package_name)
    resolved_script_name = (script_name or resolved_package_name).strip()
    if not resolved_script_name:
        raise ValueError("script_name must not be empty")

    source_root = Path(template_root) if template_root is not None else _package_root()
    destination_path = Path(destination_root) / resolved_package_name
    if destination_path.exists():
        raise FileExistsError(f"destination project root already exists: {destination_path}")

    shutil.copytree(source_root, destination_path, ignore=_ignore_copy)
    _rename_module_directory(destination_path, resolved_module_name)
    _rename_scaffold_test_file(destination_path, resolved_module_name)
    virtualenv_path = _bootstrap_virtualenv(destination_path)

    replacements = [
        (_TEMPLATE_SCRIPT_NAME, resolved_script_name),
        (_TEMPLATE_PACKAGE_PATH, str(destination_path)),
        (_TEMPLATE_DISTRIBUTION_NAME, resolved_package_name),
        (_TEMPLATE_MODULE_NAME, resolved_module_name),
    ]
    replaced_file_count = _replace_in_text_files(destination_path, replacements)
    manifest = _bootstrap_manifest_payload(
        project_root=destination_path,
        package_name=resolved_package_name,
        module_name=resolved_module_name,
        script_name=resolved_script_name,
        domain_summary=domain_summary,
        copied_from=str(source_root),
        replaced_file_count=replaced_file_count,
        virtualenv_path=virtualenv_path,
    )
    manifest_path = write_bootstrap_manifest(destination_path, manifest)
    return {
        **manifest,
        "bootstrap_manifest": manifest_path,
        "result": "created",
    }
