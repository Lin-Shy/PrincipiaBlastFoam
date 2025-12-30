import subprocess
from langchain_core.tools import tool

@tool
def text_search(query: str):
    """Do a fast text search in the workspace.
    
    Args:
        query: The text to search for.
    """
    try:
        # Using grep for fast text search
        result = subprocess.run(
            ['grep', '-r', query, '.'], 
            capture_output=True, 
            text=True
        )
        return result.stdout
    except Exception as e:
        return f"Error searching text {query}: {str(e)}"