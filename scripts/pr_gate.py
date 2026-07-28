#!/usr/bin/env python3
"""Deterministic repository quality gate.

The gate combines built-in Git safety checks, configurable static audits, and
project commands from governance.toml. It always writes machine-readable and
human-readable reports and never treats prose as evidence of success.
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import shlex
import subprocess
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

try:
    import tomllib
except ModuleNotFoundError as exc:  # pragma: no cover - Python <3.11 guard
    raise SystemExit("Python 3.11+ is required") from exc

ROOT = Path(__file__).resolve().parent.parent
LEVELS = {"fast": 1, "slice": 2, "gate": 3}


@dataclass
class CheckResult:
    name: str
    status: str
    duration_seconds: float
    detail: str = ""
    command: list[str] | None = None
    exit_code: int | None = None


class GateFailure(RuntimeError):
    pass


def run_process(argv: list[str], *, cwd: Path = ROOT) -> tuple[int, str]:
    completed = subprocess.run(
        argv,
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    return completed.returncode, completed.stdout


def load_config() -> dict[str, Any]:
    path = ROOT / "governance.toml"
    if not path.exists():
        raise GateFailure("governance.toml is missing")
    with path.open("rb") as handle:
        return tomllib.load(handle)


def git(*args: str) -> str:
    code, output = run_process(["git", *args])
    if code != 0:
        raise GateFailure(f"git {' '.join(args)} failed: {output.strip()}")
    return output.strip()


def current_branch() -> str:
    return git("rev-parse", "--abbrev-ref", "HEAD")


def current_sha() -> str:
    return git("rev-parse", "HEAD")


def resolve_base_ref(config: dict[str, Any]) -> str:
    return os.getenv("GATE_BASE_REF") or str(config["gate"].get("base_ref", "HEAD~1"))


def changed_files(base_ref: str) -> list[str]:
    code, output = run_process(["git", "diff", "--name-only", f"{base_ref}...HEAD"])
    if code != 0:
        # A new repository may not have a usable merge base yet.
        code, output = run_process(["git", "diff", "--name-only", "HEAD~1", "HEAD"])
    if code != 0:
        code, output = run_process(["git", "ls-files"])
    if code != 0:
        raise GateFailure(output.strip())
    return sorted({line.strip().replace("\\", "/") for line in output.splitlines() if line.strip()})


def path_matches_rule(path: str, rule: str) -> bool:
    """Match an exact path, a directory prefix, or an explicit glob rule."""
    if any(token in rule for token in ("*", "?", "[")):
        return fnmatch.fnmatch(path, rule)
    if rule.endswith("/"):
        return path.startswith(rule)
    return path == rule


def check_branch_and_sha(config: dict[str, Any]) -> str:
    branch = current_branch()
    sha = current_sha()
    expected_branch = os.getenv("EXPECTED_BRANCH")
    expected_sha = os.getenv("EXPECTED_HEAD_SHA")
    if expected_branch and branch != expected_branch:
        raise GateFailure(f"branch mismatch: expected {expected_branch}, got {branch}")
    if expected_sha and sha != expected_sha:
        raise GateFailure(f"SHA mismatch: expected {expected_sha}, got {sha}")
    patterns = config["gate"].get("allowed_branch_patterns", [])
    if patterns and not any(fnmatch.fnmatch(branch, pattern) for pattern in patterns):
        raise GateFailure(f"branch {branch!r} does not match allowed patterns")
    return f"branch={branch} sha={sha}"


def check_changed_file_policy(config: dict[str, Any], files: list[str]) -> str:
    gate = config["gate"]
    forbidden = [str(item) for item in gate.get("forbidden_paths", [])]
    extensions = [str(item) for item in gate.get("forbidden_extensions", [])]
    violations = [path for path in files if any(path_matches_rule(path, item) for item in forbidden)]
    violations += [path for path in files if any(path.endswith(ext) for ext in extensions)]

    allowed_raw = os.getenv("GATE_ALLOWED_FILES", "").strip()
    if allowed_raw:
        allowed = {item.strip().replace("\\", "/") for item in allowed_raw.split(",") if item.strip()}
        violations += [path for path in files if path not in allowed]

    if violations:
        raise GateFailure("forbidden or out-of-scope files changed: " + ", ".join(sorted(set(violations))))
    return f"{len(files)} changed file(s) accepted"


def check_diff() -> str:
    code, output = run_process(["git", "diff", "--check"])
    if code != 0:
        raise GateFailure(output.strip())
    return "git diff --check passed"


def check_worktree(config: dict[str, Any], level: str) -> str:
    if level != "gate" or not config["gate"].get("require_clean_tree_on_gate", False):
        return "clean-tree enforcement applies only to the full gate"
    ignore = [str(item) for item in config["gate"].get("ignore_dirty_paths", [])]
    status = git("status", "--porcelain")
    dirty = []
    for line in status.splitlines():
        path = line[3:].strip().replace("\\", "/")
        if not any(path.startswith(prefix) for prefix in ignore):
            dirty.append(line)
    if dirty:
        raise GateFailure("working tree is dirty: " + " | ".join(dirty))
    return "working tree clean"


def check_conflict_markers(files: list[str]) -> str:
    markers = re.compile(r"^(<<<<<<<|=======|>>>>>>>)", re.MULTILINE)
    found = []
    for rel in files:
        path = ROOT / rel
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if markers.search(text):
            found.append(rel)
    if found:
        raise GateFailure("merge-conflict markers found: " + ", ".join(found))
    return "no merge-conflict markers"


def check_actions_pinned() -> str:
    workflow_dir = ROOT / ".github" / "workflows"
    violations = []
    if not workflow_dir.exists():
        return "no workflows present"
    use_pattern = re.compile(r"uses:\s*([^\s#]+)")
    for path in workflow_dir.glob("*.y*ml"):
        text = path.read_text(encoding="utf-8")
        for match in use_pattern.finditer(text):
            action = match.group(1)
            if action.startswith("./"):
                continue
            ref = action.rsplit("@", 1)[-1] if "@" in action else ""
            if not re.fullmatch(r"[0-9a-fA-F]{40}", ref):
                violations.append(f"{path.relative_to(ROOT)}: {action}")
    if violations:
        raise GateFailure("third-party actions must use full commit SHAs: " + "; ".join(violations))
    return "all external actions are SHA-pinned"


def iter_glob(pattern: str) -> list[Path]:
    return [path for path in ROOT.glob(pattern) if path.is_file() and ".git" not in path.parts]


def run_static_audits(config: dict[str, Any]) -> list[CheckResult]:
    results: list[CheckResult] = []
    for rule in config.get("audits", {}).get("regex", []):
        started = time.monotonic()
        name = str(rule["name"])
        pattern = re.compile(str(rule["pattern"]), re.MULTILINE)
        severity = str(rule.get("severity", "error")).lower()
        hits = []
        for path in iter_glob(str(rule.get("glob", "**/*"))):
            try:
                text = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            if pattern.search(text):
                hits.append(str(path.relative_to(ROOT)).replace("\\", "/"))
        status = "PASS"
        detail = str(rule.get("message", ""))
        if hits:
            detail = f"{detail} Hits: {', '.join(hits)}".strip()
            status = "WARN" if severity == "warning" else "FAIL"
        results.append(CheckResult(name, status, time.monotonic() - started, detail))
    return results


def execute_check(name: str, func: Any) -> CheckResult:
    started = time.monotonic()
    try:
        detail = str(func())
        return CheckResult(name, "PASS", time.monotonic() - started, detail)
    except Exception as exc:  # gate boundary: converted to safe report
        return CheckResult(name, "FAIL", time.monotonic() - started, f"{type(exc).__name__}: {exc}")


def configured_commands(config: dict[str, Any], level: str) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    for candidate, rank in LEVELS.items():
        if rank <= LEVELS[level]:
            selected.extend(config.get("commands", {}).get(candidate, []))
    return selected


def run_command(spec: dict[str, Any]) -> CheckResult:
    name = str(spec["name"])
    argv = [str(item) for item in spec["argv"]]
    started = time.monotonic()
    code, output = run_process(argv)
    output = output.strip()
    if len(output) > 6000:
        output = output[-6000:]
    return CheckResult(
        name=name,
        status="PASS" if code == 0 else "FAIL",
        duration_seconds=time.monotonic() - started,
        detail=output,
        command=argv,
        exit_code=code,
    )


def write_reports(config: dict[str, Any], level: str, results: list[CheckResult]) -> dict[str, Any]:
    failed = [result for result in results if result.status == "FAIL"]
    warnings = [result for result in results if result.status == "WARN"]
    payload = {
        "schema_version": 1,
        "project": config.get("project", {}).get("name", ROOT.name),
        "level": level,
        "sha": current_sha(),
        "branch": current_branch(),
        "result": "BLOCKED" if failed else "PASS",
        "violations_found": bool(failed),
        "warning_count": len(warnings),
        "checks": [asdict(result) for result in results],
    }
    gate = config["gate"]
    json_path = ROOT / str(gate.get("report_json", "reports/pr-gate.json"))
    md_path = ROOT / str(gate.get("report_markdown", "reports/pr-gate.md"))
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    lines = [
        "# PR Gate Report",
        "",
        f"- Result: **{payload['result']}**",
        f"- Level: `{level}`",
        f"- Branch: `{payload['branch']}`",
        f"- SHA: `{payload['sha']}`",
        f"- Violations: `{str(payload['violations_found']).lower()}`",
        "",
        "## Checks",
        "",
    ]
    for result in results:
        lines.append(f"### {result.status} — {result.name}")
        lines.append("")
        if result.command:
            lines.append(f"Command: `{' '.join(shlex.quote(item) for item in result.command)}`")
            lines.append("")
        if result.detail:
            lines.append("```text")
            lines.append(result.detail)
            lines.append("```")
            lines.append("")
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--level", choices=LEVELS, default="gate")
    args = parser.parse_args()

    config = load_config()
    base_ref = resolve_base_ref(config)
    try:
        files = changed_files(base_ref)
    except Exception:
        files = []

    results = [
        execute_check("branch-and-sha", lambda: check_branch_and_sha(config)),
        execute_check("changed-file-policy", lambda: check_changed_file_policy(config, files)),
        execute_check("git-diff-check", check_diff),
        execute_check("working-tree", lambda: check_worktree(config, args.level)),
        execute_check("conflict-markers", lambda: check_conflict_markers(files)),
        execute_check("workflow-action-pinning", check_actions_pinned),
    ]
    results.extend(run_static_audits(config))
    for command in configured_commands(config, args.level):
        results.append(run_command(command))

    payload = write_reports(config, args.level, results)
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0 if payload["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
