# Production Governance Template

A reusable repository baseline for shipping software quickly **without sacrificing correctness**.

The central idea is simple:

> Machines verify repeatable facts. Reviewers evaluate design, correctness, risk, and maintainability.

This template turns that principle into a working repository with:

- one deterministic quality gate;
- fast, slice, and full validation levels;
- machine-readable JSON and Markdown reports;
- pre-commit integration;
- a GitHub Actions workflow that runs the same local gate;
- pull-request and review standards;
- agent instructions for Codex, ZCode, Claude, and other coding agents;
- configurable changed-file, forbidden-path, branch, SHA, and static-audit checks;
- a rule that every discovered defect becomes a permanent regression check.

## Start here

```bash
python scripts/pr_gate.py --level fast
python scripts/pr_gate.py --level slice
python scripts/pr_gate.py --level gate
```

Nox is an optional convenience wrapper when it is available:

```bash
python scripts/pr_gate.py --level gate
```

The authoritative command before a push or final review is:

```bash
python -m nox -s gate
```

It writes:

```text
reports/pr-gate.json
reports/pr-gate.md
```

## Workflow

```text
feature branch
→ Draft PR
→ implement the complete slice
→ nox -s gate
→ one consolidated review
→ one closure remediation if required
→ squash merge
```

## Adoption

1. Create a new repository from this template.
2. Edit `governance.toml` for the project’s commands and protected paths.
3. Replace the example tests with project tests.
4. Read `docs/ADOPTION_CHECKLIST.md`.
5. Configure the GitHub ruleset after the first successful CI run.

## Core rules

- A PR represents one coherent, reviewable slice.
- Draft means work is still changing; Ready means the gate is green.
- Never claim a gate passed from prose. Use the generated report.
- Do not make reviewers rediscover machine-checkable defects.
- Every real defect found in review becomes a test or permanent gate rule.
- Use squash merge for one logical change per PR.
- Keep secrets and generated data out of commits.

See `docs/OPERATING_MODEL.md` for the complete model.

## Publish the prepared Git repository

Create an empty private GitHub repository named `production-governance-template` without adding a README, license, or `.gitignore`. Then run one of:

### Windows PowerShell

```powershell
.\scripts\publish_to_github.ps1 -RepositoryUrl "https://github.com/Tariq990/production-governance-template.git"
```

### Bash

```bash
./scripts/publish_to_github.sh "https://github.com/Tariq990/production-governance-template.git"
```
