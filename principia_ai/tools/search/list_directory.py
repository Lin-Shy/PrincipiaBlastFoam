import os
from langchain_core.tools import tool

from principia_ai.tools.context import resolve_tool_path

@tool
def list_directory(path: str, max_entries: int = 120, include_hidden: bool = False):
    """List the contents of a directory. Result will have the name of the child.
    
    Args:
        path: The path to the directory.
        max_entries: Maximum entries to return.
        include_hidden: Include hidden files and directories.
    """
    try:
        resolved_path = resolve_tool_path(path, default_to_case=True)
        if not os.path.exists(resolved_path):
            return f"Error: Directory {path} does not exist. Resolved path: {resolved_path}."
            
        max_entries = max(1, min(int(max_entries), 500))
        items = sorted(os.listdir(resolved_path))
        if not include_hidden:
            items = [item for item in items if not item.startswith(".")]
        result = []
        for item in items[:max_entries]:
            full_path = os.path.join(resolved_path, item)
            if os.path.isdir(full_path):
                result.append(f"{item}/")
            else:
                result.append(item)
        if len(items) > max_entries:
            result.append(f"[truncated after {max_entries} entries]")
        return "\n".join(result)
    except Exception as e:
        return f"Error listing directory {path}: {str(e)}"
