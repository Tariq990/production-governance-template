from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pre_push_guard

HEAD = "a" * 40
BRANCH = "feature/x"


def fake_git(root: Path, proofs: Path):
    def run(*args):
        mapping = {
            ("rev-parse", "--show-toplevel"): str(root),
            ("rev-parse", "HEAD"): HEAD,
            ("rev-parse", "--abbrev-ref", "HEAD"): BRANCH,
            ("rev-parse", "--git-path", "gate-proofs"): str(proofs),
        }
        return mapping[args]

    return run


def test_missing_contract_blocks(tmp_path, monkeypatch):
    monkeypatch.setattr(
        pre_push_guard, "git", fake_git(tmp_path, tmp_path / "proofs")
    )
    assert pre_push_guard.main() == 1


def test_valid_proof_passes(tmp_path, monkeypatch):
    contract = tmp_path / ".gate/task-contract.json"
    contract.parent.mkdir()
    contract.write_text(
        json.dumps({"expected_branch": BRANCH}), encoding="utf-8"
    )
    digest = hashlib.sha256(contract.read_bytes()).hexdigest()
    report = tmp_path / "reports/pr-gate.json"
    report.parent.mkdir()
    report.write_text(
        json.dumps(
            {
                "result": "PASS",
                "violations_found": False,
                "head_sha": HEAD,
                "contract_sha256": digest,
            }
        ),
        encoding="utf-8",
    )
    proofs = tmp_path / "proofs"
    proofs.mkdir()
    (proofs / "proof-test.json").write_text(
        json.dumps(
            {
                "head_sha": HEAD,
                "branch": BRANCH,
                "contract_sha256": digest,
                "report_sha256": hashlib.sha256(report.read_bytes()).hexdigest(),
                "contract_path": ".gate/task-contract.json",
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(pre_push_guard, "git", fake_git(tmp_path, proofs))
    assert pre_push_guard.main() == 0


def test_modified_report_blocks(tmp_path, monkeypatch):
    contract = tmp_path / ".gate/task-contract.json"
    contract.parent.mkdir()
    contract.write_text("{}", encoding="utf-8")
    report = tmp_path / "reports/pr-gate.json"
    report.parent.mkdir()
    report.write_text("{}", encoding="utf-8")
    proofs = tmp_path / "proofs"
    proofs.mkdir()
    (proofs / "proof-test.json").write_text(
        json.dumps(
            {
                "head_sha": HEAD,
                "branch": BRANCH,
                "contract_sha256": hashlib.sha256(contract.read_bytes()).hexdigest(),
                "report_sha256": "wrong",
                "contract_path": ".gate/task-contract.json",
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(pre_push_guard, "git", fake_git(tmp_path, proofs))
    assert pre_push_guard.main() == 1
