# Review Standard

## Review order

1. Verify exact remote head.
2. Read objective, scope, non-goals, and contracts.
3. Inspect architecture and production entry points.
4. Inspect tests for realism.
5. Inspect implementation details.
6. Confirm gate evidence.
7. Publish one consolidated report.

## Severity

- **BLOCKER** — confirmed production defect, security issue, data corruption, contract violation, or unsafe rollout.
- **REQUIRED** — must be fixed before the slice closes.
- **SUGGESTION** — improvement that does not block closure.
- **NIT** — minor readability or consistency point.
- **FYI** — contextual information.
- **FOLLOW-UP** — valid future work tracked separately.

## Review quality rules

- Do not block on personal preference.
- Do not relabel deferred scope as a blocker unless the PR claims to implement it.
- Do not accept helper-only tests as proof of route or worker wiring.
- Do not repeat machine-checkable findings already enforced by the gate.
- Identify design blockers early.
- Re-review only the remediation diff plus affected contracts.
- State limitations honestly, including unavailable integration environments.
