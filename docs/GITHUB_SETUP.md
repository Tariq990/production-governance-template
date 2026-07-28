# GitHub Setup

After the workflow succeeds at least once, configure a repository ruleset for `main`.

Recommended settings:

- require a pull request before merging;
- require the `quality-gate` status check;
- require all conversations resolved;
- block force pushes;
- block branch deletion;
- allow squash merge and disable unnecessary merge methods;
- require a new review when material code changes after approval once a second human reviewer exists;
- keep workflow permissions read-only by default;
- pin any future third-party actions to full commit SHAs.

Do not enable rules that the current team cannot satisfy. For a single-owner repository, the automated gate is the technical barrier; add mandatory human approval when another qualified reviewer is available.
