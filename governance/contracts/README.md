# Owner-approved task contracts

Pull-request contracts live on the protected base branch, not on the implementation branch.

For a branch such as `feature/payments`, create:

```text
governance/contracts/feature_payments.json
```

The `quality-gate` workflow derives this path from `github.head_ref` and reads it with `git show origin/$GITHUB_BASE_REF:...`. A contract modified by the pull request is never trusted.

Contracts define the base ref, allowed files, protected paths, required test nodes, focused commands, repeat count, and explicit owner-approved waivers. Changes to this directory require CODEOWNER review and server-side required checks.
