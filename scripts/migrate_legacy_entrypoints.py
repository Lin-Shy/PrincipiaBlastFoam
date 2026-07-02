from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


DEEPAGENTS_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TARGET_PROJECT = DEEPAGENTS_ROOT.parent / "PrincipiaBlastFoam"
ENTRYPOINTS = ("run_workflow.py", "run_batch_workflow.py")


def wrapper_text(entrypoint: str, deepagents_root: Path) -> str:
    function_name = "workflow_main" if entrypoint == "run_workflow.py" else "batch_main"
    return f'''from __future__ import annotations

import os
import sys
from pathlib import Path


DEEPAGENTS_ROOT = Path(os.getenv("PRINCIPIA_DEEPAGENTS_ROOT", {str(deepagents_root)!r}))
DEEPAGENTS_PYTHON = DEEPAGENTS_ROOT / ".venv" / "bin" / "python"
if DEEPAGENTS_PYTHON.exists() and Path(sys.prefix).resolve() != (DEEPAGENTS_ROOT / ".venv").resolve():
    os.execv(str(DEEPAGENTS_PYTHON), [str(DEEPAGENTS_PYTHON), __file__, *sys.argv[1:]])

DEEPAGENTS_SRC = DEEPAGENTS_ROOT / "src"
if str(DEEPAGENTS_SRC) not in sys.path:
    sys.path.insert(0, str(DEEPAGENTS_SRC))

from principia_deepagents.legacy_cli import {function_name}


if __name__ == "__main__":
    sys.exit({function_name}())
'''


def backup_path_for(destination: Path) -> Path:
    base = destination.with_suffix(destination.suffix + ".legacy-langgraph.bak")
    if not base.exists():
        return base
    for index in range(1, 1000):
        candidate = destination.with_suffix(destination.suffix + f".legacy-langgraph.{index}.bak")
        if not candidate.exists():
            return candidate
    raise RuntimeError(f"could not find available backup path for {destination}")


def git_status_for_paths(target_project: Path, paths: tuple[str, ...]) -> list[str]:
    git_dir = target_project / ".git"
    if not git_dir.exists():
        return []
    result = subprocess.run(
        ["git", "-C", str(target_project), "status", "--short", "--", *paths],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return [result.stderr.strip() or "git status failed"]
    return [line for line in result.stdout.splitlines() if line.strip()]


def migrate(args: argparse.Namespace) -> int:
    target_project = args.target_project.resolve()
    deepagents_root = args.deepagents_root.resolve()
    if not target_project.exists():
        print(f"target project does not exist: {target_project}", file=sys.stderr)
        return 2
    if not (deepagents_root / "src" / "principia_deepagents").exists():
        print(f"deepagents root does not look valid: {deepagents_root}", file=sys.stderr)
        return 2

    dirty = git_status_for_paths(target_project, ENTRYPOINTS)
    if dirty and not args.allow_dirty:
        action = "Refusing to overwrite" if args.apply else "Apply would refuse to overwrite"
        print(f"{action} dirty legacy entrypoint files:")
        for line in dirty:
            print(f"  {line}")
        print("Re-run with --allow-dirty only after preserving those changes.")
        return 1 if args.apply else 0

    for entrypoint in ENTRYPOINTS:
        destination = target_project / entrypoint
        print(f"{'write' if args.apply else 'dry-run'}: {destination}")
        if args.apply:
            if args.backup and destination.exists():
                backup = backup_path_for(destination)
                backup.write_text(destination.read_text(encoding="utf-8"), encoding="utf-8")
                print(f"  backup: {backup}")
            destination.write_text(wrapper_text(entrypoint, deepagents_root), encoding="utf-8")

    if not args.apply:
        print("No files were changed. Pass --apply to write wrappers.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Install DeepAgents-backed compatibility wrappers into the legacy PrincipiaBlastFoam project."
    )
    parser.add_argument("--target-project", type=Path, default=DEFAULT_TARGET_PROJECT)
    parser.add_argument("--deepagents-root", type=Path, default=DEEPAGENTS_ROOT)
    parser.add_argument("--apply", action="store_true", help="Write wrapper files. Default is dry-run.")
    parser.add_argument("--allow-dirty", action="store_true", help="Allow overwriting dirty legacy entrypoint files.")
    parser.add_argument("--no-backup", dest="backup", action="store_false", help="Do not create .bak files.")
    parser.set_defaults(backup=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    return migrate(build_parser().parse_args(argv))


if __name__ == "__main__":
    sys.exit(main())
