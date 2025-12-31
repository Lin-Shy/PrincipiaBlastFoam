from langchain_core.tools import tool
from .text_search import text_search

@tool
def search_codebase(query: str, path: str = None):
    """Find relevant file chunks, symbols, and other information in your codebase.
    
    Args:
        query: The query to search for.
        path: The path to search in. Defaults to the current directory.
    """
    # Mapping codebase search to text search for now
    return text_search(query, path)