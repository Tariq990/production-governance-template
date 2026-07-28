from __future__ import annotations

import os

import pr_gate_ci


def test_ci_binds_source_identity(monkeypatch):
    seen = {}

    class Result:
        returncode = 0

    def run(argv, **kwargs):
        seen["argv"] = argv
        return Result()

    monkeypatch.setenv("GITHUB_HEAD_REF", "feature/x")
    monkeypatch.setenv("GATE_SOURCE_SHA", "abc")
    monkeypatch.setenv("GATE_TRUSTED_CONTRACT_PATH", ".gate/ci-contract.json")
    monkeypatch.setattr(pr_gate_ci.subprocess, "run", run)
    assert pr_gate_ci.main() == 0
    assert os.environ["EXPECTED_BRANCH"] == "feature/x"
    assert os.environ["EXPECTED_HEAD_SHA"] == "abc"
    assert seen["argv"][-1] == ".gate/ci-contract.json"
