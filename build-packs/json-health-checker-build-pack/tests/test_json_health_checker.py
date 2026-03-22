from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from json_health_checker_template_pack.json_health_checker import check_json_file


class CheckJsonFileTests(unittest.TestCase):
    def write_file(self, temp_dir: Path, name: str, contents: str) -> Path:
        path = temp_dir / name
        path.write_text(contents, encoding="utf-8")
        return path

    def test_passes_when_all_required_fields_are_present(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = self.write_file(
                Path(tmpdir),
                "healthy.json",
                '{"id": 1, "status": "ok", "extra": true}\n',
            )

            result = check_json_file(input_path, ["status", "id", "status"])

        self.assertEqual(result["status"], "pass")
        self.assertEqual(result["required_fields"], ["id", "status"])
        self.assertEqual(result["present_fields"], ["id", "status"])
        self.assertEqual(result["missing_fields"], [])

    def test_fails_when_required_fields_are_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = self.write_file(Path(tmpdir), "missing.json", '{"id": 1}\n')

            result = check_json_file(input_path, ["status", "id", "owner"])

        self.assertEqual(result["status"], "fail")
        self.assertEqual(result["present_fields"], ["id"])
        self.assertEqual(result["missing_fields"], ["owner", "status"])

    def test_fails_for_invalid_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = self.write_file(Path(tmpdir), "invalid.json", '{"id": 1,\n')

            result = check_json_file(input_path, ["id"])

        self.assertEqual(result["status"], "fail")
        self.assertTrue(result["error"].startswith("invalid_json:"))
        self.assertEqual(result["missing_fields"], [])

    def test_fails_when_root_value_is_not_an_object(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = self.write_file(Path(tmpdir), "list.json", '["id", "status"]\n')

            result = check_json_file(input_path, ["id"])

        self.assertEqual(result["status"], "fail")
        self.assertEqual(result["error"], "root_value_must_be_object")
        self.assertEqual(result["missing_fields"], [])

    def test_fails_when_input_file_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "absent.json"

            result = check_json_file(input_path, ["id"])

        self.assertEqual(result["status"], "fail")
        self.assertEqual(result["error"], "input_file_not_found")
        self.assertEqual(result["missing_fields"], [])


if __name__ == "__main__":
    unittest.main()
