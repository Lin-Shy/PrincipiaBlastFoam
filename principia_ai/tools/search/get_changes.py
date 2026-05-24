import subprocess
from pathlib import Path
from langchain_core.tools import tool

from principia_ai.tools.context import get_active_case_path, resolve_tool_path
from principia_ai.utils.redaction import filter_sensitive_diff


def _git_root(path: Path) -> Path | None:
    cwd = path if path.is_dir() else path.parent
    if not cwd.exists():
        cwd = cwd.parent
    try:
        result = subprocess.run(
            ['git', '-C', str(cwd), 'rev-parse', '--show-toplevel'],
            capture_output=True,
            text=True,
        )
    except Exception:
        return None
    if result.returncode != 0:
        return None
    return Path(result.stdout.strip()).resolve()


@tool
def get_changes(path: str | None = None):
    """Get diffs scoped to the active generated case or an explicit path."""
    try:
        active_case = get_active_case_path()
        if path is None and active_case is None:
            return (
                "No active case path is set, so repository-wide git diff is hidden. "
                "Pass an explicit path if a scoped diff is required."
            )

        scoped_path = resolve_tool_path(path, default_to_case=True).resolve()
        root = _git_root(scoped_path)
        if root is None:
            return f"No git diff available for scoped path {scoped_path}; repository-wide diff is hidden."

        try:
            pathspec = str(scoped_path.relative_to(root)) or "."
        except ValueError:
            return f"Scoped path {scoped_path} is outside git root {root}; repository-wide diff is hidden."

        command = [
            'git',
            '-C',
            str(root),
            'diff',
            '--',
            pathspec,
            ':(exclude).env',
            ':(exclude).env.*',
            ':(exclude)**/.env',
            ':(exclude)**/.env.*',
        ]
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            return f"Error getting scoped git diff for {scoped_path}: {result.stderr.strip()}"
        return filter_sensitive_diff(result.stdout)
    except Exception as e:
        return f"Error getting changes: {str(e)}"
