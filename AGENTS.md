# Agent Operating Contract

These instructions apply to every coding agent working in this repository.

## Before modifying files

1. Fetch the current remote branch.
2. Verify the expected branch and SHA when supplied.
3. Verify the working tree is clean.
4. Read the PR objective, non-goals, contracts, and allowed-file scope.
5. Inspect every production path affected by the requested behavior.

## During implementation

- Implement the complete requested slice, not only the first visible call site.
- Preserve existing public behavior unless the task explicitly changes it.
- Do not hide unexpected failures silently.
- Do not expose raw exception text, tokens, credentials, or provider responses.
- Do not introduce synchronous network work inside an async event loop.
- Use one authoritative helper rather than duplicating production logic.
- Tests must invoke real production entry points when claiming route, worker, CLI, or agent coverage.
- A helper-only test must never be described as full production-path coverage.

## Validation

Run while developing:

```bash
python scripts/pr_gate.py --level fast
```

Before declaring a slice complete:

```bash
python scripts/pr_gate.py --level slice
```

Before pushing or requesting final review:

```bash
python scripts/pr_gate.py --level gate
```

A task is not complete unless:

- the command exits zero;
- `reports/pr-gate.json` contains `"result": "PASS"`;
- no machine-readable assertion reports a violation;
- the working tree state matches the task contract;
- no forbidden or out-of-scope files changed.

Never write “all gates pass” when the JSON report says otherwise.

## Git safety

Do not, unless explicitly authorized:

- force-push;
- rebase a reviewed branch;
- rewrite history;
- merge;
- mark a Draft PR Ready;
- modify PR metadata;
- disable or bypass checks;
- add blanket ignores;
- alter baselines merely to conceal a new violation.

## Final report

Return facts, not impressions:

- old and new full SHA;
- exact files changed;
- behavior implemented;
- production paths audited;
- focused and full test counts;
- gate report path and result;
- policy result;
- clean-tree status;
- known limitations separated into blockers and follow-ups.
