from __future__ import annotations

import unittest
from pathlib import Path

import pr_gate
import pytest


class GateContractTests(unittest.TestCase):
    def test_levels_are_monotonic(self) -> None:
        self.assertEqual(pr_gate.LEVELS, {"fast": 1, "slice": 2, "gate": 3})

    def test_path_rules(self) -> None:
        self.assertTrue(
            pr_gate.path_matches_rule(
                "data/production/a.json", "data/production/"
            )
        )
        self.assertTrue(pr_gate.path_matches_rule(".env", ".env"))
        self.assertTrue(pr_gate.path_matches_rule(".env.production", ".env.*"))
        self.assertFalse(
            pr_gate.path_matches_rule("docs/environment.md", ".env")
        )

    def test_config_loads(self) -> None:
        config = pr_gate.load_config()
        self.assertEqual(
            config["project"]["name"], "production-governance-template"
        )
        self.assertTrue(config["commands"]["gate"])

    def test_report_schema_fields(self) -> None:
        result = pr_gate.CheckResult("demo", "PASS", 0.01, "ok")
        self.assertEqual(result.name, "demo")
        self.assertEqual(result.status, "PASS")


class TempDir:
    def __init__(self, path: Path):
        self.path = str(path)

    def __enter__(self):
        return self.path

    def __exit__(self, *args):
        return False


def test_levels_are_monotonic():
    assert pr_gate.LEVELS == {"fast": 1, "slice": 2, "gate": 3}


def test_path_matching():
    assert pr_gate.path_matches_rule(
        "data/production/a.json", "data/production/"
    )
    assert pr_gate.path_matches_rule(".env.prod", ".env.*")
    assert not pr_gate.path_matches_rule("docs/env.md", ".env")


def test_explicit_invalid_base_fails_closed(monkeypatch):
    monkeypatch.setattr(
        pr_gate, "run_process", lambda argv, **kwargs: (1, "bad ref")
    )
    with pytest.raises(pr_gate.GateFailure, match="not resolvable"):
        pr_gate.validate_base_ref({"gate": {}}, {"base_ref": "missing"})


def test_changed_files_failure_is_not_hidden(monkeypatch):
    monkeypatch.setattr(
        pr_gate, "run_process", lambda argv, **kwargs: (128, "bad diff")
    )
    with pytest.raises(pr_gate.GateFailure, match="bad diff"):
        pr_gate.changed_files("missing")


def test_committed_diff_is_checked(monkeypatch):
    calls = []

    def run(argv, **kwargs):
        calls.append(argv)
        return 0, ""

    monkeypatch.setattr(pr_gate, "run_process", run)
    pr_gate.check_diff("origin/main")
    assert ["git", "diff", "--check", "origin/main...HEAD"] in calls


def test_out_of_scope_file_blocks():
    with pytest.raises(pr_gate.GateFailure, match="out-of-scope"):
        pr_gate.check_file_policy(
            {"gate": {}},
            ["src/a.py", "secret.txt"],
            {"allowed_files": ["src/a.py"]},
        )


def test_protected_path_blocks():
    with pytest.raises(pr_gate.GateFailure, match="out-of-scope"):
        pr_gate.check_file_policy(
            {"gate": {}},
            ["data/production/a.json"],
            {"protected_paths": ["data/production/"]},
        )


def test_deleted_test_blocks(monkeypatch):
    monkeypatch.setattr(
        pr_gate, "deleted_files", lambda base: ["tests/test_old.py"]
    )
    with pytest.raises(pr_gate.GateFailure, match="without waiver"):
        pr_gate.check_test_deletions("base", None)


def test_removed_test_definition_blocks(monkeypatch):
    monkeypatch.setattr(
        pr_gate, "committed_diff", lambda base: "-def test_removed():\n-    pass"
    )
    with pytest.raises(pr_gate.GateFailure, match="without waiver"):
        pr_gate.check_removed_test_definitions(
            "base", {"forbid_test_removals": True}
        )


