import os
import re
from pathlib import Path
from langchain_core.tools import tool

from principia_ai.tools.context import resolve_tool_path
from principia_ai.utils.redaction import redact_text


RUNTIME_DIR_NAMES = {"postProcessing", "VTK", "polyMesh"}
DEFAULT_MAX_MATCHES = 40
DEFAULT_MAX_CHARS = 12000
DEFAULT_MAX_FILE_BYTES = 1_000_000


def _is_numeric_time_dir(name: str) -> bool:
    return bool(re.fullmatch(r"\d+(?:\.\d+)?(?:[eE][+-]?\d+)?", name))


def _is_runtime_dir(path: Path) -> bool:
    name = path.name
    if name.startswith("processor"):
        return True
    if name in RUNTIME_DIR_NAMES:
        return True
    return name != "0" and _is_numeric_time_dir(name)


def _iter_search_files(search_path: Path, include_runtime: bool):
    if search_path.is_file():
        if include_runtime or not any(_is_runtime_dir(parent) for parent in search_path.parents):
            yield search_path
        return

    for root, dirs, files in os.walk(search_path):
        root_path = Path(root)
        if not include_runtime:
            dirs[:] = [
                name for name in dirs
                if not _is_runtime_dir(root_path / name) and not name.startswith(".")
            ]
        for name in files:
            if name.startswith(".env"):
                continue
            yield root_path / name


@tool
def text_search(
    query: str,
    path: str = None,
    max_matches: int = DEFAULT_MAX_MATCHES,
    max_chars: int = DEFAULT_MAX_CHARS,
    include_runtime: bool = False,
):
    """Do a fast text search in the workspace.
    
    Args:
        query: The text to search for.
        path: The path to search in. Defaults to the current directory.
        max_matches: Maximum matching lines to return.
        max_chars: Maximum returned characters.
        include_runtime: Include solver runtime outputs such as time directories,
            postProcessing, processor directories, VTK, and polyMesh.
    """
    try:
        search_path = resolve_tool_path(path, default_to_case=True)
        max_matches = max(1, min(int(max_matches), 200))
        max_chars = max(1000, min(int(max_chars), 50000))
        matches = []
        skipped_large = 0
        truncated = False

        for file_path in _iter_search_files(search_path, include_runtime):
            try:
                if file_path.stat().st_size > DEFAULT_MAX_FILE_BYTES:
                    skipped_large += 1
                    continue
                with file_path.open("r", encoding="utf-8", errors="ignore") as handle:
                    for line_number, line in enumerate(handle, start=1):
                        if query not in line:
                            continue
                        snippet = " ".join(line.strip().split())[:600]
                        matches.append(f"{file_path}:{line_number}:{snippet}")
                        if len(matches) >= max_matches:
                            truncated = True
                            break
                if truncated:
                    break
            except OSError:
                continue

        output = "\n".join(matches)
        notes = []
        if truncated:
            notes.append(f"[truncated after {max_matches} matches]")
        if skipped_large:
            notes.append(f"[skipped {skipped_large} files larger than {DEFAULT_MAX_FILE_BYTES} bytes]")
        if not include_runtime:
            notes.append("[runtime output directories excluded by default; set include_runtime=true to search them]")
        if notes:
            output = (output + "\n" if output else "") + "\n".join(notes)
        if len(output) > max_chars:
            output = output[:max_chars] + f"\n[truncated after {max_chars} characters]"
        return redact_text(output)
    except Exception as e:
        return f"Error searching text {query} in {path}: {str(e)}"
