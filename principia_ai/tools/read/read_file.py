import os
from langchain_core.tools import tool

from principia_ai.tools.context import resolve_tool_path
from principia_ai.utils.redaction import is_sensitive_path, redact_text


DEFAULT_MAX_CHARS = 12000
MAX_ALLOWED_CHARS = 50000


@tool
def read_file(path: str, start_line: int = 1, end_line: int = -1, max_chars: int = DEFAULT_MAX_CHARS):
    """Read the contents of a file.
    
    Args:
        path: The path to the file to read.
        start_line: The line number to start reading from (1-based).
        end_line: The line number to end reading at (1-based). -1 for end of file.
        max_chars: Maximum returned characters.
    """
    try:
        resolved_path = resolve_tool_path(path)
        if is_sensitive_path(resolved_path):
            return f"Error: Refusing to read sensitive file {resolved_path}."

        if not os.path.exists(resolved_path):
            return f"Error: File {path} does not exist. Resolved path: {resolved_path}."

        max_chars = max(1000, min(int(max_chars), MAX_ALLOWED_CHARS))
        file_size = os.path.getsize(resolved_path)
        if end_line == -1 and file_size > max_chars:
            return (
                f"Warning: File '{path}' is large ({file_size} bytes). "
                "Specify start_line/end_line or increase max_chars for a targeted read."
            )
            
        with open(resolved_path, 'r', encoding='utf-8') as f:
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
        
        output = "".join(lines[start_index:end_index])
        if len(output) > max_chars:
            output = output[:max_chars] + f"\n[truncated after {max_chars} characters]"
        return redact_text(output)
    except Exception as e:
        return f"Error reading file {path}: {str(e)}"
