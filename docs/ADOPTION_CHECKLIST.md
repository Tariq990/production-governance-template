# Adoption checklist

- [ ] Set the project name and commands in `governance.toml`.
- [ ] Define forbidden and protected paths.
- [ ] Add project tests and required test nodes.
- [ ] Create an owner-approved contract in `governance/contracts/` on the base branch.
- [ ] Keep the standing `governance/contract-administration` lane limited to contract JSON.
- [ ] Install hooks with `python scripts/install_governance_hooks.py`.
- [ ] Confirm both workflows pass on a test PR.
- [ ] Make only squash merge available and delete merged branches automatically.
- [ ] Require pull requests, up-to-date branches, resolved conversations, linear history, and the three status checks.
- [ ] Block force pushes and branch deletion.
- [ ] Enable Dependabot and secret scanning features available to the repository plan.
- [ ] Require full-length Action SHAs in repository Actions settings.
