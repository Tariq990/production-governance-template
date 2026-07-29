"""Normalize policy baselines by path + snippet hash before checking."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import verify_repo_policy as policy

TOKEN = "sys.path" + ".insert"


def root_from(argv: list[str]) -> Path:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--root", type=Path)
    args, _ = parser.parse_known_args(argv)
    return (args.root or Path(__file__).resolve().parent.parent).resolve()


def normalize(
    root: Path, entries: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for raw in entries:
        entry = dict(raw)
        path_text = str(entry["path"]).replace("\\", "/")
        digest = str(entry["snippet_hash"])
        identity = (path_text, digest)
        if identity in seen:
            raise ValueError(
                f"duplicate baseline identity: {path_text} {digest}"
            )
        seen.add(identity)
        path = root / path_text
        if not path.exists():
            raise ValueError(f"baseline file missing: {path_text}")
        lines = path.read_text(encoding="utf-8").splitlines()
        matches = [
            number
            for number, line in enumerate(lines, 1)
            if TOKEN in line and policy.sha256_text(line.strip()) == digest
        ]
        if not matches:
            raise ValueError(
                f"baseline snippet not found: {path_text} {digest}"
            )
        if len(matches) > 1:
            raise ValueError(
                f"ambiguous baseline snippet: {path_text} {matches}"
            )
        entry["line_index"] = matches[0]
        normalized.append(entry)
    return normalized


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    root = root_from(args)
    policy.ROOT = root
    policy.EXIT = 0
    original = policy.load_baseline
    entries = original()
    if policy.EXIT:
        return policy.EXIT
    try:
        normalized = normalize(root, entries)
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"[POLICY] baseline normalization failed: {exc}")
        if "--json" in args:
            print(
                json.dumps(
                    {
                        "exit_code": 1,
                        "checks_run": [],
                        "violations_found": True,
                        "normalization_error": str(exc),
                    },
                    indent=2,
                )
            )
        return 1
    policy.load_baseline = lambda: [dict(entry) for entry in normalized]
    try:
        return policy.main(args)
    finally:
        policy.load_baseline = original


if __name__ == "__main__":
    raise SystemExit(main())
