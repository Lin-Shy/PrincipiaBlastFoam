import os
from langchain_core.tools import tool

@tool
def list_directory(path: str):
    """List the contents of a directory. Result will have the name of the child.
    
    Args:
        path: The path to the directory.
    """
    try:
        if not os.path.exists(path):
            return f"Error: Directory {path} does not exist."
            
        items = os.listdir(path)
        result = []
        for item in items:
            full_path = os.path.join(path, item)
            if os.path.isdir(full_path):
                result.append(f"{item}/")
            else:
                result.append(item)
        return "\n".join(result)
    except Exception as e:
        return f"Error listing directory {path}: {str(e)}"