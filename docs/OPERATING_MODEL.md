# Operating Model

## Purpose

Maximize delivery speed by removing repeated manual verification, not by lowering the correctness bar.

## Division of responsibility

### Machines verify

- formatting and lint;
- compilation and types;
- tests;
- policy assertions;
- changed-file scope;
- forbidden paths and secrets;
- deterministic static audits;
- branch and SHA expectations;
- report consistency.

### Reviewers verify

- design and architecture;
- behavior and edge cases;
- security and trust boundaries;
- data ownership and isolation;
- concurrency and idempotency;
- failure handling;
- performance and maintainability;
- whether tests represent production behavior.

## Lifecycle

1. Define the slice and non-goals.
2. Open a Draft PR.
3. Implement all known production paths.
4. Run `fast` continuously.
5. Run `slice` before handoff.
6. Run `gate` before final review.
7. Receive one consolidated review.
8. Perform one closure remediation when required.
9. Convert every confirmed defect into permanent protection.
10. Squash merge.

## Definition of done

A slice is done when:

- intended production paths are wired;
- authoritative contracts are preserved;
- machine gate reports PASS;
- no production blocker remains;
- follow-ups are recorded as issues;
- rollback is understood;
- the PR remains one coherent change.

## Review-loop budget

Target:

```text
implementation
→ internal gate repair loop
→ consolidated review
→ at most one closure remediation
```

A second remediation is acceptable only when the first remediation introduced a new production defect or the original review missed a material issue.
