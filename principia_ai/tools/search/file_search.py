import glob
import os
from langchain_core.tools import tool

@tool
def file_search(pattern: str, path: str = None):
    """Search for files in the workspace by glob pattern. This only returns the paths of matching files.
    
    Args:
        pattern: The glob pattern to search for (e.g. **/*.py).
        path: The path to search in. Defaults to the current directory.
    """
    try:
        search_path = path if path else "."
        # glob.glob with recursive=True handles **
        full_pattern = os.path.join(search_path, pattern)
        matches = glob.glob(full_pattern, recursive=True)
        return "\n".join(matches)
    except Exception as e:
        return f"Error searching files with pattern {pattern} in {path}: {str(e)}"