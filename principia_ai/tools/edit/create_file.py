import os
from langchain_core.tools import tool

@tool
def create_file(path: str, content: str = ""):
    """Create new files.
    
    Args:
        path: The path to the file to create.
        content: The content to write to the file.
    """
    try:
        directory = os.path.dirname(path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
            
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"Successfully created file: {path}"
    except Exception as e:
        return f"Error creating file {path}: {str(e)}"