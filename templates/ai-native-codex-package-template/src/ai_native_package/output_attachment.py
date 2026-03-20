from __future__ import annotations

from .output_formatter import format_output_metadata_markdown
from .output_metadata import get_output_metadata


def build_output_attachment() -> dict[str, object]:
    metadata = get_output_metadata()
    return {
        "metadata": metadata,
        "markdown": format_output_metadata_markdown(metadata),
    }
