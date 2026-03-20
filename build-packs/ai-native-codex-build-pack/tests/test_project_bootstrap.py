from __future__ import annotations

import json
import sys
from pathlib import Path

from click.testing import CliRunner


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def _src() -> Path:
    return _root() / "src"


def test_create_project_from_template_copies_and_renames(tmp_path: Path) -> None:
    sys.path.insert(0, str(_src()))
    from ai_native_package.project_bootstrap import create_project_from_template

    payload = create_project_from_template(
        package_name="sample-build-pack",
        destination_root=tmp_path,
        module_name="sample_build_pack",
        template_root=_root(),
    )

    project_root = tmp_path / "sample-build-pack"
    assert payload["result"] == "created"
    assert project_root.exists()
    assert (project_root / "src" / "sample_build_pack").exists()
    assert not (project_root / "src" / "ai_native_package").exists()
    assert (project_root / "tests" / "test_sample_build_pack_scaffold.py").exists()
    assert not (project_root / "tests" / "test_ai_native_package_scaffold.py").exists()
    assert (project_root / ".venv").exists()
    assert (project_root / ".venv" / "pyvenv.cfg").exists()
    assert not (project_root / ".pytest_cache").exists()
    assert not (project_root / "src" / "ai_native_package.egg-info").exists()
    pyproject_text = (project_root / "pyproject.toml").read_text(encoding="utf-8")
    assert 'name = "sample-build-pack"' in pyproject_text
    assert 'sample_build_pack.cli:main' in pyproject_text
    manifest = json.loads((project_root / ".ai-native-codex-package-template" / "bootstrap-manifest.json").read_text(encoding="utf-8"))
    assert manifest["package_name"] == "sample-build-pack"
    assert manifest["module_name"] == "sample_build_pack"
    assert manifest["virtualenv_path"].endswith("/sample-build-pack/.venv")
    assert manifest["environment_commands"] == [
        f"cd {project_root}",
        "make setup-env",
    ]


def test_cli_new_project_emits_machine_readable_payload(tmp_path: Path) -> None:
    sys.path.insert(0, str(_src()))
    from ai_native_package.cli import build_app

    runner = CliRunner()
    result = runner.invoke(
        build_app(),
        [
            "new-project",
            "--package-name",
            "sample-build-pack",
            "--destination-root",
            str(tmp_path),
            "--module-name",
            "sample_build_pack",
            "--template-root",
            str(_root()),
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["project_root"].endswith("sample-build-pack")
    assert payload["module_name"] == "sample_build_pack"
    assert Path(payload["bootstrap_manifest"]).exists()
