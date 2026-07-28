# Adoption Checklist

## Repository identity

- [ ] Rename the project in `governance.toml`.
- [ ] Replace CODEOWNERS if ownership differs.
- [ ] Choose private or public visibility intentionally.
- [ ] Add a license only when distribution terms are decided.

## Commands

- [ ] Replace example fast commands.
- [ ] Add focused slice tests.
- [ ] Add full test, type, and integration commands.
- [ ] Add migration checks when databases exist.
- [ ] Add dependency and security checks.

## Contracts

- [ ] Document tenancy and ownership.
- [ ] Document API compatibility.
- [ ] Document async and worker behavior.
- [ ] Document failure containment and retry policy.
- [ ] Document production data and secret paths.

## Static audits

- [ ] Add known forbidden patterns.
- [ ] Add production-path inventory checks.
- [ ] Add generated-file checks.
- [ ] Add action pinning and workflow policy checks.

## GitHub

- [ ] Confirm `quality-gate` succeeds.
- [ ] Configure the main-branch ruleset.
- [ ] Enable squash merge.
- [ ] Run the dependency-free gate locally.
- [ ] Optionally install Nox and pre-commit wrappers.
- [ ] Test a Draft PR from creation through closure.
