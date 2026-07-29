"""Run a fresh gate, create a bound proof, and push through the hook."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPORT = ROOT / "reports" / "pr-gate.json"
DEFAULT_CONTRACT = ROOT / ".gate" / "task-contract.json"


class VerifiedPushFailure(RuntimeError):
    pass


def git(*args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise VerifiedPushFailure(
            completed.stderr.strip() or completed.stdout.strip()
        )
    return completed.stdout.strip()


def contract_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def proof_dir() -> Path:
    path = Path(git("rev-parse", "--git-path", "gate-proofs"))
    return path if path.is_absolute() else ROOT / path


def non_report_dirty() -> list[str]:
    lines = git("status", "--porcelain").splitlines()
    return [
        line
        for line in lines
        if not line[3:].strip().replace("\\", "/").startswith("reports/")
    ]


def create_proof(
    head: str, branch: str, report: Path, contract: Path
) -> Path:
    directory = proof_dir()
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"proof-{head[:12]}.json"
    payload = {
        "head_sha": head,
        "branch": branch,
        "report_sha256": hashlib.sha256(report.read_bytes()).hexdigest(),
        "contract_sha256": contract_hash(contract),
        "report_path": "reports/pr-gate.json",
        "contract_path": ".gate/task-contract.json",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    path.write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )
    return path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", default=str(DEFAULT_CONTRACT))
    args = parser.parse_args()
    contract = Path(args.contract)
    if not contract.exists():
        print(f"BLOCKED: contract not found: {contract}", file=sys.stderr)
        return 1
    try:
        payload = json.loads(contract.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"BLOCKED: invalid contract JSON: {exc}", file=sys.stderr)
        return 1
    head = git("rev-parse", "HEAD")
    branch = git("rev-parse", "--abbrev-ref", "HEAD")
    if payload.get("expected_branch") and payload["expected_branch"] != branch:
        print("BLOCKED: contract branch mismatch", file=sys.stderr)
        return 1
    if payload.get("expected_head_sha") and payload["expected_head_sha"] != head:
        print("BLOCKED: contract SHA mismatch", file=sys.stderr)
        return 1
    dirty = non_report_dirty()
    if dirty:
        print(f"BLOCKED: working tree dirty: {dirty[0]}", file=sys.stderr)
        return 1
    for path in (
        REPORT,
        ROOT / "reports" / "pr-gate.md",
        ROOT / "reports" / "delivery-report.md",
    ):
        if path.exists():
            path.unlink()
    nonce = uuid.uuid4().hex
    environment = os.environ.copy()
    environment["GATE_RUN_NONCE"] = nonce
    completed = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "pr_gate.py"),
            "--level",
            "gate",
            "--contract",
            str(contract),
        ],
        cwd=ROOT,
        text=True,
        env=environment,
        check=False,
    )
    if completed.returncode != 0 or not REPORT.exists():
        print(
            f"BLOCKED: gate failed with exit {completed.returncode}",
            file=sys.stderr,
        )
        return 1
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    if report.get("run_nonce") != nonce:
        print("BLOCKED: report nonce mismatch", file=sys.stderr)
        return 1
    if (
        report.get("head_sha") != head
        or report.get("contract_sha256") != contract_hash(contract)
    ):
        print("BLOCKED: report identity mismatch", file=sys.stderr)
        return 1
    if (
        report.get("result") != "PASS"
        or report.get("violations_found") is not False
    ):
        print("BLOCKED: report is not a clean PASS", file=sys.stderr)
        return 1
    dirty = non_report_dirty()
    if dirty:
        print(
            f"BLOCKED: gate modified tracked files: {dirty[0]}",
            file=sys.stderr,
        )
        return 1
    proof = create_proof(head, branch, REPORT, contract)
    print(f"Proof created: {proof}")
    push = subprocess.run(
        ["git", "push", "origin", branch], cwd=ROOT, check=False
    )
    return push.returncode


if __name__ == "__main__":
    raise SystemExit(main())
