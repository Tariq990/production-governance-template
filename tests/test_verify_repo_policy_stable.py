from __future__ import annotations

import hashlib
import json

import verify_repo_policy_stable as stable

TOKEN = "sys.path" + ".insert"


def entry(path: str, line: str):
    return {
        "rule": "sys_path_insert",
        "path": path,
        "line_index": 1,
        "snippet_hash": hashlib.sha256(line.strip().encode()).hexdigest(),
    }


def test_line_shift_is_normalized(tmp_path):
    line = f"{TOKEN}(0, '/tmp')"
    (tmp_path / "ok.py").write_text(
        "# header\n\n" + line + "\n", encoding="utf-8"
    )
    (tmp_path / "policy_baseline.json").write_text(
        json.dumps({"entries": [entry("ok.py", line)]}), encoding="utf-8"
    )
    assert stable.main(["--root", str(tmp_path)]) == 0


def test_missing_snippet_blocks(tmp_path):
    line = f"{TOKEN}(0, '/tmp')"
    (tmp_path / "ok.py").write_text("print('gone')\n", encoding="utf-8")
    (tmp_path / "policy_baseline.json").write_text(
        json.dumps({"entries": [entry("ok.py", line)]}), encoding="utf-8"
    )
    assert stable.main(["--root", str(tmp_path)]) == 1
