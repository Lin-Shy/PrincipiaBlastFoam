import subprocess
from langchain_core.tools import tool

from principia_ai.tools.context import get_active_case_path
from principia_ai.utils.redaction import redact_text

@tool
def run_in_terminal(command: str):
    """Run commands in the terminal.
    
    Args:
        command: The command to run.
    """
    try:
        cwd = get_active_case_path()
        result = subprocess.run(
            command, 
            shell=True, 
            capture_output=True, 
            text=True,
            cwd=str(cwd) if cwd else None,
        )
        output = result.stdout
        if result.stderr:
            output += f"\nSTDERR:\n{result.stderr}"
        return redact_text(output)
    except Exception as e:
        return redact_text(f"Error running command {command}: {str(e)}")
