from __future__ import annotations

import verify_repo_policy as policy

TOKEN = "sys.path" + ".insert"


def test_unapproved_path_insert_blocks(tmp_path):
    (tmp_path / "policy_baseline.json").write_text(
        '{"entries": []}', encoding="utf-8"
    )
    (tmp_path / "bad.py").write_text(
        f"{TOKEN}(0, '/tmp')\n", encoding="utf-8"
    )
    assert policy.main(["--root", str(tmp_path)]) == 1


def test_pinned_workflow_passes(tmp_path):
    (tmp_path / "policy_baseline.json").write_text(
        '{"entries": []}', encoding="utf-8"
    )
    path = tmp_path / ".github/workflows/x.yml"
    path.parent.mkdir(parents=True)
    path.write_text(
        "steps:\n  - uses: owner/action@" + "a" * 40 + "\n",
        encoding="utf-8",
    )
    assert policy.main(["--root", str(tmp_path)]) == 0
