import subprocess
from langchain_core.tools import tool

@tool
def find_usages(symbol: str):
    """Find references, definitions, and other usages of a symbol.
    
    Args:
        symbol: The symbol to find usages for.
    """
    # Using grep as a simple find usages implementation
    try:
        result = subprocess.run(
            ['grep', '-r', symbol, '.'], 
            capture_output=True, 
            text=True
        )
        return result.stdout
    except Exception as e:
        return f"Error finding usages for {symbol}: {str(e)}"