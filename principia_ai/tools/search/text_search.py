import subprocess
from langchain_core.tools import tool

from principia_ai.tools.context import resolve_tool_path
from principia_ai.utils.redaction import redact_text


@tool
def text_search(query: str, path: str = None):
    """Do a fast text search in the workspace.
    
    Args:
        query: The text to search for.
        path: The path to search in. Defaults to the current directory.
    """
    try:
        search_path = resolve_tool_path(path, default_to_case=True)
        # Using grep for fast text search
        result = subprocess.run(
            [
                'grep',
                '-r',
                '--exclude=.env',
                '--exclude=.env.*',
                query,
                str(search_path),
            ],
            capture_output=True,
            text=True,
        )
        return redact_text(result.stdout)
    except Exception as e:
        return f"Error searching text {query} in {path}: {str(e)}"
