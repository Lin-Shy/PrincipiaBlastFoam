import subprocess
from langchain_core.tools import tool

@tool
def get_changes():
    """Get diffs of changed files.
    """
    try:
        result = subprocess.run(
            ['git', 'diff'], 
            capture_output=True, 
            text=True
        )
        return result.stdout
    except Exception as e:
        return f"Error getting changes: {str(e)}"