def test_equal_count_missing_node_blocks(tmp_path, monkeypatch):
    responses = iter(
        [
            (0, "tests/test_x.py::test_a\ntests/test_x.py::test_c\n"),
            (0, ""),
            (0, "tests/test_x.py::test_a\ntests/test_x.py::test_b\n"),
            (0, ""),
        ]
    )
    monkeypatch.setattr(
        pr_gate, "run_process", lambda argv, **kwargs: next(responses)
    )
    monkeypatch.setattr(pr_gate, "git", lambda *args: "base-sha")
    monkeypatch.setattr(
        pr_gate.tempfile,
        "TemporaryDirectory",
        lambda prefix: TempDir(tmp_path),
    )
    with pytest.raises(pr_gate.GateFailure, match="disappeared"):
        pr_gate.collection_evidence("base", None)


def test_missing_node_waiver_requires_approval(tmp_path, monkeypatch):
    responses = iter(
        [
            (0, "tests/test_x.py::test_a\n"),
            (0, ""),
            (0, "tests/test_x.py::test_a\ntests/test_x.py::test_b\n"),
            (0, ""),
        ]
    )
    monkeypatch.setattr(
        pr_gate, "run_process", lambda argv, **kwargs: next(responses)
    )
    monkeypatch.setattr(pr_gate, "git", lambda *args: "base-sha")
    monkeypatch.setattr(
        pr_gate.tempfile,
        "TemporaryDirectory",
        lambda prefix: TempDir(tmp_path),
    )
    contract = {
        "waivers": [
            {
                "type": "test_node_removal",
                "pattern": "*::test_b",
                "reason": "replaced",
                "approver": "owner",
            }
        ]
    }
    evidence = pr_gate.collection_evidence("base", contract)
    assert evidence.waived_missing_nodes == ["tests/test_x.py::test_b"]


def test_required_test_is_executed(monkeypatch):
    calls = []

    def run(argv, **kwargs):
        calls.append(argv)
        if "--collect-only" in argv:
            return 0, "tests/test_x.py::test_a\n"
        return 0, "1 passed"

    monkeypatch.setattr(pr_gate, "run_process", run)
    records = pr_gate.execute_required_tests(
        {"required_tests": ["tests/test_x.py::test_a"]}
    )
    assert records[0]["executed"] is True
    assert calls[-1][-1] == "tests/test_x.py::test_a"


def test_missing_required_test_blocks(monkeypatch):
    monkeypatch.setattr(
        pr_gate,
        "run_process",
        lambda argv, **kwargs: (0, "tests/test_x.py::test_a\n"),
    )
    with pytest.raises(pr_gate.GateFailure, match="not in collection"):
        pr_gate.execute_required_tests({"required_tests": ["*::test_b"]})


def test_required_test_failure_blocks(monkeypatch):
    def run(argv, **kwargs):
        if "--collect-only" in argv:
            return 0, "tests/test_x.py::test_a\n"
        return 1, "failed"

    monkeypatch.setattr(pr_gate, "run_process", run)
    with pytest.raises(pr_gate.GateFailure, match="required test failed"):
        pr_gate.execute_required_tests({"required_tests": ["*::test_a"]})


def test_post_command_dirty_tree_blocks(monkeypatch):
    monkeypatch.setattr(
        pr_gate, "filtered_status", lambda config: " M src/a.py"
    )
    status, detail, final = pr_gate.check_final_tree("", {"gate": {}})
    assert status == "FAIL"
    assert "modified" in detail
    assert final


def test_report_schema_and_delivery(tmp_path, monkeypatch):
    monkeypatch.setattr(pr_gate, "ROOT", tmp_path)
    payload = {
        "result": "PASS",
        "level": "gate",
        "branch": "feature/x",
        "head_sha": "abc",
        "base_ref": "origin/main",
        "base_sha": "def",
        "contract_sha256": "hash",
        "violations_found": False,
        "changed_files": [],
        "base_collected_tests": 1,
        "head_collected_tests": 1,
        "missing_test_nodes": [],
        "checks": [],
    }
    pr_gate.write_reports({"gate": {}}, payload)
    assert (tmp_path / "reports" / "pr-gate.json").exists()
    assert (tmp_path / "reports" / "delivery-report.md").exists()
