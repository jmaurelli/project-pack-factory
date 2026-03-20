from __future__ import annotations

from pathlib import PurePosixPath

from .metadata import get_package_metadata
from .templates import load_generated_agent_readme_contract


DEFAULT_GENERATED_README_MODE = "in-repo"


def _package_asset(*parts: str) -> str:
    return PurePosixPath("src", "ai_native_package", *parts).as_posix()


def _generated_agent_readme_section_order() -> list[str]:
    contract = load_generated_agent_readme_contract()
    section_order = contract.get("canonical_section_order")
    if not isinstance(section_order, list) or not all(isinstance(item, str) for item in section_order):
        raise ValueError("The generated agent README contract must define canonical_section_order.")
    return list(section_order)


def _build_generated_readme_metadata() -> dict[str, object]:
    contract_path = _package_asset("contracts", "generated-agent-readme.contract.json")
    template_path = _package_asset("templates", "generated-agent-readme.md")
    machine_readable_truth = [
        f"`{_package_asset('contracts', 'generated-agent-readme.contract.json')}`",
        f"`{_package_asset('contracts', 'delegation-brief.schema.json')}`",
        f"`{_package_asset('contracts', 'task-record.schema.json')}`",
        f"`{_package_asset('contracts', 'worker-result.schema.json')}`",
    ]
    section_values: dict[str, object] = {
        "mode": DEFAULT_GENERATED_README_MODE,
        "start_here": [
            f"Canonical generated-agent README structure: `{contract_path}`.",
            f"Rendered agent-facing Markdown shape: `{template_path}`.",
        ],
        "machine_readable_truth": machine_readable_truth,
        "read_order": [
            f"`{contract_path}`",
            f"`{template_path}`",
            f"`{_package_asset('output_metadata.py')}`",
            f"`{_package_asset('templates.py')}`",
            f"`{_package_asset('output_formatter.py')}`",
            f"`{_package_asset('output_attachment.py')}`",
        ],
        "primary_content_files": [
            f"`{template_path}`",
            f"`{_package_asset('templates.py')}`",
            f"`{_package_asset('output_metadata.py')}`",
            f"`{_package_asset('output_formatter.py')}`",
            f"`{_package_asset('output_attachment.py')}`",
        ],
        "validation_status": {
            "result": "pass",
            "summary": "Runtime README emission stays focused on agent reading guidance derived from the canonical template and contract.",
            "evidence": [
                f"`{contract_path}`",
                f"`{template_path}`",
                f"`{_package_asset('output_metadata.py')}`",
                f"`{_package_asset('output_formatter.py')}`",
            ],
        },
        "warning_policy": {
            "default_interpretation": "If this README and a referenced machine-readable artifact differ, follow the machine-readable artifact.",
            "use_machine_readable_reports_for_detail": True,
            "relevant_warning_classes": [
                "contract_drift",
                "section_order_drift",
                "role_separation_drift",
            ],
        },
    }
    section_order = _generated_agent_readme_section_order()
    generated_readme = {section_id: section_values[section_id] for section_id in section_order}
    generated_readme["canonical_section_order"] = section_order
    return generated_readme


def get_output_metadata() -> dict[str, object]:
    return {
        "package": get_package_metadata(),
        "generated_readme": _build_generated_readme_metadata(),
    }
