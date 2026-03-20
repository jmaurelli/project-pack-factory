from __future__ import annotations

from pathlib import Path

from .project_bootstrap import create_project_from_template, derive_module_name


def create_new_project(
    *,
    template_root: Path,
    destination_root: Path,
    package_name: str,
    domain: str,
    module_name: str | None = None,
    console_script: str | None = None,
    overwrite: bool = False,
) -> dict[str, object]:
    if destination_root.name != package_name:
        raise ValueError("destination_root name must match package_name for the compatibility wrapper")
    if overwrite and destination_root.exists():
        import shutil
        shutil.rmtree(destination_root)
    return create_project_from_template(
        package_name=package_name,
        destination_root=destination_root.parent,
        module_name=module_name or derive_module_name(package_name),
        script_name=console_script or package_name,
        domain_summary=domain,
        template_root=template_root,
    )
