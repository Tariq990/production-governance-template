# Agent Operating Contract

These rules apply to every coding agent in repositories created from this template.

## Before modifying files

1. Fetch the current remote branch and verify the full SHA.
2. Confirm the expected branch, clean working tree, task contract, allowed files, and protected paths.
3. Inspect every production entry point affected by the requested behavior.

## Implementation integrity

- Complete the requested slice; a helper-only implementation is not production-path completion.
- Never weaken an approved task contract: do not remove required tests, widen allowed files, clear protected paths, or alter approval metadata. Approved contracts are owner-controlled.
- Never make tests pass by deleting, replacing, skipping, xfail-ing, or renaming required behavior.
- Preserve test node IDs unless an explicit waiver includes a reason and approver.
- Do not hide unexpected failures, secrets, provider responses, or raw exception text.

## Required validation

During development:

```bash
python scripts/pr_gate.py --level fast
```

Before review:

```bash
python scripts/pr_gate.py --level slice --contract .gate/task-contract.json
```

Before push:

```bash
python scripts/install_governance_hooks.py
python scripts/verified_push.py --contract .gate/task-contract.json
```

Never substitute a direct push or any bypass:

- `git push`
- `git push --no-verify`
- manually fabricated proof files
- proof fabrication
- history rewriting, rebase, force-push, or amend to escape a blocked gate

When the gate reports `BLOCKED`, fix the cause or return `Progress Report — Incomplete`. Do not claim completion.

The stable policy runner is:

```bash
python scripts/verify_repo_policy_stable.py --root . --json
```

## Final reporting

A final report must cite the remote full SHA, exact changed files, production paths, focused and full test counts, report result, policy result, data diff, and clean-tree status. `reports/pr-gate.json` is authoritative; prose must never contradict it.
