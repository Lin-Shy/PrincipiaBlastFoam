import subprocess
from langchain_core.tools import tool

from principia_ai.tools.context import resolve_tool_path
from principia_ai.utils.redaction import redact_text


@tool
def find_usages(symbol: str):
    """Find references, definitions, and other usages of a symbol.
    
    Args:
        symbol: The symbol to find usages for.
    """
    # Using grep as a simple find usages implementation
    try:
        search_path = resolve_tool_path(None, default_to_case=True)
        result = subprocess.run(
            [
                'grep',
                '-r',
                '--exclude=.env',
                '--exclude=.env.*',
                symbol,
                str(search_path),
            ],
            capture_output=True,
            text=True,
        )
        return redact_text(result.stdout)
    except Exception as e:
        return f"Error finding usages for {symbol}: {str(e)}"
