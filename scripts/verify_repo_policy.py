#!/usr/bin/env python3
"""Small generic repository policy checker."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
EXIT = 0
PATH_TOKEN = "sys.path" + ".insert"


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_baseline() -> list[dict[str, Any]]:
    global EXIT
    path = ROOT / "policy_baseline.json"
    if not path.exists():
        print("[POLICY] policy_baseline.json missing")
        EXIT = 1
        return []
    try:
        return list(json.loads(path.read_text(encoding="utf-8")).get("entries", []))
    except (json.JSONDecodeError, OSError) as exc:
        print(f"[POLICY] invalid baseline: {exc}")
        EXIT = 1
        return []


def tracked_files(root: Path) -> list[Path]:
    return [path for path in root.rglob("*") if path.is_file() and ".git" not in path.parts and "reports" not in path.parts]


def main(argv: list[str] | None = None) -> int:
    global ROOT, EXIT
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    ROOT = args.root.resolve()
    EXIT = 0
    entries = load_baseline()
    approved = {
        (str(entry.get("path", "")).replace("\\", "/"), str(entry.get("snippet_hash", "")))
        for entry in entries
        if entry.get("rule") == "sys_path_insert"
    }
    violations: list[str] = []
    for path in tracked_files(ROOT):
        relative = str(path.relative_to(ROOT)).replace("\\", "/")
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            continue
        for number, line in enumerate(lines, 1):
            stripped = line.strip()
            if PATH_TOKEN in stripped and not stripped.startswith("#"):
                identity = (relative, sha256_text(stripped))
                if identity not in approved:
                    violations.append(f"{relative}: line {number}: unapproved {PATH_TOKEN}")
        if relative.startswith(".github/workflows/"):
            text = "\n".join(lines)
            if "|| true" in text:
                violations.append(f"{relative}: contains || true")
            for action in re.findall(r"uses:\s*([^\s#]+)", text):
                if action.startswith("./"):
                    continue
                ref = action.rsplit("@", 1)[-1] if "@" in action else ""
                if not re.fullmatch(r"[0-9a-fA-F]{40}", ref):
                    violations.append(f"{relative}: unpinned action {action}")
        private_key_token = "-----BEGIN " + "PRIVATE KEY-----"
        if private_key_token in "\n".join(lines):
            violations.append(f"{relative}: private key material")
    for violation in violations:
        print(f"[POLICY] {violation}")
    EXIT = 1 if violations or EXIT else 0
    payload = {
        "exit_code": EXIT,
        "checks_run": ["sys_path_insert", "or_true_in_workflow", "unpinned_actions", "hardcoded_secrets"],
        "violations_found": bool(EXIT),
    }
    if args.json:
        print(json.dumps(payload, indent=2))
    return EXIT


if __name__ == "__main__":
    raise SystemExit(main())
