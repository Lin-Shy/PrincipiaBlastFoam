from __future__ import annotations

import os
import sys
from pathlib import Path


DEEPAGENTS_ROOT = Path(os.getenv("PRINCIPIA_DEEPAGENTS_ROOT", '/data/graduation-projects/PrincipiaBlastFoam'))
DEEPAGENTS_PYTHON = DEEPAGENTS_ROOT / ".venv" / "bin" / "python"
if DEEPAGENTS_PYTHON.exists() and Path(sys.prefix).resolve() != (DEEPAGENTS_ROOT / ".venv").resolve():
    os.execv(str(DEEPAGENTS_PYTHON), [str(DEEPAGENTS_PYTHON), __file__, *sys.argv[1:]])

DEEPAGENTS_SRC = DEEPAGENTS_ROOT / "src"
if str(DEEPAGENTS_SRC) not in sys.path:
    sys.path.insert(0, str(DEEPAGENTS_SRC))

from principia_deepagents.legacy_cli import workflow_main


if __name__ == "__main__":
    sys.exit(workflow_main())
