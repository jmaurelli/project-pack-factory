from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from config_drift_checker_build_pack.drift_runtime import check_drift


class CheckDriftTests(unittest.TestCase):
    def write_file(self, temp_dir: Path, name: str, contents: str) -> Path:
        path = temp_dir / name
        path.write_text(contents, encoding="utf-8")
        return path

    def test_passes_when_documents_are_equivalent(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_dir = Path(tmpdir)
            baseline = self.write_file(
                temp_dir,
                "baseline.json",
                '{"service": {"name": "config-drift-checker", "timeout_seconds": 30}}\n',
            )
            candidate = self.write_file(
                temp_dir,
                "candidate.json",
                '{\n  "service": {\n    "timeout_seconds": 30,\n    "name": "config-drift-checker"\n  }\n}\n',
            )

            result = check_drift(baseline, candidate)

        self.assertEqual(result["status"], "pass")
        self.assertEqual(result["counts"]["total_findings"], 0)
        self.assertEqual(result["findings"], [])

    def test_returns_review_required_for_non_blocking_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_dir = Path(tmpdir)
            baseline = self.write_file(
                temp_dir,
                "baseline.json",
                '{"service": {"timeout_seconds": 30}}\n',
            )
            candidate = self.write_file(
                temp_dir,
                "candidate.yaml",
                "service:\n  timeout_seconds: 45\n",
            )

            result = check_drift(baseline, candidate)

        self.assertEqual(result["status"], "review_required")
        self.assertEqual(result["input_format"], "mixed")
        self.assertEqual(result["counts"]["warning"], 1)

    def test_returns_fail_for_blocking_override(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_dir = Path(tmpdir)
            baseline = self.write_file(
                temp_dir,
                "baseline.json",
                '{"service": {"timeout_seconds": 30}}\n',
            )
            candidate = self.write_file(
                temp_dir,
                "candidate.json",
                '{"service": {"timeout_seconds": 45}}\n',
            )
            rules = self.write_file(
                temp_dir,
                "rules.yaml",
                "severity_overrides:\n  service.timeout_seconds: blocking\n",
            )

            result = check_drift(baseline, candidate, rules_path=rules)

        self.assertEqual(result["status"], "fail")
        self.assertEqual(result["counts"]["blocking"], 1)

    def test_ignores_configured_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_dir = Path(tmpdir)
            baseline = self.write_file(
                temp_dir,
                "baseline.json",
                '{"service": {"timeout_seconds": 30, "owner": "ops"}}\n',
            )
            candidate = self.write_file(
                temp_dir,
                "candidate.json",
                '{"service": {"timeout_seconds": 30, "owner": "platform"}}\n',
            )
            rules = self.write_file(
                temp_dir,
                "rules.json",
                '{"ignore_paths": ["service.owner"]}\n',
            )

            result = check_drift(baseline, candidate, rules_path=rules)

        self.assertEqual(result["status"], "pass")
        self.assertEqual(result["counts"]["total_findings"], 0)

    def test_fails_closed_for_malformed_input(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_dir = Path(tmpdir)
            baseline = self.write_file(
                temp_dir,
                "baseline.json",
                '{"service": {"timeout_seconds": 30}}\n',
            )
            candidate = self.write_file(
                temp_dir,
                "candidate.json",
                '{"service": \n',
            )

            result = check_drift(baseline, candidate)

        self.assertEqual(result["status"], "fail")
        self.assertEqual(result["counts"]["total_findings"], 0)
        self.assertTrue(result["errors"])


if __name__ == "__main__":
    unittest.main()
