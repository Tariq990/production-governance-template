from __future__ import annotations

import nox

nox.options.default_venv_backend = "venv"
nox.options.reuse_existing_virtualenvs = True


def _run_gate(session: nox.Session, level: str) -> None:
    session.run("python", "scripts/pr_gate.py", "--level", level)


@nox.session
def fast(session: nox.Session) -> None:
    """Cheap checks for active development and pre-commit."""
    _run_gate(session, "fast")


@nox.session
def slice(session: nox.Session) -> None:
    """Feature-slice checks before review handoff."""
    _run_gate(session, "slice")


@nox.session
def gate(session: nox.Session) -> None:
    """Authoritative full repository gate."""
    _run_gate(session, "gate")
