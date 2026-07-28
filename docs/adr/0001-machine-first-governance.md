# ADR-0001: Machine-first repository governance

- Status: Accepted
- Date: 2026-07-28
- Owners: @Tariq990

## Context

Repeated manual cycles allowed contradictory reports, missed production paths, helper-only tests presented as full wiring evidence, and review effort spent on deterministic checks.

## Decision

Use one local and CI quality gate as the authoritative source of verification. Human review focuses on design, correctness, risk, and test realism.

## Consequences

### Positive

- fewer review loops;
- consistent local and CI behavior;
- machine-readable evidence;
- recurring defects become permanent checks;
- reviewers spend time on high-value reasoning.

### Negative

- initial setup cost;
- project-specific commands and audits must be maintained;
- integration environments still require real infrastructure.

## Enforcement

- `noxfile.py` exposes fast, slice, and gate sessions;
- `scripts/pr_gate.py` produces deterministic reports;
- pre-commit and GitHub Actions run the same gate;
- PR template requires contracts, production paths, and validation evidence.
