import subprocess
from langchain_core.tools import tool

@tool
def text_search(query: str, path: str = None):
    """Do a fast text search in the workspace.
    
    Args:
        query: The text to search for.
        path: The path to search in. Defaults to the current directory.
    """
    try:
        search_path = path if path else "."
        # Using grep for fast text search
        result = subprocess.run(
            ['grep', '-r', query, search_path], 
            capture_output=True, 
            text=True
        )
        return result.stdout
    except Exception as e:
        return f"Error searching text {query} in {path}: {str(e)}"