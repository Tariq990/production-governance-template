## Objective

<!-- What user or system problem does this PR solve? -->

## Scope

<!-- Exact behavior and files intentionally changed. -->

## Non-goals

<!-- Explicitly deferred work. -->

## Authoritative contracts

<!-- Ownership, compatibility, persistence, security, concurrency, or API rules. -->

## Production paths audited

- [ ] API / synchronous path
- [ ] background path
- [ ] worker / scheduler path
- [ ] CLI / operator path
- [ ] agent / automation path
- [ ] migration / maintenance path

## Risks

- [ ] data integrity
- [ ] tenant or ownership isolation
- [ ] async blocking
- [ ] retries and idempotency
- [ ] backward compatibility
- [ ] security and secrets
- [ ] performance and pagination

## Validation

- [ ] `python scripts/pr_gate.py --level fast`
- [ ] `python scripts/pr_gate.py --level slice`
- [ ] `python scripts/pr_gate.py --level gate`
- [ ] `reports/pr-gate.json` says `PASS`
- [ ] no forbidden or out-of-scope files changed
- [ ] no production data changed

## Rollback

<!-- How can this change be safely reverted or disabled? -->

## Follow-ups

<!-- Link issues. Do not leave untracked follow-up prose. -->
