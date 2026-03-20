from __future__ import annotations

from collections.abc import Mapping

from .output_metadata import get_output_metadata
from .templates import render_generated_agent_readme


def format_output_metadata_markdown(metadata: Mapping[str, object] | None = None) -> str:
    resolved_metadata = get_output_metadata() if metadata is None else metadata
    generated_readme = resolved_metadata.get("generated_readme")
    if not isinstance(generated_readme, Mapping):
        raise ValueError("Output metadata must include a generated_readme payload.")
    return render_generated_agent_readme(generated_readme)
