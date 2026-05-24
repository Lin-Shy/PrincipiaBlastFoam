import os
from langchain_core.tools import tool

from principia_ai.tools.context import resolve_tool_path

@tool
def create_directory(path: str):
    """Create new directories in your workspace.
    
    Args:
        path: The absolute or relative path to the directory to create.
    """
    try:
        resolved_path = resolve_tool_path(path, default_to_case=True)
        os.makedirs(resolved_path, exist_ok=True)
        return f"Successfully created directory: {resolved_path}"
    except Exception as e:
        return f"Error creating directory {path}: {str(e)}"
