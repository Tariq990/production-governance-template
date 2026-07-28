#!/usr/bin/env python3
"""Fail-closed pre-push proof validation."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path


def git(*args: str) -> str:
    completed = subprocess.run(["git", *args], text=True, capture_output=True, check=False)
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or completed.stdout.strip())
    return completed.stdout.strip()


def git_path(path: str) -> Path:
    candidate = Path(git("rev-parse", "--git-path", path))
    return candidate if candidate.is_absolute() else Path(git("rev-parse", "--show-toplevel")) / candidate


def main() -> int:
    try:
        root = Path(git("rev-parse", "--show-toplevel"))
        head = git("rev-parse", "HEAD")
        branch = git("rev-parse", "--abbrev-ref", "HEAD")
    except RuntimeError as exc:
        print(f"pre-push: BLOCKED — {exc}", file=sys.stderr)
        return 1
    contract = root / ".gate" / "task-contract.json"
    report = root / "reports" / "pr-gate.json"
    if not contract.exists():
        print("pre-push: BLOCKED — contract missing", file=sys.stderr)
        return 1
    try:
        contract_data = json.loads(contract.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"pre-push: BLOCKED — invalid contract: {exc}", file=sys.stderr)
        return 1
    if contract_data.get("expected_branch") and contract_data["expected_branch"] != branch:
        print("pre-push: BLOCKED — contract branch mismatch", file=sys.stderr)
        return 1
    if contract_data.get("expected_head_sha") and contract_data["expected_head_sha"] != head:
        print("pre-push: BLOCKED — contract SHA mismatch", file=sys.stderr)
        return 1
    contract_digest = hashlib.sha256(contract.read_bytes()).hexdigest()
    directory = git_path("gate-proofs")
    if not directory.exists():
        print("pre-push: BLOCKED — proof directory missing", file=sys.stderr)
        return 1
    for proof_path in directory.glob("proof-*.json"):
        try:
            proof = json.loads(proof_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if proof.get("head_sha") != head or proof.get("branch") != branch:
            continue
        if proof.get("contract_sha256") != contract_digest:
            continue
        if proof.get("contract_path") != ".gate/task-contract.json":
            continue
        if not report.exists():
            print("pre-push: BLOCKED — report missing", file=sys.stderr)
            return 1
        report_digest = hashlib.sha256(report.read_bytes()).hexdigest()
        if proof.get("report_sha256") != report_digest:
            print("pre-push: BLOCKED — report changed", file=sys.stderr)
            return 1
        try:
            report_data = json.loads(report.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            print("pre-push: BLOCKED — invalid report", file=sys.stderr)
            return 1
        if (
            report_data.get("result") != "PASS"
            or report_data.get("violations_found") is not False
            or report_data.get("head_sha") != head
            or report_data.get("contract_sha256") != contract_digest
        ):
            print("pre-push: BLOCKED — report identity/result mismatch", file=sys.stderr)
            return 1
        return 0
    print(f"pre-push: BLOCKED — no valid proof for {head[:12]}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
