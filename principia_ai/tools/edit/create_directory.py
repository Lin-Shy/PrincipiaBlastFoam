import os
from langchain_core.tools import tool

@tool
def create_directory(path: str):
    """Create new directories in your workspace.
    
    Args:
        path: The absolute or relative path to the directory to create.
    """
    try:
        os.makedirs(path, exist_ok=True)
        return f"Successfully created directory: {path}"
    except Exception as e:
        return f"Error creating directory {path}: {str(e)}"