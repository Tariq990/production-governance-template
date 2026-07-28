from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import pr_gate  # noqa: E402


class GateContractTests(unittest.TestCase):
    def test_levels_are_monotonic(self) -> None:
        self.assertEqual(pr_gate.LEVELS, {"fast": 1, "slice": 2, "gate": 3})

    def test_path_rules(self) -> None:
        self.assertTrue(pr_gate.path_matches_rule("data/production/a.json", "data/production/"))
        self.assertTrue(pr_gate.path_matches_rule(".env", ".env"))
        self.assertTrue(pr_gate.path_matches_rule(".env.production", ".env.*"))
        self.assertFalse(pr_gate.path_matches_rule("docs/environment.md", ".env"))

    def test_config_loads(self) -> None:
        config = pr_gate.load_config()
        self.assertEqual(config["project"]["name"], "production-governance-template")
        self.assertTrue(config["commands"]["gate"])

    def test_report_schema_fields(self) -> None:
        result = pr_gate.CheckResult("demo", "PASS", 0.01, "ok")
        self.assertEqual(result.name, "demo")
        self.assertEqual(result.status, "PASS")


if __name__ == "__main__":
    unittest.main()
