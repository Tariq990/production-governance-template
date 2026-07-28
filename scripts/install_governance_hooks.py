#!/usr/bin/env python3
from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
subprocess.run(["git", "config", "core.hooksPath", ".githooks"], cwd=ROOT, check=True)
print("Installed repository hooks from .githooks")
