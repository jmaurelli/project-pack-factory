from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def check_json_file(input_path: Path, required_fields: list[str]) -> dict[str, Any]:
    try:
        payload = json.loads(input_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {
            "status": "fail",
            "input_path": str(input_path),
            "error": "input_file_not_found",
            "required_fields": sorted(set(required_fields)),
            "missing_fields": [],
        }
    except json.JSONDecodeError as exc:
        return {
            "status": "fail",
            "input_path": str(input_path),
            "error": f"invalid_json:{exc.msg}",
            "required_fields": sorted(set(required_fields)),
            "missing_fields": [],
        }

    if not isinstance(payload, dict):
        return {
            "status": "fail",
            "input_path": str(input_path),
            "error": "root_value_must_be_object",
            "required_fields": sorted(set(required_fields)),
            "missing_fields": [],
        }

    normalized_fields = sorted(set(required_fields))
    missing_fields = [field for field in normalized_fields if field not in payload]
    present_fields = [field for field in normalized_fields if field in payload]

    return {
        "status": "pass" if not missing_fields else "fail",
        "input_path": str(input_path),
        "required_fields": normalized_fields,
        "present_fields": present_fields,
        "missing_fields": missing_fields,
    }
