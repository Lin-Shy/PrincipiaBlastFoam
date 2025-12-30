import glob
import os
from langchain_core.tools import tool

@tool
def file_search(pattern: str):
    """Search for files in the workspace by glob pattern. This only returns the paths of matching files.
    
    Args:
        pattern: The glob pattern to search for (e.g. **/*.py).
    """
    try:
        # glob.glob with recursive=True handles **
        matches = glob.glob(pattern, recursive=True)
        return "\n".join(matches)
    except Exception as e:
        return f"Error searching files with pattern {pattern}: {str(e)}"