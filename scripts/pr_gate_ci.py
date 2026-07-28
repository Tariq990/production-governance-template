#!/usr/bin/env python3
"""CI entry point that binds the gate to the PR source identity."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    contract = os.environ.get("GATE_TRUSTED_CONTRACT_PATH", ".gate/ci-contract.json")
    branch = os.environ.get("GITHUB_HEAD_REF") or os.environ.get("GATE_SOURCE_BRANCH")
    sha = os.environ.get("GATE_SOURCE_SHA") or os.environ.get("GITHUB_SHA")
    if branch:
        os.environ["GATE_SOURCE_BRANCH"] = branch
        os.environ["EXPECTED_BRANCH"] = branch
    if sha:
        os.environ["GATE_SOURCE_SHA"] = sha
        os.environ["EXPECTED_HEAD_SHA"] = sha
    completed = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "pr_gate.py"), "--level", "gate", "--contract", contract],
        cwd=ROOT,
        check=False,
    )
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
