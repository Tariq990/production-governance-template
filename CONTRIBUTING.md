# Contributing

## Branches

Use short-lived branches:

```text
feature/<name>
fix/<name>
governance/<name>
```

Keep the pull request Draft until implementation and validation are complete.

## Pull-request scope

A pull request should contain one coherent change. Split unrelated formatting, migrations, refactors, backend behavior, and frontend behavior when they can be reviewed independently.

Recommended production-code size:

- preferred: 150–500 meaningful changed lines;
- review carefully above 800 meaningful changed lines;
- generated files and focused tests are evaluated separately.

## Commit policy

Use descriptive commits during implementation. The repository’s preferred merge method is squash merge, producing one logical commit per PR.

Examples:

```text
feat: add category-aware export
fix: preserve tenant ownership during scheduling
governance: add deterministic quality gate
```

## Validation levels

### Fast

```bash
python scripts/pr_gate.py --level fast
```

Run continuously. It should remain inexpensive.

### Slice

```bash
python scripts/pr_gate.py --level slice
```

Run before handing a complete feature slice to review.

### Gate

```bash
python scripts/pr_gate.py --level gate
```

Run before push, final review, or merge consideration.

## Review labels

Use these severities:

- `BLOCKER`: confirmed production defect, security issue, data corruption, or contract violation.
- `REQUIRED`: must be addressed before closure.
- `SUGGESTION`: worthwhile but optional improvement.
- `NIT`: minor style or naming point.
- `FYI`: informational context.
- `FOLLOW-UP`: valid work recorded separately and not blocking this PR.

Reviewers should provide one consolidated report. Do not drip-feed unrelated findings across repeated cycles.

## Regression rule

Every confirmed defect found during implementation or review must produce one of:

- a regression test;
- a static audit;
- a policy check;
- a documented contract enforced by the gate.
