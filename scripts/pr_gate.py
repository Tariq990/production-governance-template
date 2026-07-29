#!/usr/bin/env python3
"""Deterministic repository quality gate with contract and test integrity."""
from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
import tempfile
import time
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable

try:
    import tomllib
except ModuleNotFoundError:
    raise SystemExit("Python 3.11+ is required") from None

ROOT = Path(__file__).resolve().parent.parent
LEVELS = {"fast": 1, "slice": 2, "gate": 3}
DEFAULT_CONTRACT = ROOT / ".gate" / "task-contract.json"


@dataclass
class CheckResult:
    name: str
    status: str
    duration_seconds: float
    detail: str = ""
    command: list[str] | None = None
    exit_code: int | None = None


@dataclass
class CollectionEvidence:
    base_nodes: set[str]
    head_nodes: set[str]
    missing_nodes: list[str]
    waived_missing_nodes: list[str]


class GateFailure(RuntimeError):
    pass


def run_process(argv: list[str], *, cwd: Path | None = None) -> tuple[int, str]:
    completed = subprocess.run(
        argv,
        cwd=cwd or ROOT,
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
        raise GateFailure(output.strip() or f"git {' '.join(args)} failed")
    return output.strip()


def source_branch() -> str:
    return os.getenv("GATE_SOURCE_BRANCH") or git("rev-parse", "--abbrev-ref", "HEAD")


def source_sha() -> str:
    return os.getenv("GATE_SOURCE_SHA") or git("rev-parse", "HEAD")


def validate_base_ref(
    config: dict[str, Any], contract: dict[str, Any] | None
) -> tuple[str, bool, str]:
    if contract and contract.get("base_ref"):
        base_ref = str(contract["base_ref"])
        code, output = run_process(["git", "rev-parse", "--verify", f"{base_ref}^{{commit}}"])
        if code != 0:
            raise GateFailure(f"contract base_ref {base_ref!r} is not resolvable: {output.strip()}")
        code, output = run_process(["git", "merge-base", base_ref, "HEAD"])
        if code != 0 or not output.strip():
            raise GateFailure(f"no merge base for {base_ref!r} and HEAD: {output.strip()}")
        return base_ref, False, "contract base_ref validated (fail-closed)"

    candidates = [
        ("GATE_BASE_REF", os.getenv("GATE_BASE_REF", "")),
        ("governance.toml", str(config.get("gate", {}).get("base_ref", ""))),
        ("fallback", "HEAD~1"),
    ]
    usable = [(name, ref) for name, ref in candidates if ref]
    for index, (name, ref) in enumerate(usable):
        code, _ = run_process(["git", "rev-parse", "--verify", f"{ref}^{{commit}}"])
        if code == 0:
            return ref, index > 0, f"resolved from {name}"
    raise GateFailure("no usable base ref")


def git_lines(*args: str) -> list[str]:
    code, output = run_process(["git", *args])
    if code != 0:
        raise GateFailure(output.strip() or f"git {' '.join(args)} failed")
    return [line.strip().replace("\\", "/") for line in output.splitlines() if line.strip()]


def changed_files(base_ref: str) -> list[str]:
    return sorted(set(git_lines("diff", "--name-only", base_ref, "HEAD")))


def deleted_files(base_ref: str) -> list[str]:
    return sorted(
        set(
            git_lines(
                "diff", "--name-only", "--diff-filter=D", base_ref, "HEAD"
            )
        )
    )


def committed_diff(base_ref: str) -> str:
    code, output = run_process(["git", "diff", base_ref, "HEAD"])
    if code != 0:
        raise GateFailure(output.strip() or "unable to read committed diff")
    return output


def path_matches_rule(path: str, rule: str) -> bool:
    if any(token in rule for token in ("*", "?", "[")):
        return fnmatch.fnmatch(path, rule)
    if rule.endswith("/"):
        return path.startswith(rule)
    return path == rule


def check_identity(config: dict[str, Any], contract: dict[str, Any] | None) -> str:
    branch, sha = source_branch(), source_sha()
    if contract:
        expected_branch = contract.get("expected_branch")
        expected_sha = contract.get("expected_head_sha")
        if expected_branch and branch != expected_branch:
            raise GateFailure(f"contract branch mismatch: expected {expected_branch}, got {branch}")
        if expected_sha and sha != expected_sha:
            raise GateFailure(f"contract SHA mismatch: expected {expected_sha}, got {sha}")
    env_branch = os.getenv("EXPECTED_BRANCH")
    env_sha = os.getenv("EXPECTED_HEAD_SHA")
    if env_branch and branch != env_branch:
        raise GateFailure(f"branch mismatch: expected {env_branch}, got {branch}")
    if env_sha and sha != env_sha:
        raise GateFailure(f"SHA mismatch: expected {env_sha}, got {sha}")
    patterns = config.get("gate", {}).get("allowed_branch_patterns", [])
    if patterns and not any(fnmatch.fnmatch(branch, pattern) for pattern in patterns):
        raise GateFailure(f"branch {branch!r} does not match allowed patterns")
    return f"branch={branch} sha={sha}"


def check_file_policy(
    config: dict[str, Any], files: list[str], contract: dict[str, Any] | None
) -> str:
    gate = config.get("gate", {})
    forbidden = [str(item) for item in gate.get("forbidden_paths", [])]
    extensions = [str(item) for item in gate.get("forbidden_extensions", [])]
    violations = [path for path in files if any(path_matches_rule(path, rule) for rule in forbidden)]
    violations += [path for path in files if any(path.endswith(ext) for ext in extensions)]
    if contract is not None:
        allowed = {
            str(item).replace("\\", "/")
            for item in contract.get("allowed_files", [])
        }
        allowed_patterns = [
            str(item).replace("\\", "/")
            for item in contract.get("allowed_file_patterns", [])
        ]
        if not allowed and not allowed_patterns:
            raise GateFailure("contract has no allowed file scope")
        violations += [
            path
            for path in files
            if path not in allowed
            and not any(
                path_matches_rule(path, rule) for rule in allowed_patterns
            )
        ]
        protected = [str(item) for item in contract.get("protected_paths", [])]
        violations += [
            path for path in files if any(path_matches_rule(path, rule) for rule in protected)
        ]
    if violations:
        raise GateFailure("forbidden or out-of-scope files: " + ", ".join(sorted(set(violations))))
    return f"{len(files)} changed file(s) accepted"


def check_contract_administration(
    files: list[str],
    contract: dict[str, Any] | None,
    *,
    root: Path = ROOT,
) -> str:
    """Validate contracts added through the standing owner-controlled lane."""
    if not contract or not contract.get("contract_administration"):
        return "not applicable"
    if not files:
        raise GateFailure("contract administration change is empty")

    approver = str(contract.get("contract_approver", "")).strip()
    if not approver:
        raise GateFailure("contract administration approver is missing")
    required_protected = {"data/production/", "secrets/", "private_keys/"}

    for path in files:
        normalized = path.replace("\\", "/")
        if (
            not normalized.startswith("governance/contracts/")
            or not normalized.endswith(".json")
        ):
            raise GateFailure(
                "contract administration may only change contract JSON: "
                + normalized
            )
        contract_file = root / normalized
        if not contract_file.is_file():
            raise GateFailure(f"contract file is missing: {normalized}")
        try:
            task = json.loads(contract_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise GateFailure(
                f"invalid task contract {normalized}: {exc}"
            ) from exc

        expected_branch = Path(normalized).stem.replace("__", "/")
        if task.get("expected_branch") != expected_branch:
            raise GateFailure(
                f"{normalized} must bind expected_branch to {expected_branch}"
            )
        if task.get("base_ref") != "origin/main":
            raise GateFailure(f"{normalized} must use base_ref origin/main")
        if task.get("expected_head_sha") not in ("", None):
            raise GateFailure(f"{normalized} must not pre-authorize a head SHA")
        if task.get("approved_by") != approver:
            raise GateFailure(f"{normalized} has invalid approved_by metadata")
        if not str(task.get("approval_reason", "")).strip():
            raise GateFailure(f"{normalized} has no approval reason")
        if task.get("forbid_test_removals") is not True:
            raise GateFailure(f"{normalized} must forbid test removals")
        protected = set(task.get("protected_paths", []))
        if not required_protected.issubset(protected):
            raise GateFailure(
                f"{normalized} must protect production data and secret paths"
            )
        if task.get("waivers") != []:
            raise GateFailure(f"{normalized} may not pre-authorize waivers")
        if task.get("allowed_file_patterns"):
            raise GateFailure(
                f"{normalized} may not use broad allowed file patterns"
            )

        allowed = task.get("allowed_files")
        required = task.get("required_tests")
        focused = task.get("focused_commands")
        if not isinstance(allowed, list) or not allowed:
            raise GateFailure(f"{normalized} must list exact allowed files")
        if not all(
            isinstance(item, str) and item.strip() for item in allowed
        ):
            raise GateFailure(
                f"{normalized} has an invalid allowed_files entry"
            )
        if not isinstance(required, list) or not required:
            raise GateFailure(f"{normalized} must list required tests")
        if not isinstance(focused, list) or not focused:
            raise GateFailure(f"{normalized} must list focused commands")
        if any(
            any(
                path_matches_rule(item.replace("\\", "/"), rule)
                for rule in required_protected
            )
            for item in allowed
        ):
            raise GateFailure(
                f"{normalized} may not allow protected production files"
            )

    return f"{len(files)} owner-bound contract file(s) validated"


def check_diff(base_ref: str) -> str:
    commands = [
        ["git", "diff", "--check", base_ref, "HEAD"],
        ["git", "diff", "--check"],
        ["git", "diff", "--cached", "--check"],
    ]
    for command in commands:
        code, output = run_process(command)
        if code != 0:
            raise GateFailure(output.strip() or f"{' '.join(command)} failed")
    return "committed, unstaged, and staged diff checks passed"


def filtered_status(config: dict[str, Any]) -> str:
    ignored = [str(item).rstrip("/") for item in config.get("gate", {}).get("ignore_dirty_paths", [])]
    status = git("status", "--porcelain")
    kept: list[str] = []
    for line in status.splitlines():
        path = line[3:].strip().replace("\\", "/")
        if not any(path == item or path.startswith(item + "/") for item in ignored):
            kept.append(line)
    return "\n".join(kept)


def check_initial_tree(config: dict[str, Any], level: str) -> str:
    if level != "gate" or not config.get("gate", {}).get("require_clean_tree_on_gate", False):
        return "clean-tree enforcement skipped"
    status = filtered_status(config)
    if status:
        raise GateFailure("working tree dirty: " + status.replace("\n", " | "))
    return "working tree clean"


def check_final_tree(initial: str, config: dict[str, Any]) -> tuple[str, str, str]:
    final = filtered_status(config)
    if final or final != initial:
        detail = "working tree modified by gate commands"
        if final:
            detail += ": " + final.replace("\n", " | ")
        return "FAIL", detail, final
    return "PASS", "working tree unchanged after commands", final


def check_conflict_markers(files: list[str]) -> str:
    markers = re.compile(r"^(<<<<<<<|=======|>>>>>>>)", re.MULTILINE)
    found: list[str] = []
    for relative in files:
        path = ROOT / relative
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if markers.search(text):
            found.append(relative)
    if found:
        raise GateFailure("merge-conflict markers: " + ", ".join(found))
    return "no conflict markers"


def check_actions_pinned() -> str:
    workflow_dir = ROOT / ".github" / "workflows"
    if not workflow_dir.exists():
        return "no workflows"
    pattern = re.compile(r"uses:\s*([^\s#]+)")
    violations: list[str] = []
    for path in workflow_dir.glob("*.y*ml"):
        for match in pattern.finditer(path.read_text(encoding="utf-8")):
            action = match.group(1)
            if action.startswith("./"):
                continue
            ref = action.rsplit("@", 1)[-1] if "@" in action else ""
            if not re.fullmatch(r"[0-9a-fA-F]{40}", ref):
                violations.append(f"{path.relative_to(ROOT)}: {action}")
    if violations:
        raise GateFailure("unpinned actions: " + "; ".join(violations))
    return "all external actions are SHA-pinned"


def waiver_patterns(contract: dict[str, Any] | None, types: set[str]) -> set[str]:
    patterns: set[str] = set()
    for waiver in (contract or {}).get("waivers", []):
        if (
            waiver.get("type") in types
            and waiver.get("pattern")
            and waiver.get("reason")
            and waiver.get("approver")
        ):
            patterns.add(str(waiver["pattern"]))
    return patterns


def check_test_deletions(base_ref: str, contract: dict[str, Any] | None) -> str:
    deleted = [path for path in deleted_files(base_ref) if path.startswith("tests/") and path.endswith(".py")]
    if not deleted:
        return "no test files deleted"
    patterns = waiver_patterns(contract, {"test_file_deletion"})
    unwaived = [path for path in deleted if not any(fnmatch.fnmatch(path, p) for p in patterns)]
    if unwaived:
        raise GateFailure("test files deleted without waiver: " + ", ".join(unwaived))
    return f"{len(deleted)} deleted test file(s) waived"


def removed_test_definitions(base_ref: str) -> list[str]:
    removed: list[str] = []
    for line in committed_diff(base_ref).splitlines():
        if not line.startswith("-") or line.startswith("---"):
            continue
        text = line[1:].strip()
        if text.startswith("def test_") or text.startswith("async def test_") or text.startswith("class Test"):
            removed.append(text)
    return removed


def check_removed_test_definitions(base_ref: str, contract: dict[str, Any] | None) -> str:
    if not (contract or {}).get("forbid_test_removals", False):
        return "test-definition removal inspection skipped"
    removed = removed_test_definitions(base_ref)
    if not removed:
        return "no test definitions removed"
    patterns = waiver_patterns(contract, {"test_removal"})
    unwaived = [item for item in removed if not any(fnmatch.fnmatch(item, p) for p in patterns)]
    if unwaived:
        raise GateFailure("test definitions removed without waiver: " + "; ".join(unwaived))
    return f"{len(removed)} removed test definition(s) waived"


def parse_collection(output: str) -> set[str]:
    return {
        line.strip().split(" ", 1)[0]
        for line in output.splitlines()
        if line.strip().startswith("tests/") and "::" in line
    }


def collect_nodes(*, cwd: Path | None = None, label: str) -> set[str]:
    code, output = run_process([sys.executable, "-m", "pytest", "--collect-only", "-q"], cwd=cwd)
    if code != 0:
        raise GateFailure(f"{label} test collection failed (exit {code}): {output.strip()}")
    return parse_collection(output)


def collection_evidence(base_ref: str, contract: dict[str, Any] | None) -> CollectionEvidence:
    head_nodes = collect_nodes(label="HEAD")
    base_sha = git("rev-parse", base_ref)
    cleanup_error = ""
    with tempfile.TemporaryDirectory(prefix="gate-base-") as directory:
        worktree = Path(directory) / "worktree"
        code, output = run_process(["git", "worktree", "add", "--detach", str(worktree), base_sha])
        if code != 0:
            raise GateFailure(f"base worktree creation failed: {output.strip()}")
        try:
            base_nodes = collect_nodes(cwd=worktree, label="base")
        finally:
            cleanup_code, cleanup_output = run_process(["git", "worktree", "remove", "--force", str(worktree)])
            if cleanup_code != 0:
                cleanup_error = cleanup_output.strip() or f"exit {cleanup_code}"
    if cleanup_error:
        raise GateFailure(f"base worktree cleanup failed: {cleanup_error}")
    missing = sorted(base_nodes - head_nodes)
    patterns = waiver_patterns(contract, {"test_node_removal", "test_removal"})
    waived = [node for node in missing if any(fnmatch.fnmatch(node, p) for p in patterns)]
    unwaived = [node for node in missing if node not in waived]
    if unwaived:
        preview = ", ".join(unwaived[:15])
        raise GateFailure(f"test nodes disappeared: {preview}")
    return CollectionEvidence(base_nodes, head_nodes, missing, waived)


def execute_required_tests(contract: dict[str, Any] | None) -> list[dict[str, Any]]:
    required = [str(item) for item in (contract or {}).get("required_tests", [])]
    if not required:
        return []
    nodes = collect_nodes(label="HEAD")
    selected: list[tuple[str, str]] = []
    missing: list[str] = []
    for pattern in required:
        matches = sorted(node for node in nodes if fnmatch.fnmatch(node, pattern))
        if not matches:
            missing.append(pattern)
        selected.extend((pattern, node) for node in matches)
    if missing:
        raise GateFailure("required tests not in collection: " + ", ".join(missing))
    records: list[dict[str, Any]] = []
    for pattern, node in selected:
        started = time.monotonic()
        code, output = run_process([sys.executable, "-m", "pytest", "-q", node])
        record = {
            "pattern": pattern,
            "node": node,
            "collected": True,
            "executed": True,
            "exit_code": code,
            "duration_seconds": round(time.monotonic() - started, 6),
            "output": output.strip()[-2000:],
        }
        records.append(record)
        if code != 0:
            raise GateFailure(f"required test failed: {node} (exit {code})")
    return records


def execute_check(name: str, function: Callable[[], str]) -> CheckResult:
    started = time.monotonic()
    try:
        return CheckResult(name, "PASS", time.monotonic() - started, str(function()))
    except Exception as exc:
        return CheckResult(name, "FAIL", time.monotonic() - started, f"{type(exc).__name__}: {exc}")


def run_command(name: str, argv: list[str]) -> CheckResult:
    started = time.monotonic()
    code, output = run_process(argv)
    detail = output.strip()[-6000:]
    return CheckResult(name, "PASS" if code == 0 else "FAIL", time.monotonic() - started, detail, argv, code)


def configured_commands(config: dict[str, Any], level: str) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    for candidate, rank in LEVELS.items():
        if rank <= LEVELS[level]:
            selected.extend(config.get("commands", {}).get(candidate, []))
    return selected


def run_audits(config: dict[str, Any]) -> list[CheckResult]:
    results: list[CheckResult] = []
    for rule in config.get("audits", {}).get("regex", []):
        started = time.monotonic()
        pattern = re.compile(str(rule["pattern"]), re.MULTILINE)
        hits: list[str] = []
        for path in ROOT.glob(str(rule.get("glob", "**/*"))):
            if not path.is_file() or ".git" in path.parts:
                continue
            try:
                if pattern.search(path.read_text(encoding="utf-8")):
                    hits.append(str(path.relative_to(ROOT)).replace("\\", "/"))
            except (OSError, UnicodeDecodeError):
                continue
        severity = str(rule.get("severity", "error")).lower()
        status = "PASS" if not hits else ("WARN" if severity == "warning" else "FAIL")
        detail = str(rule.get("message", ""))
        if hits:
            detail += " Hits: " + ", ".join(hits)
        results.append(CheckResult(str(rule["name"]), status, time.monotonic() - started, detail))
    return results


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# PR Gate Report",
        "",
        f"- Result: **{payload['result']}**",
        f"- Level: `{payload['level']}`",
        f"- Branch: `{payload['branch']}`",
        f"- SHA: `{payload['head_sha']}`",
        f"- Base: `{payload['base_ref']}` (`{payload['base_sha']}`)",
        f"- Contract SHA-256: `{payload['contract_sha256'] or 'N/A'}`",
        f"- Violations: `{str(payload['violations_found']).lower()}`",
        "",
        "## Checks",
        "",
    ]
    for check in payload["checks"]:
        lines += [f"### {check['status']} — {check['name']}", ""]
        if check.get("command"):
            lines += ["Command: `" + " ".join(shlex.quote(item) for item in check["command"]) + "`", ""]
        if check.get("detail"):
            lines += ["```text", str(check["detail"]), "```", ""]
    return "\n".join(lines)


def write_reports(config: dict[str, Any], payload: dict[str, Any]) -> None:
    gate = config.get("gate", {})
    json_path = ROOT / str(gate.get("report_json", "reports/pr-gate.json"))
    md_path = ROOT / str(gate.get("report_markdown", "reports/pr-gate.md"))
    delivery_path = ROOT / "reports" / "delivery-report.md"
    for path in (json_path, md_path, delivery_path):
        path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(payload), encoding="utf-8")
    delivery_path.write_text(
        "\n".join(
            [
                "# Delivery Report",
                "",
                f"Completion status: {'COMPLETE' if payload['result'] == 'PASS' else 'BLOCKED'}",
                f"Gate result: {payload['result']}",
                f"Remote full SHA: {payload['head_sha']}",
                f"Branch: {payload['branch']}",
                f"Violations found: {str(payload['violations_found']).lower()}",
                f"Changed files: {len(payload['changed_files'])}",
                f"Tests collected: base={payload['base_collected_tests']} head={payload['head_collected_tests']}",
                f"Missing test nodes: {len(payload['missing_test_nodes'])}",
                "",
                "Generated from reports/pr-gate.json.",
            ]
        ),
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--level", choices=list(LEVELS), default="gate")
    parser.add_argument("--contract")
    args = parser.parse_args()

    config = load_config()
    contract_path = Path(args.contract) if args.contract else DEFAULT_CONTRACT
    contract: dict[str, Any] | None = None
    contract_hash: str | None = None
    if args.contract and not contract_path.exists():
        raise GateFailure(f"contract not found: {contract_path}")
    if contract_path.exists():
        try:
            contract = json.loads(contract_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise GateFailure(f"invalid contract JSON: {exc}") from exc
        contract_hash = hashlib.sha256(contract_path.read_bytes()).hexdigest()

    base_ref, fallback_used, fallback_detail = validate_base_ref(config, contract)
    files = changed_files(base_ref)
    base_sha = git("rev-parse", base_ref)
    initial_tree = filtered_status(config)
    results = [
        execute_check("branch-and-sha", lambda: check_identity(config, contract)),
        execute_check("changed-file-policy", lambda: check_file_policy(config, files, contract)),
        execute_check(
            "contract-administration",
            lambda: check_contract_administration(files, contract),
        ),
        execute_check("git-diff-check", lambda: check_diff(base_ref)),
        execute_check("working-tree-initial", lambda: check_initial_tree(config, args.level)),
        execute_check("conflict-markers", lambda: check_conflict_markers(files)),
        execute_check("workflow-action-pinning", check_actions_pinned),
        execute_check("test-file-deletions", lambda: check_test_deletions(base_ref, contract)),
        execute_check("test-removals-in-diff", lambda: check_removed_test_definitions(base_ref, contract)),
    ]

    evidence: CollectionEvidence | None = None
    if args.level in ("slice", "gate") or (contract and contract.get("forbid_test_removals")):
        started = time.monotonic()
        try:
            evidence = collection_evidence(base_ref, contract)
            results.append(
                CheckResult(
                    "test-collection-comparison",
                    "PASS",
                    time.monotonic() - started,
                    f"base={len(evidence.base_nodes)} head={len(evidence.head_nodes)} missing={len(evidence.missing_nodes)}",
                )
            )
        except Exception as exc:
            results.append(CheckResult("test-collection-comparison", "FAIL", time.monotonic() - started, f"{type(exc).__name__}: {exc}"))

    required_records: list[dict[str, Any]] = []
    if contract and contract.get("required_tests"):
        started = time.monotonic()
        try:
            required_records = execute_required_tests(contract)
            results.append(CheckResult("required-tests", "PASS", time.monotonic() - started, f"{len(required_records)} node(s) executed"))
        except Exception as exc:
            results.append(CheckResult("required-tests", "FAIL", time.monotonic() - started, f"{type(exc).__name__}: {exc}"))

    results.extend(run_audits(config))
    focused_records: list[dict[str, Any]] = []
    if contract and contract.get("focused_commands"):
        repeat = max(1, int(contract.get("focused_repeat_count", 1)))
        for iteration in range(1, repeat + 1):
            for index, command in enumerate(contract["focused_commands"], 1):
                argv = [str(item) for item in command] if isinstance(command, list) else shlex.split(str(command))
                result = run_command(f"focused-{iteration}-{index}", argv)
                results.append(result)
                focused_records.append({
                    "iteration": iteration,
                    "command": argv,
                    "status": result.status,
                    "exit_code": result.exit_code,
                    "duration_seconds": result.duration_seconds,
                })

    for spec in configured_commands(config, args.level):
        results.append(run_command(str(spec["name"]), [str(item) for item in spec["argv"]]))

    final_status, final_detail, final_tree = check_final_tree(initial_tree, config)
    results.append(CheckResult("working-tree-final", final_status, 0.0, final_detail))
    failures = [result for result in results if result.status == "FAIL"]
    payload = {
        "schema_version": 3,
        "project": config.get("project", {}).get("name", ROOT.name),
        "level": args.level,
        "branch": source_branch(),
        "head_sha": source_sha(),
        "base_ref": base_ref,
        "base_sha": base_sha,
        "base_fallback_used": fallback_used,
        "fallback_detail": fallback_detail,
        "contract_sha256": contract_hash,
        "run_nonce": os.getenv("GATE_RUN_NONCE") or uuid.uuid4().hex,
        "result": "BLOCKED" if failures else "PASS",
        "violations_found": bool(failures),
        "changed_files": files,
        "test_files_deleted": [path for path in deleted_files(base_ref) if path.startswith("tests/")],
        "removed_test_definitions": removed_test_definitions(base_ref),
        "base_collected_tests": len(evidence.base_nodes) if evidence else None,
        "head_collected_tests": len(evidence.head_nodes) if evidence else None,
        "missing_test_nodes": evidence.missing_nodes if evidence else [],
        "required_test_executions": required_records,
        "focused_repeat_results": focused_records,
        "initial_working_tree_status": initial_tree or "clean",
        "final_working_tree_status": final_tree or "clean",
        "checks": [asdict(result) for result in results],
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    write_reports(config, payload)
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0 if payload["result"] == "PASS" else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except GateFailure as exc:
        print(f"BLOCKED: {exc}", file=sys.stderr)
        raise SystemExit(1) from None
