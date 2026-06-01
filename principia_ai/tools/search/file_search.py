import fnmatch
import os
import re
from pathlib import Path
from langchain_core.tools import tool

from principia_ai.tools.context import resolve_tool_path


RUNTIME_DIR_NAMES = {"postProcessing", "VTK", "polyMesh"}
DEFAULT_MAX_MATCHES = 200
DEFAULT_MAX_CHARS = 20000


def _is_numeric_time_dir(name: str) -> bool:
    return bool(re.fullmatch(r"\d+(?:\.\d+)?(?:[eE][+-]?\d+)?", name))


def _is_runtime_dir(path: Path) -> bool:
    name = path.name
    if name.startswith("processor"):
        return True
    if name in RUNTIME_DIR_NAMES:
        return True
    return name != "0" and _is_numeric_time_dir(name)


@tool
def file_search(
    pattern: str,
    path: str = None,
    max_matches: int = DEFAULT_MAX_MATCHES,
    max_chars: int = DEFAULT_MAX_CHARS,
    include_runtime: bool = False,
):
    """Search for files in the workspace by glob pattern. This only returns the paths of matching files.
    
    Args:
        pattern: The glob pattern to search for (e.g. **/*.py).
        path: The path to search in. Defaults to the current directory.
        max_matches: Maximum matching paths to return.
        max_chars: Maximum returned characters.
        include_runtime: Include solver runtime outputs such as time directories,
            postProcessing, processor directories, VTK, and polyMesh.
    """
    try:
        search_path = resolve_tool_path(path, default_to_case=True)
        max_matches = max(1, min(int(max_matches), 1000))
        max_chars = max(1000, min(int(max_chars), 200000))
        matches = []
        truncated = False

        for root, dirs, files in os.walk(search_path):
            root_path = Path(root)
            if not include_runtime:
                dirs[:] = [
                    name for name in dirs
                    if not _is_runtime_dir(root_path / name) and not name.startswith(".")
                ]
            for name in files:
                rel_path = (root_path / name).relative_to(search_path)
                rel_text = str(rel_path)
                if fnmatch.fnmatch(rel_text, pattern) or rel_path.match(pattern):
                    matches.append(str(root_path / name))
                    if len(matches) >= max_matches:
                        truncated = True
                        break
            if truncated:
                break

        output = "\n".join(matches)
        notes = []
        if truncated:
            notes.append(f"[truncated after {max_matches} matches]")
        if not include_runtime:
            notes.append("[runtime output directories excluded by default; set include_runtime=true to search them]")
        if notes:
            output = (output + "\n" if output else "") + "\n".join(notes)
        if len(output) > max_chars:
            output = output[:max_chars] + f"\n[truncated after {max_chars} characters]"
        return output
    except Exception as e:
        return f"Error searching files with pattern {pattern} in {path}: {str(e)}"
