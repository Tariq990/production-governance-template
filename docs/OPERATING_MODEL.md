# Operating model

1. The owner approves a branch-specific task contract on the protected base branch.
2. A fixed contract-administration branch can add exact task contracts but no implementation files.
3. The implementation branch changes only allowed files and cannot weaken the trusted contract.
4. Local development uses fast and slice gates.
5. `verified_push.py` runs a fresh full gate, binds the report to a nonce, creates a proof in Git's real metadata directory, and pushes through the hook.
6. Pull-request CI checks the synthetic merge tree while reporting the real source branch and SHA.
7. Required server-side checks—not local hooks—decide whether the PR can merge.
8. Every defect discovered in review becomes a regression test or permanent gate rule.
