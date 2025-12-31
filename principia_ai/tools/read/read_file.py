import os
from langchain_core.tools import tool

@tool
def read_file(path: str, start_line: int = 1, end_line: int = -1):
    """Read the contents of a file.
    
    Args:
        path: The path to the file to read.
        start_line: The line number to start reading from (1-based).
        end_line: The line number to end reading at (1-based). -1 for end of file.
    """
    try:
        if not os.path.exists(path):
            return f"Error: File {path} does not exist."
            
        with open(path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        if end_line == -1:
            end_line = len(lines)
            
        # Check for large log files
        file_name = os.path.basename(path)
        if file_name.startswith('log.') and (end_line - start_line + 1) > 500:
            return (f"Warning: The log file '{file_name}' is too large ({len(lines)} lines). "
                    f"Please specify a smaller range using 'start_line' and 'end_line' (limit 500 lines).")

        # Adjust for 0-based indexing
        start_index = max(0, start_line - 1)
        end_index = min(len(lines), end_line)
        
        return "".join(lines[start_index:end_index])
    except Exception as e:
        return f"Error reading file {path}: {str(e)}"