from __future__ import annotations

from .output_attachment import build_output_attachment


def build_path_payload(path_key: str, path_value: str) -> dict[str, object]:
    return {
        path_key: path_value,
        "output_attachment": build_output_attachment(),
    }
