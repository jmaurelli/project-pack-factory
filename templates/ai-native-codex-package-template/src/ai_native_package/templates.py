from __future__ import annotations

import json
import re
from collections.abc import Iterable, Mapping
from pathlib import Path

from .models import WorkflowPlan


GENERATED_AGENT_README_TEMPLATE = "generated-agent-readme.md"
GENERATED_AGENT_README_CONTRACT = "generated-agent-readme.contract.json"
_ROLE_SEPARATION_SECTION_IDS = (
    "start_here",
    "machine_readable_truth",
    "read_order",
    "primary_content_files",
    "validation_status",
    "warning_policy",
)
_AGENT_README_FORBIDDEN_PATTERNS = (
    re.compile(r"\bupload\b", re.IGNORECASE),
    re.compile(r"\boperator\b", re.IGNORECASE),
    re.compile(r"\bchecklist\b", re.IGNORECASE),
    re.compile(r"\bclick\b", re.IGNORECASE),
    re.compile(r"\bhandoff\b", re.IGNORECASE),
    re.compile(r"\bhand off\b", re.IGNORECASE),
    re.compile(r"\brunbook\b", re.IGNORECASE),
    re.compile(r"\bwhat to (?:run|upload|click|hand ?off)\b", re.IGNORECASE),
)
_START_HERE_SEQUENCE_PATTERNS = (
    re.compile(r"\bthen\b", re.IGNORECASE),
    re.compile(r"\bnext\b", re.IGNORECASE),
    re.compile(r"\bafter that\b", re.IGNORECASE),
    re.compile(r"\bfinally\b", re.IGNORECASE),
    re.compile(r"\bstep\s+\d+\b", re.IGNORECASE),
)
_TEMPLATE_LOOP_PATTERN = re.compile(
    r"{%\s*for\s+(?P<loop_var>\w+)\s+in\s+(?P<expression>[\w.]+)\s*%}(?P<body>.*?){%\s*endfor\s*%}",
    re.DOTALL,
)
_TEMPLATE_VARIABLE_PATTERN = re.compile(r"{{\s*(?P<expression>[\w.]+)\s*}}")


def _package_root() -> Path:
    return Path(__file__).resolve().parent


def _template_path(name: str) -> Path:
    return _package_root() / "templates" / name


def _contract_path(name: str) -> Path:
    return _package_root() / "contracts" / name


def load_generated_agent_readme_contract() -> dict[str, object]:
    payload = json.loads(_contract_path(GENERATED_AGENT_README_CONTRACT).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("The generated agent README contract must deserialize to an object.")
    return payload


def load_generated_agent_readme_template() -> str:
    return _template_path(GENERATED_AGENT_README_TEMPLATE).read_text(encoding="utf-8")


def _resolve_template_expression(context: Mapping[str, object], expression: str) -> object:
    value: object = context
    for segment in expression.split("."):
        if not isinstance(value, Mapping) or segment not in value:
            raise KeyError(f"Unknown template expression `{expression}`.")
        value = value[segment]
    return value


def _stringify_template_value(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _iter_string_values(value: object) -> Iterable[str]:
    if isinstance(value, str):
        yield value
        return
    if isinstance(value, Mapping):
        for nested_value in value.values():
            yield from _iter_string_values(nested_value)
        return
    if isinstance(value, Iterable):
        for nested_value in value:
            yield from _iter_string_values(nested_value)


def _validate_no_operator_language(section_id: str, value: object) -> None:
    for text in _iter_string_values(value):
        for pattern in _AGENT_README_FORBIDDEN_PATTERNS:
            if pattern.search(text):
                raise ValueError(
                    f"The generated agent README `{section_id}` section must stay agent-facing and omit operator checklist language."
                )


def _validate_start_here_orientation(value: object) -> None:
    for text in _iter_string_values(value):
        for pattern in _START_HERE_SEQUENCE_PATTERNS:
            if pattern.search(text):
                raise ValueError(
                    "The generated agent README `start_here` section must orient agents without duplicating action sequencing."
                )


def _validate_generated_agent_readme_role_separation(generated_readme: Mapping[str, object]) -> None:
    for section_id in _ROLE_SEPARATION_SECTION_IDS:
        if section_id not in generated_readme:
            continue
        _validate_no_operator_language(section_id, generated_readme[section_id])

    if "start_here" in generated_readme:
        _validate_start_here_orientation(generated_readme["start_here"])


def _render_template_block(template: str, context: Mapping[str, object]) -> str:
    def replace_loop(match: re.Match[str]) -> str:
        loop_var = match.group("loop_var")
        expression = match.group("expression")
        block = match.group("body")
        items = _resolve_template_expression(context, expression)
        if isinstance(items, Mapping) or isinstance(items, str) or not isinstance(items, Iterable):
            raise ValueError(f"Template loop `{expression}` must resolve to an iterable of values.")

        rendered_items: list[str] = []
        for item in items:
            loop_context = dict(context)
            loop_context[loop_var] = item
            rendered_items.append(_render_template_block(block, loop_context))
        return "".join(rendered_items)

    rendered = _TEMPLATE_LOOP_PATTERN.sub(replace_loop, template)
    return _TEMPLATE_VARIABLE_PATTERN.sub(
        lambda match: _stringify_template_value(
            _resolve_template_expression(context, match.group("expression"))
        ),
        rendered,
    )


def render_generated_agent_readme(generated_readme: Mapping[str, object]) -> str:
    contract = load_generated_agent_readme_contract()
    section_order = contract.get("canonical_section_order")
    if not isinstance(section_order, list) or not all(isinstance(item, str) for item in section_order):
        raise ValueError("The generated agent README contract must define canonical_section_order.")

    missing_sections = [section_id for section_id in section_order if section_id not in generated_readme]
    if missing_sections:
        joined_sections = ", ".join(missing_sections)
        raise ValueError(f"Missing generated README sections required by contract: {joined_sections}")

    _validate_generated_agent_readme_role_separation(generated_readme)

    rendered = _render_template_block(
        load_generated_agent_readme_template(),
        {"generated_readme": dict(generated_readme)},
    ).rstrip()
    return f"{rendered}\n"


def render_delegate_prompt(plan: WorkflowPlan) -> str:
    return "\n".join(
        [
            "You are the delegated execution worker.",
            "Operate from the copied package root for this workflow.",
            "Use /ai-workflow/project-context.md for code-change tasks.",
            f"task_name: {plan.task_name}",
            f"backend: {plan.backend}",
            f"output_dir: {plan.output_dir}",
            f"operation_class: {plan.operation_class}",
            f"contract: {plan.contract}",
        ]
    )
