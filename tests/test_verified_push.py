from __future__ import annotations

import hashlib
import json

import verified_push


def test_proof_dir_uses_git_path(tmp_path, monkeypatch):
    monkeypatch.setattr(verified_push, "ROOT", tmp_path)
    monkeypatch.setattr(
        verified_push, "git", lambda *args: ".git/worktrees/wt/gate-proofs"
    )
    assert verified_push.proof_dir() == (
        tmp_path / ".git/worktrees/wt/gate-proofs"
    )


def test_create_proof_binds_hashes(tmp_path, monkeypatch):
    report = tmp_path / "report.json"
    contract = tmp_path / "contract.json"
    report.write_text("{}", encoding="utf-8")
    contract.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(verified_push, "ROOT", tmp_path)
    monkeypatch.setattr(verified_push, "proof_dir", lambda: tmp_path / "proofs")
    path = verified_push.create_proof("abcdef", "feature/x", report, contract)
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["report_sha256"] == hashlib.sha256(report.read_bytes()).hexdigest()
    assert data["contract_sha256"] == hashlib.sha256(contract.read_bytes()).hexdigest()
