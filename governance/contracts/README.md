# Owner-approved task contracts

Pull-request contracts live on the protected base branch, not on the implementation branch.

For a branch such as `feature/payments`, create:

```text
governance/contracts/feature__payments.json
```

The `quality-gate` workflow derives this path from `github.head_ref` and reads it with `git show origin/$GITHUB_BASE_REF:...`. A contract modified by the pull request is never trusted.

Create new contracts only through the standing
`governance/contract-administration` branch. Its base-controlled contract is
`.gate/task-contract.example.json`, and it permits contract JSON only. It
rejects broad allowed-file patterns and pre-authorized waivers.

Contracts define the base ref, exact allowed files, protected paths, required
test nodes, focused commands, and owner approval metadata. Changes to this
directory require CODEOWNER review and server-side required checks.
