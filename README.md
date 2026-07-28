# Production Governance Template

A public reusable GitHub template for reliable human and coding-agent delivery.

## What it enforces

- deterministic fast, slice, and gate levels;
- owner-approved task contracts loaded from the protected base branch;
- fail-closed base-ref and changed-file validation;
- committed, staged, and unstaged whitespace checks;
- deleted-test, removed-definition, and missing-node detection;
- required tests that are collected and executed explicitly;
- stale-report prevention and nonce-bound verified pushes;
- pre-push proof validation that works in normal and linked worktrees;
- machine-readable JSON, Markdown, and delivery reports;
- stable policy baselines identified by path and snippet hash;
- GitHub Actions bound to the real PR branch and head SHA.

## Authoritative commands

```bash
python scripts/pr_gate.py --level fast
python scripts/pr_gate.py --level slice --contract .gate/task-contract.json
python scripts/pr_gate.py --level gate --contract .gate/task-contract.json
python scripts/verified_push.py --contract .gate/task-contract.json
```

Nox may wrap these commands, but `scripts/pr_gate.py` and its JSON report remain authoritative.

## Adoption

1. Create a repository from this public template.
2. Customize `governance.toml` commands and protected paths.
3. Copy `.gate/task-contract.example.json` into an owner-approved base-branch contract under `governance/contracts/`.
4. Add project-specific policy rules and tests.
5. Run the workflows once.
6. Configure a GitHub ruleset that requires `quality-gate`, `Repository Policy Check`, and `Policy Checker Tests`.

Local hooks are intentionally bypassable by Git; they are workflow aids, not the final security boundary. Required server-side checks and branch rules provide hard merge enforcement.

See `docs/ADOPTION_CHECKLIST.md` and `docs/OPERATING_MODEL.md`.
