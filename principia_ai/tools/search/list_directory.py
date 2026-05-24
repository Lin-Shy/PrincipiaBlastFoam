import os
from langchain_core.tools import tool

from principia_ai.tools.context import resolve_tool_path

@tool
def list_directory(path: str):
    """List the contents of a directory. Result will have the name of the child.
    
    Args:
        path: The path to the directory.
    """
    try:
        resolved_path = resolve_tool_path(path, default_to_case=True)
        if not os.path.exists(resolved_path):
            return f"Error: Directory {path} does not exist. Resolved path: {resolved_path}."
            
        items = os.listdir(resolved_path)
        result = []
        for item in items:
            full_path = os.path.join(resolved_path, item)
            if os.path.isdir(full_path):
                result.append(f"{item}/")
            else:
                result.append(item)
        return "\n".join(result)
    except Exception as e:
        return f"Error listing directory {path}: {str(e)}"
