import subprocess
from langchain_core.tools import tool

@tool
def run_in_terminal(command: str):
    """Run commands in the terminal.
    
    Args:
        command: The command to run.
    """
    try:
        result = subprocess.run(
            command, 
            shell=True, 
            capture_output=True, 
            text=True
        )
        output = result.stdout
        if result.stderr:
            output += f"\nSTDERR:\n{result.stderr}"
        return output
    except Exception as e:
        return f"Error running command {command}: {str(e)}"