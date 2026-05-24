import os
from langchain_core.tools import tool

from principia_ai.tools.context import resolve_tool_path

@tool
def create_file(path: str, content: str = ""):
    """Create new files.
    
    Args:
        path: The path to the file to create.
        content: The content to write to the file.
    """
    try:
        resolved_path = resolve_tool_path(path, default_to_case=True)
        directory = os.path.dirname(resolved_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
            
        with open(resolved_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"Successfully created file: {resolved_path}"
    except Exception as e:
        return f"Error creating file {path}: {str(e)}"
