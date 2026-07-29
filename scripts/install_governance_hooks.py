from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOOK = ROOT / ".githooks" / "pre-push"

subprocess.run(
    ["git", "config", "core.hooksPath", ".githooks"],
    cwd=ROOT,
    check=True,
)
if os.name != "nt" and HOOK.exists():
    HOOK.chmod(
        HOOK.stat().st_mode
        | stat.S_IXUSR
        | stat.S_IXGRP
        | stat.S_IXOTH
    )
print("Installed repository hooks from .githooks")
